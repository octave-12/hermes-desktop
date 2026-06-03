import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  source?: 'desktop' | 'wechat'
  audioUrl?: string       // TTS audio URL for voice message playback
}

export interface ToolCall {
  name: string
  args: string
  result?: string
  status: 'running' | 'done' | 'error'
}

export interface QueueItem {
  user_msg_id: string
  content_preview: string
}

export interface Session {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  lastAiMessage?: string
  isLoading?: boolean
  queueItems?: QueueItem[]
  needsReload?: boolean
  totalCount?: number
  hasMore?: boolean
  isLocalOnly?: boolean
}

export interface WeChatConnection {
  user_id: string
  nickname: string
  avatar: string
  connected_at?: number
  status?: string
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const isConnected = ref(false)
  const isReconnecting = ref(false)
  const isLoading = ref(false)
  const ws = ref<WebSocket | null>(null)

  // WeChat connections
  const wechatConnections = ref<WeChatConnection[]>([])

  // Context summary notification (shows when LLM summarizes pruned messages)
  const sessionSummary = ref<{
    sessionId: string
    summaryText: string
    droppedCount: number
    totalMessages: number
  } | null>(null)

  // Pending messages queue (per session)
  const pendingMessages = ref<Map<string, string[]>>(new Map())

  // Reconnection state
  let backendUrl = ''
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_DELAY = 30000
  const HEARTBEAT_INTERVAL = 15000

  // ── Helper: send JSON via WebSocket ──────────────────────
  function wsSend(data: Record<string, unknown>) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }

  // ── Session CRUD (all go through backend) ────────────────
  function createSession() {
    const id = crypto.randomUUID()
    const session: Session = {
      id,
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      isLocalOnly: true
    }
    sessions.value.unshift(session)
    currentSessionId.value = id
    wsSend({ type: 'create_session', session_id: id, title: '新对话' })
    return session
  }

  function deleteSession(id: string) {
    const idx = sessions.value.findIndex((s) => s.id === id)
    if (idx === -1) return
    
    const session = sessions.value[idx]
    // Stop generation if session is loading
    if (session.isLoading) {
      wsSend({ type: 'stop_generation', session_id: id })
    }
    
    sessions.value.splice(idx, 1)
    // Clean up pending messages for deleted session
    pendingMessages.value.delete(id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
    wsSend({ type: 'delete_session', session_id: id })
  }

  function switchSession(id: string) {
    // Don't stop generation - let AI continue in background
    // Messages will be persisted to database automatically
    
    currentSessionId.value = id
    const session = sessions.value.find((s) => s.id === id)
    // Always reload wechat-session (gateway data may have changed)
    // Load messages if session has none or needs reload
    if (session && (session.messages.length === 0 || session.needsReload || id === 'wechat-session')) {
      session.needsReload = false
      wsSend({ type: 'load_messages', session_id: id, limit: 100 })
    }
  }

  function loadMoreMessages(sessionId: string, beforeTimestamp: number) {
    wsSend({ type: 'load_messages', session_id: sessionId, before_timestamp: beforeTimestamp, limit: 100 })
  }

  function getCurrentSession(): Session | undefined {
    return sessions.value.find((s) => s.id === currentSessionId.value)
  }

  function addMessage(message: Message) {
    const session = getCurrentSession()
    if (session) {
      session.messages.push(message)
    }
  }

  function renameSession(id: string, title: string) {
    const session = sessions.value.find((s) => s.id === id)
    if (session) {
      session.title = title
    }
    wsSend({ type: 'rename_session', session_id: id, title })
  }

  // ── Heartbeat ────────────────────────────────────────────
  let lastPongTime = 0
  const PONG_TIMEOUT = 60000 // 60 seconds (increased from 30s)

  function startHeartbeat() {
    stopHeartbeat()
    lastPongTime = Date.now()
    heartbeatTimer = setInterval(() => {
      // Check pong timeout
      if (Date.now() - lastPongTime > PONG_TIMEOUT) {
        console.warn('[WS] Pong timeout, closing connection')
        ws.value?.close()
        return
      }
      wsSend({ type: 'ping' })
    }, HEARTBEAT_INTERVAL)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // ── Reconnect ────────────────────────────────────────────
  const MAX_RECONNECT_ATTEMPTS = 10

  function scheduleReconnect() {
    if (reconnectTimer) return
    
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error('[WS] Max reconnect attempts reached, giving up')
      isReconnecting.value = false
      
      // Notify user
      sessions.value.forEach(session => {
        if (session.messages.length > 0) {
          session.messages.push({
            id: crypto.randomUUID(),
            role: 'system',
            content: '无法连接到服务器，请检查网络或重启应用。',
            timestamp: Date.now()
          })
        }
      })
      return
    }
    
    isReconnecting.value = true
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      reconnectAttempts++
      connectWebSocket(backendUrl)
    }, delay)
  }

  // ── WebSocket connection ─────────────────────────────────
  function connectWebSocket(url: string) {
    backendUrl = url

    // Clear any pending reconnect timer before creating new connection
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    // Stop heartbeat before creating new connection
    stopHeartbeat()

    if (ws.value) {
      ws.value.onclose = null
      ws.value.close()
    }

    const socket = new WebSocket(url)

    socket.onopen = () => {
      isConnected.value = true
      isReconnecting.value = false
      reconnectAttempts = 0
      startHeartbeat()
      // Load persisted sessions from backend
      socket.send(JSON.stringify({ type: 'load_sessions' }))
    }

    socket.onclose = () => {
      isConnected.value = false
      stopHeartbeat()
      // Reset all sessions' isLoading state
      sessions.value.forEach(session => {
        if (session.isLoading) {
          session.isLoading = false
          if (session.messages.length > 0) {
            session.messages.push({
              id: crypto.randomUUID(),
              role: 'system',
              content: '连接已断开，正在尝试重新连接...',
              timestamp: Date.now()
            })
          }
        }
      })
      scheduleReconnect()
    }

    socket.onerror = (err) => {
      console.error('[WS] Error:', err)
      isConnected.value = false
      stopHeartbeat()
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') {
          lastPongTime = Date.now()
          return
        }
        handleServerMessage(data)
      } catch (e) {
        console.error('[WS] Failed to parse message:', e)
      }
    }

    ws.value = socket
  }

  // ── Message handler ──────────────────────────────────────
  function handleServerMessage(data: any) {
    switch (data.type) {
      // ── Persistence messages ──
      case 'sessions_loaded': {
        const backendSessions: Session[] = data.sessions.map((s: any) => ({
          id: s.id,
          title: s.title,
          messages: [],
          createdAt: s.createdAt
        }))
        // Only keep local sessions explicitly marked as local (user just created them)
        // This prevents stale "ghost" sessions from persisting forever
        const localOnly = sessions.value.filter(
          (ls) => !backendSessions.some((bs) => bs.id === ls.id)
            && ls.isLocalOnly === true
        )
        sessions.value = [...localOnly, ...backendSessions]
        
        // Auto-select first session if none selected
        if (!currentSessionId.value && sessions.value.length > 0) {
          switchSession(sessions.value[0].id)
        }
        break
      }
      case 'messages_loaded': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          // For wechat-session: always replace (gateway data is authoritative)
          // For other sessions: merge new messages with existing
          if (session.messages.length === 0 || data.session_id === 'wechat-session') {
            session.messages = data.messages
          } else if (data.messages.length > 0) {
            const firstNewTimestamp = data.messages[0].timestamp
            const existingIds = new Set(session.messages.map(m => m.id))
            const newMessages = data.messages.filter(m => !existingIds.has(m.id))
            if (newMessages.length > 0) {
              session.messages = [...newMessages, ...session.messages]
            }
          }
          session.totalCount = data.total_count
          session.hasMore = data.has_more
          const aiMessages = data.messages.filter((m: Message) => m.role === 'assistant')
          if (aiMessages.length > 0) {
            session.lastAiMessage = aiMessages[aiMessages.length - 1].content
          }
        }
        break
      }
      case 'session_title': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) session.title = data.title
        break
      }
      case 'session-summary': {
        sessionSummary.value = {
          sessionId: data.session_id,
          summaryText: data.summary_text,
          droppedCount: data.dropped_count,
          totalMessages: data.total_messages,
        }
        break
      }
      case 'session_renamed': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) session.title = data.title
        break
      }
      // ── Streaming chat messages ──
      case 'token': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (!session) break
        // Clean special control characters
        const cleanedContent = data.content.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
        const lastMsg = session.messages[session.messages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content += cleanedContent
        } else {
          session.messages.push({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: cleanedContent,
            timestamp: Date.now()
          })
        }
        // Dispatch token event for streaming TTS
        window.dispatchEvent(new CustomEvent('chat-token', { detail: { token: cleanedContent } }))
        break
      }
      case 'message_done': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.isLoading = false
          session.queueItems = []  // Clear queue display when conversation round completes
          // Update lastAiMessage only when message is complete
          const lastMsg = session.messages[session.messages.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            session.lastAiMessage = lastMsg.content
          }
          // If this is not current session, mark for reload instead of clearing
          if (data.session_id !== currentSessionId.value) {
            // Set a flag to reload messages when user switches back
            session.needsReload = true
          }
        }
        break
      }
      case 'message_queued': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.isLoading = true
        }
        break
      }
      case 'session_waiting': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.isLoading = true
          session.messages.push({
            id: crypto.randomUUID(),
            role: 'system',
            content: data.reason || '等待并发槽位...',
            timestamp: Date.now()
          })
        }
        break
      }
      case 'queue_updated': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.queueItems = data.queue_items || []
          // Don't reset isLoading here — let message_done handle it
          // isLoading should stay true while AI is generating
        }
        break
      }
      case 'tool_call': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (!session) break
        const currentMsg = session.messages[session.messages.length - 1]
        if (currentMsg && currentMsg.role === 'assistant') {
          if (!currentMsg.toolCalls) currentMsg.toolCalls = []
          currentMsg.toolCalls.push({
            name: data.name,
            args: data.args,
            status: 'running'
          })
        }
        break
      }
      case 'tool_result': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (!session) break
        const msg = session.messages[session.messages.length - 1]
        if (msg?.toolCalls) {
          const tc = msg.toolCalls[msg.toolCalls.length - 1]
          if (tc) {
            tc.result = data.result
            tc.status = data.error ? 'error' : 'done'
          }
        }
        break
      }
      case 'error': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.isLoading = false
          session.messages.push({
            id: crypto.randomUUID(),
            role: 'system',
            content: `Error: ${data.message}`,
            timestamp: Date.now()
          })
        } else {
          console.error(`Error for unknown session ${data.session_id}: ${data.message}`)
        }
        break
      }
      
      // ── WeChat integration messages ──
      case 'wechat_connected': {
        const existing = wechatConnections.value.find(c => c.user_id === data.user_id)
        if (!existing) {
          wechatConnections.value.push({
            user_id: data.user_id,
            nickname: data.nickname,
            avatar: data.avatar
          })
        }
        break
      }
      
      case 'wechat_disconnected': {
        wechatConnections.value = wechatConnections.value.filter(
          c => c.user_id !== data.user_id
        )
        break
      }
      
      case 'new_message': {
        // Message from WeChat or other sources (supports both nested and flat format)
        // Always route gateway/wechat messages to the consolidated wechat-session
        const sessionId = data.session_id === 'wechat-session' ? 'wechat-session' : data.session_id
        let session = sessions.value.find((s) => s.id === sessionId)

        // Never auto-create sessions from incoming messages — if session doesn't exist,
        // route to the wechat-session instead to prevent duplicate sidebar entries
        if (!session && sessionId !== 'wechat-session') {
          session = sessions.value.find((s) => s.id === 'wechat-session')
        }

        if (session) {
          // Support both nested (data.message) and flat (data.role/data.content) formats
          const msg = data.message || {
            id: data.message_id,
            role: data.role,
            content: data.content,
            source: data.source,
            timestamp: data.timestamp
          }
          const exists = session.messages.some(m => m.id === msg.id)
          if (!exists) {
            session.messages.push({
              ...msg,
              timestamp: msg.timestamp || Date.now()
            })
          }
        }
        break
      }
      
      case 'chat_stream': {
        // Streaming response from WeChat
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (!session) break
        
        const msg = session.messages.find(m => m.id === data.message_id)
        if (msg) {
          msg.content += data.delta
        } else {
          session.messages.push({
            id: data.message_id,
            role: 'assistant',
            content: data.delta,
            source: data.source || 'wechat',
            timestamp: Date.now()
          })
        }
        break
      }
      
      case 'gateway_new_messages': {
        // Gateway sync detected new messages in Hermes state.db
        // If we're currently on wechat-session, reload messages immediately
        if (currentSessionId.value === 'wechat-session') {
          wsSend({ type: 'load_messages', session_id: 'wechat-session', limit: 100 })
        } else {
          // Mark wechat-session for reload when user switches back
          const wcSession = sessions.value.find(s => s.id === 'wechat-session')
          if (wcSession) wcSession.needsReload = true
        }
        break
      }
      case 'gateway_sessions_updated': {
        // New gateway sessions detected — trigger session list refresh
        wsSend({ type: 'load_sessions' })
        // Reload current session's messages to pick up new gateway content
        if (currentSessionId.value) {
          const active = sessions.value.find(s => s.id === currentSessionId.value)
          if (active) {
            wsSend({ type: 'load_messages', session_id: currentSessionId.value, limit: 100 })
          }
        }
        break
      }
      
      case 'gateway_active_session_changed': {
        // Active gateway session changed (user did /new or /切换会话 in WeChat)
        // Reload wechat-session messages to show the new active conversation
        const wcSession = sessions.value.find(s => s.id === 'wechat-session')
        if (wcSession) {
          wcSession.needsReload = true
          // If currently viewing wechat-session, reload immediately
          if (currentSessionId.value === 'wechat-session') {
            wsSend({ type: 'load_messages', session_id: 'wechat-session', limit: 100 })
          }
        }
        break
      }

      case 'session_created': {
        // Session created from WeChat
        const exists = sessions.value.some(s => s.id === data.session.id)
        if (!exists) {
          sessions.value.unshift({
            id: data.session.id,
            title: data.session.title,
            messages: [],
            createdAt: data.session.createdAt
          })
        } else {
          // Backend confirmed creation — clear local-only flag so sessions_loaded keeps it
          const local = sessions.value.find(s => s.id === data.session.id)
          if (local) local.isLocalOnly = false
        }
        break
      }
    }
  }

  // ── Send chat message ────────────────────────────────────
  function sendMessage(content: string) {
    // Validate message content
    const trimmedContent = content.trim()
    if (!trimmedContent) return
    
    const session = getCurrentSession()
    if (!session) return
    
    // Check WebSocket connection
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      // Add message to queue for later sending
      const queue = pendingMessages.value.get(session.id) || []
      queue.push(trimmedContent)
      pendingMessages.value.set(session.id, queue)
      
      session.messages.push({
        id: crypto.randomUUID(),
        role: 'system',
        content: '连接已断开，消息已加入队列，等待重连后发送...',
        timestamp: Date.now()
      })
      return
    }

    const message: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmedContent,
      timestamp: Date.now()
    }

    // If already loading, add to queue only (not in messages yet)
    if (session.isLoading) {
      // Initialize queue items if not exists
      if (!session.queueItems) {
        session.queueItems = []
      }
      session.queueItems.push({
        user_msg_id: message.id,
        content_preview: trimmedContent.substring(0, 50)
      })
      
      // Send to backend but don't add to messages yet
      ws.value.send(
        JSON.stringify({
          type: 'chat',
          session_id: currentSessionId.value,
          message_id: message.id,
          content
        })
      )
    } else {
      // Not loading, add to messages and send
      session.messages.push(message)
      session.isLoading = true
      
      // Send with message_id so backend can persist it
      ws.value.send(
        JSON.stringify({
          type: 'chat',
          session_id: currentSessionId.value,
          message_id: message.id,
          content
        })
      )
    }
  }

  // ── Process pending messages ───────────────────────────────
  function processPendingMessages(sessionId: string) {
    const queue = pendingMessages.value.get(sessionId)
    if (!queue || queue.length === 0) return

    const nextMessage = queue.shift()
    if (queue.length === 0) {
      pendingMessages.value.delete(sessionId)
    }

    // Send next message
    if (nextMessage) {
      sendMessage(nextMessage)
    }
  }

  // ── Stop generation ─────────────────────────────────────────
  function stopGeneration(sessionId: string) {
    const session = sessions.value.find((s) => s.id === sessionId)
    if (session) {
      session.isLoading = false
      // Send stop signal to backend
      wsSend({ type: 'stop_generation', session_id: sessionId })
    }
  }

  // ── Remove from queue ───────────────────────────────────────
  function removeFromQueue(sessionId: string, userMsgId: string) {
    wsSend({ type: 'remove_from_queue', session_id: sessionId, user_msg_id: userMsgId })
  }

  function disconnect() {
    stopHeartbeat()
    isReconnecting.value = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.onclose = null
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
    // Clean up all pending messages
    pendingMessages.value.clear()
  }

  function clearSummary() {
    sessionSummary.value = null
  }

  return {
    sessions,
    currentSessionId,
    isConnected,
    isReconnecting,
    isLoading,
    pendingMessages,
    wechatConnections,
    sessionSummary,
    clearSummary,
    createSession,
    deleteSession,
    switchSession,
    getCurrentSession,
    addMessage,
    renameSession,
    sendMessage,
    stopGeneration,
    removeFromQueue,
    loadMoreMessages,
    connectWebSocket,
    disconnect
  }
})
