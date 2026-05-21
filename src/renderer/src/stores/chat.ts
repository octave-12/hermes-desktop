import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  name: string
  args: string
  result?: string
  status: 'running' | 'done' | 'error'
}

export interface Session {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  lastAiMessage?: string
  isLoading?: boolean
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const isConnected = ref(false)
  const isReconnecting = ref(false)
  const isLoading = ref(false)
  const ws = ref<WebSocket | null>(null)

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
      createdAt: Date.now()
    }
    sessions.value.unshift(session)
    currentSessionId.value = id
    wsSend({ type: 'create_session', session_id: id, title: '新对话' })
    return session
  }

  function deleteSession(id: string) {
    const idx = sessions.value.findIndex((s) => s.id === id)
    if (idx === -1) return
    sessions.value.splice(idx, 1)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
    wsSend({ type: 'delete_session', session_id: id })
  }

  function switchSession(id: string) {
    currentSessionId.value = id
    const session = sessions.value.find((s) => s.id === id)
    // Load messages if session has none yet (lazy load from DB)
    if (session && session.messages.length === 0) {
      wsSend({ type: 'load_messages', session_id: id })
    }
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
  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
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
  function scheduleReconnect() {
    if (reconnectTimer) return
    isReconnecting.value = true
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY)
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})...`)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      reconnectAttempts++
      connectWebSocket(backendUrl)
    }, delay)
  }

  // ── WebSocket connection ─────────────────────────────────
  function connectWebSocket(url: string) {
    backendUrl = url

    if (ws.value) {
      ws.value.onclose = null
      ws.value.close()
    }

    const socket = new WebSocket(url)

    socket.onopen = () => {
      isConnected.value = true
      isReconnecting.value = false
      reconnectAttempts = 0
      console.log('[WS] Connected')
      startHeartbeat()
      // Load persisted sessions from backend
      socket.send(JSON.stringify({ type: 'load_sessions' }))
    }

    socket.onclose = () => {
      isConnected.value = false
      stopHeartbeat()
      console.log('[WS] Disconnected')
      scheduleReconnect()
    }

    socket.onerror = (err) => {
      console.error('[WS] Error:', err)
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
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
        // Merge backend sessions (don't overwrite locally created ones)
        const backendSessions: Session[] = data.sessions.map((s: any) => ({
          id: s.id,
          title: s.title,
          messages: [],
          createdAt: s.createdAt
        }))
        // Keep any local sessions not yet in backend list
        const localOnlyIds = new Set(
          sessions.value
            .filter((ls) => !backendSessions.some((bs) => bs.id === ls.id))
            .map((ls) => ls.id)
        )
        const localOnly = sessions.value.filter((s) => localOnlyIds.has(s.id))
        sessions.value = [...localOnly, ...backendSessions]
        
        // Auto-select first session if none selected
        if (!currentSessionId.value && sessions.value.length > 0) {
          switchSession(sessions.value[0].id)
        }
        break
      }
      case 'messages_loaded': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session && session.messages.length === 0) {
          session.messages = data.messages
          // Extract last AI message for preview
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
      case 'session_renamed': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) session.title = data.title
        break
      }
      // ── Streaming chat messages ──
      case 'token': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (!session) break
        const lastMsg = session.messages[session.messages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content += data.content
          session.lastAiMessage = lastMsg.content
        } else {
          session.messages.push({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: data.content,
            timestamp: Date.now()
          })
          session.lastAiMessage = data.content
          session.isLoading = false
        }
        break
      }
      case 'message_done': {
        const session = sessions.value.find((s) => s.id === data.session_id)
        if (session) {
          session.isLoading = false
          processPendingMessages(session.id)
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
        if (session) session.isLoading = false
        session?.messages.push({
          id: crypto.randomUUID(),
          role: 'system',
          content: `Error: ${data.message}`,
          timestamp: Date.now()
        })
        break
      }
    }
  }

  // ── Send chat message ────────────────────────────────────
  function sendMessage(content: string) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      console.error('[WS] Not connected')
      return
    }

    const session = getCurrentSession()
    if (!session) return

    // If AI is currently responding, add to pending queue
    if (session.isLoading) {
      const queue = pendingMessages.value.get(session.id) || []
      queue.push(content)
      pendingMessages.value.set(session.id, queue)
      return
    }

    const message: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: Date.now()
    }

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
  }

  return {
    sessions,
    currentSessionId,
    isConnected,
    isReconnecting,
    isLoading,
    pendingMessages,
    createSession,
    deleteSession,
    switchSession,
    getCurrentSession,
    addMessage,
    renameSession,
    sendMessage,
    stopGeneration,
    connectWebSocket,
    disconnect
  }
})
