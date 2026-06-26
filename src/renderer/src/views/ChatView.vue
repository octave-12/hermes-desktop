<template>
  <div class="chat-view">
    <!-- Empty state -->
    <div v-if="!currentSession || currentSession.messages.length === 0" class="empty-state">
      <div class="empty-content">
        <div class="horse-animation">
          <img src="@/assets/horse-running.gif" alt="Running Horse" class="running-horse-gif" />
        </div>
        <h2>Hermes Agent</h2>
        <p>开始一段新对话，或从左侧选择历史会话</p>
      </div>
    </div>

    <!-- Messages -->
    <div v-else class="messages-container" ref="messagesContainer" @scroll="handleScroll">
      <div v-if="currentSession?.hasMore" class="load-more">
        <span class="load-more-text">↑ 上滑加载更多消息</span>
      </div>
      <div
        v-for="msg in currentSession.messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
            <!-- Summary notification pill (before first message) -->
            <template v-if="msg === currentSession.messages[0] && sessionSummary">
              <div class="summary-pill" @click="dismissSummary">
                <span class="summary-icon">📋</span>
                <span class="summary-text">
                  已自动总结 {{ sessionSummary.droppedCount }} 条历史消息
                  （共 {{ sessionSummary.totalMessages }} 条）
                </span>
                <span class="summary-close">×</span>
              </div>
            </template>
            <!-- AI message: avatar left, bubble left -->
            <template v-if="msg.role === 'assistant'">
              <div class="bubble ai-bubble" :class="msg.source">
                <div class="bubble-content" v-html="renderMarkdown(msg.content)"></div>
                <VoiceMessagePlayer
                  v-if="msg.audioUrl"
                  :audio-url="msg.audioUrl"
                  :auto-play="true"
                />
                <div v-if="msg.toolCalls?.length" class="tool-calls">
                  <div v-for="(tc, idx) in msg.toolCalls" :key="idx" class="tool-call">
                    <div class="tool-header">
                      <span class="tool-name">{{ tc.name }}</span>
                      <span class="tool-status" :class="tc.status">{{ tc.status }}</span>
                    </div>
                    <pre v-if="tc.result" class="tool-result">{{ tc.result }}</pre>
                  </div>
                </div>
                <div v-if="msg.source === 'wechat'" class="source-badge wechat">
                  <span class="source-icon">📱</span>
                  <span class="source-label">微信</span>
                </div>
              </div>
            </template>

            <!-- User message: bubble right -->
            <template v-else-if="msg.role === 'user'">
              <div class="bubble user-bubble" :class="msg.source">
                <div class="bubble-content">{{ msg.content }}</div>
                <div v-if="msg.source === 'wechat'" class="source-badge wechat">
                  <span class="source-icon">📱</span>
                  <span class="source-label">微信</span>
                </div>
              </div>
            </template>

            <!-- System message: centered -->
            <template v-else>
              <div class="system-msg">{{ msg.content }}</div>
            </template>
          </div>

      <!-- Loading indicator -->
      <div v-if="currentSession?.isLoading" class="message-row assistant">
        <div class="avatar ai-avatar">H</div>
        <div class="bubble ai-bubble">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pending messages queue -->
    <div v-if="currentSession?.queueItems && currentSession.queueItems.length > 0" class="pending-queue">
      <div class="pending-header">
        <span class="pending-icon">⏳</span>
        <span>任务队列: {{ currentSession.queueItems.length }} 条</span>
      </div>
      <div class="queue-items">
        <div 
          v-for="(item, index) in currentSession.queueItems" 
          :key="item.user_msg_id"
          class="queue-item"
        >
          <span class="queue-index">{{ index + 1 }}.</span>
          <span class="queue-preview">{{ item.content_preview }}...</span>
          <button 
            class="queue-remove-btn"
            @click="removeQueueItem(item.user_msg_id)"
            title="删除"
          >
            ×
          </button>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="input-area" :style="{ height: inputAreaHeight + 'px' }">
      <div class="resize-handle" @mousedown="startResize"></div>
      <div class="input-wrapper">
        <textarea
          v-model="inputText"
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          @keydown.enter.exact.prevent="handleSend"
          rows="1"
        ></textarea>
        <button
          class="voice-toggle-btn"
          :class="{ active: voiceMode.settings.value.enabled }"
          @click="toggleVoiceMode"
          title="语音模式"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/>
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
          </svg>
        </button>
        <button 
          class="send-btn" 
          :class="{ 'is-loading': currentSession?.isLoading }"
          @click="handleSendOrStop"
        >
          <!-- Loading spinner (when AI is responding) -->
          <svg v-if="currentSession?.isLoading" class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20">
              <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
            </circle>
          </svg>
          <!-- Send icon (when idle) -->
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useVoiceMode } from '@/composables/useVoiceMode'
import VoiceMessagePlayer from '@/components/VoiceMessagePlayer.vue'

declare global {
  interface Window {
    api: {
      getBackendUrl: () => Promise<string>
    }
  }
}

const chatStore = useChatStore()
const inputText = ref('')
const messagesContainer = ref<HTMLElement>()
const inputAreaHeight = ref(120)
const isResizing = ref(false)
const isLoadingMore = ref(false)

const currentSession = computed(() => chatStore.getCurrentSession())
const sessionSummary = computed(() => chatStore.sessionSummary)
const dismissSummary = () => chatStore.clearSummary()

// ── Voice Mode Integration ──────────────────────────────────
const voiceMode = useVoiceMode()
const pendingTtsMessage = ref<{ audioUrl: string } | null>(null)

const toggleVoiceMode = () => {
  const next = !voiceMode.settings.value.enabled
  voiceMode.settings.value.enabled = next
  const saved = JSON.parse(localStorage.getItem('hermes_voice_settings') || '{}')
  saved.enabled = next
  localStorage.setItem('hermes_voice_settings', JSON.stringify(saved))
  // Only dispatch event — useVoiceMode's listener handles start/stop (no double-call)
  window.dispatchEvent(new CustomEvent('voice-settings-changed', { detail: { enabled: next } }))
}

// ── Streaming TTS: forward tokens to voice mode ─────────
function handleChatToken(e: Event) {
  const token = (e as CustomEvent).detail?.token
  if (token && voiceMode.settings.value.enabled) {
    console.log(`[ChatView] chat-token received, forwarding to voiceMode`)
    voiceMode.onStreamingToken(token)
  }
}

onMounted(() => {
  window.addEventListener('chat-token', handleChatToken)
})

onUnmounted(() => {
  window.removeEventListener('chat-token', handleChatToken)
})

// Watch for AI response completion to trigger TTS
watch(
  () => currentSession.value?.isLoading,
  (isLoading) => {
    if (!isLoading && currentSession.value) {
      const lastMsg = currentSession.value.messages[currentSession.value.messages.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && voiceMode.settings.value.enabled) {
        pendingTtsMessage.value = lastMsg
        voiceMode.onAiResponse(lastMsg.content)
      }
    }
  }
)

/** Strip voice mode markers and hidden instructions from text for display */
function stripVoiceMarkers(content: string): string {
  return content
    .replace(/<!--[\s\S]*?-->/g, '')           // HTML comments (hidden instructions)
    .replace(/\[CONTINUE\]/g, '')              // Continue marker
    .replace(/\[DONE\]/g, '')                  // Done marker
    .trim()
}

function renderMarkdown(content: string): string {
  if (!content) return ''
  return stripVoiceMarkers(content)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return

  if (!chatStore.currentSessionId) {
    chatStore.createSession()
  }

  chatStore.sendMessage(text)
  inputText.value = ''
  nextTick(() => scrollToBottom())
}

function removeQueueItem(userMsgId: string) {
  if (currentSession.value) {
    chatStore.removeFromQueue(currentSession.value.id, userMsgId)
  }
}

function handleSendOrStop() {
  // If AI is responding, stop it
  if (currentSession.value?.isLoading) {
    chatStore.stopGeneration(currentSession.value.id)
    return
  }
  
  // Otherwise send message
  handleSend()
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function handleScroll() {
  if (!messagesContainer.value || !currentSession.value || isLoadingMore.value) return
  
  const { scrollTop } = messagesContainer.value
  
  if (scrollTop < 100 && currentSession.value.hasMore && currentSession.value.messages.length > 0) {
    isLoadingMore.value = true
    const firstMessage = currentSession.value.messages[0]
    chatStore.loadMoreMessages(currentSession.value.id, firstMessage.timestamp)
    
    setTimeout(() => {
      isLoadingMore.value = false
    }, 500)
  }
}

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startY = e.clientY
  const startHeight = inputAreaHeight.value

  function onMouseMove(e: MouseEvent) {
    const deltaY = startY - e.clientY
    const newHeight = Math.min(300, Math.max(60, startHeight + deltaY))
    inputAreaHeight.value = newHeight
  }

  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

watch(
  () => currentSession.value?.messages.length,
  () => scrollToBottom()
)

onMounted(async () => {
  try {
    const url = await window.api.getBackendUrl()
    chatStore.connectWebSocket(url)
  } catch (e) {
    console.error('Failed to get backend URL:', e)
  }

  // Configure voice mode
  voiceMode.configure({
    sendMessage: (text) => {
      if (!chatStore.currentSessionId) {
        chatStore.createSession()
      }
      chatStore.sendMessage(text)
    },
    onStatusChange: () => {
      // Status changes reflected via computed properties
    },
    onTtsComplete: (audioUrl) => {
      if (pendingTtsMessage.value) {
        pendingTtsMessage.value.audioUrl = audioUrl
        pendingTtsMessage.value = null
      }
    },
  })

  // If voice mode was already enabled, start it
  if (voiceMode.settings.value.enabled) {
    voiceMode.startVoiceMode()
  }
})
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
  color: #6c7086;
}

.empty-content h2 {
  font-size: 1.8rem;
  color: #cdd6f4;
  margin-bottom: 8px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden; /* 新增：水平方向绝不撑开 */
  padding: 20px 16px;
  max-width: 100%; /* 新增：明确限制最大宽度 */
}

.load-more {
  text-align: center;
  padding: 10px;
  margin-bottom: 10px;
}

.load-more-text {
  font-size: 0.8rem;
  color: #6c7086;
  opacity: 0.7;
}

/* ── Message rows ── */
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 16px;
  width: 100%;
  box-sizing: border-box;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.system {
  justify-content: center;
}

/* ── Avatars ── */
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.ai-avatar {
  background: #89b4fa;
  color: #1e1e2e;
}

.user-avatar {
  background: #a6e3a1;
  color: #1e1e2e;
}

/* ── Bubbles ── */
.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 0.9rem;
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-all; /* 新增：强制断词，防止长字符串溢出 */
  overflow-x: auto; /* 新增：万一溢出，可横向滚动而非撑开布局 */
  flex-shrink: 0;
}

.ai-bubble {
  background: #313244;
  color: #cdd6f4;
  border-top-left-radius: 4px;
}

.user-bubble {
  background: #313244;
  color: #cdd6f4;
  border-top-right-radius: 4px;
}

/* ── Message source badge ── */
.source-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.7rem;
}

.source-badge.wechat {
  color: #07C160;
}

.source-icon {
  font-size: 0.8rem;
}

.source-label {
  opacity: 0.8;
}

/* ── WeChat message indicator ── */
.bubble.wechat {
  border-left: 3px solid #07C160;
  margin-left: -3px;
  padding-left: 12px;
}

/* 气泡内容（markdown 渲染后的 HTML） */
.bubble-content {
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-all; /* 新增 */
  overflow-x: auto; /* 新增 */
}

.bubble-content :deep(code) {
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 5px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em;
  word-break: break-all; /* 新增：代码块也允许断词 */
  white-space: pre-wrap; /* 保留原有格式但允许换行 */
}

/* ── System message ── */
.system-msg {
  background: #f38ba822;
  color: #f38ba8;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
}

/* ── Summary pill ── */
.summary-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #89b4fa18;
  border: 1px solid #89b4fa33;
  border-radius: 8px;
  padding: 8px 14px;
  margin: 8px 0;
  font-size: 0.82rem;
  color: #89b4fa;
  cursor: pointer;
  transition: background 0.2s;
  width: fit-content;
  max-width: 90%;
}
.summary-pill:hover {
  background: #89b4fa28;
}
.summary-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
}
.summary-text {
  flex: 1;
  line-height: 1.4;
}
.summary-close {
  font-size: 1.1rem;
  color: #89b4fa88;
  flex-shrink: 0;
  padding: 0 2px;
}
.summary-close:hover {
  color: #89b4fa;
}

/* ── Tool calls ── */
.tool-calls {
  margin-top: 8px;
}

.tool-call {
  background: #1e1e2e;
  border: 1px solid #45475a;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 6px;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.tool-name {
  font-family: monospace;
  font-size: 0.8rem;
  color: #89b4fa;
}

.tool-status {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.tool-status.running { background: #f9e2af33; color: #f9e2af; }
.tool-status.done { background: #a6e3a133; color: #a6e3a1; }
.tool-status.error { background: #f38ba833; color: #f38ba8; }

.tool-result {
  font-size: 0.75rem;
  color: #a6adc8;
  margin: 4px 0 0;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

/* ── Typing indicator ── */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #585b70;
  animation: bounce 1.4s infinite both;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

/* ── Horse Animation ── */
.horse-animation {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.running-horse-gif {
  width: 200px;
  height: auto;
  filter: drop-shadow(0 6px 12px rgba(0,0,0,0.25));
  transform: scaleX(-1);
  image-rendering: optimizeQuality;
  will-change: transform;
}

/* ── Pending queue ── */
.pending-queue {
  padding: 8px 16px;
  background: #f9e2af22;
  border-top: 1px solid #f9e2af;
}

.pending-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f9e2af;
  font-size: 0.85rem;
}

.pending-icon {
  font-size: 1rem;
}

.queue-items {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #313244;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #a6adc8;
}

.queue-index {
  color: #6c7086;
  font-weight: 500;
}

.queue-preview {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-remove-btn {
  background: transparent;
  border: none;
  color: #f38ba8;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.queue-remove-btn:hover {
  background: #f38ba822;
  border-radius: 4px;
}

/* ── Input area ── */
.input-area {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 12px 16px 16px;
  border-top: 1px solid #313244;
  min-height: 60px;
  max-height: 300px;
}

.resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
  cursor: ns-resize;
  background: transparent;
  z-index: 10;
}

.resize-handle:hover {
  background: #45475a;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #1e1e2e;
  border: 1px solid #313244;
  border-radius: 12px;
  padding: 8px 12px;
  flex: 1;
}

.input-wrapper textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #cdd6f4;
  font-size: 0.9rem;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  height: 100%;
}

.input-wrapper textarea::placeholder {
  color: #585b70;
}

.voice-toggle-btn {
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 6px;
  cursor: pointer;
  color: #585b70;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.voice-toggle-btn:hover {
  color: #cdd6f4;
  background: rgba(255,255,255,0.06);
}

.voice-toggle-btn.active {
  color: #a6e3a1;
  background: rgba(166,227,161,0.1);
}

.voice-toggle-btn.active:hover {
  background: rgba(166,227,161,0.18);
}

.send-btn {
  background: #89b4fa;
  border: none;
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  color: #1e1e2e;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  opacity: 0.8;
}

.send-btn.is-loading {
  background: #f38ba8;
}

.send-btn.is-loading:hover {
  background: #eba0ac;
}
</style>
