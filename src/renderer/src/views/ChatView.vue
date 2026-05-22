<template>
  <div class="chat-view">
    <!-- Empty state -->
    <div v-if="!currentSession || currentSession.messages.length === 0" class="empty-state">
      <div class="empty-content">
        <div class="horse-animation">
          <svg width="150" height="100" viewBox="0 0 150 100" class="running-horse">
            <!-- Horse Body -->
            <ellipse cx="75" cy="50" rx="35" ry="18" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="1"/>
            <!-- Neck -->
            <path d="M50 45 Q45 30 50 18 Q55 15 60 18 Q65 25 55 45" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="1"/>
            <!-- Head -->
            <path d="M50 18 Q45 12 40 15 L35 22 Q38 28 45 25 L50 22 Z" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="1"/>
            <!-- Ear -->
            <path d="M45 15 Q43 8 48 10 Q50 12 48 16 Z" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="0.5"/>
            <!-- Eye -->
            <circle cx="42" cy="20" r="2" fill="#333"/>
            <circle cx="41.5" cy="19.5" r="0.8" fill="#fff"/>
            <!-- Mane -->
            <path class="mane" d="M55 20 Q52 15 58 12 Q62 16 55 22" fill="#ddd"/>
            <path class="mane" d="M58 25 Q55 20 61 18 Q65 22 58 27" fill="#ddd"/>
            <path class="mane" d="M60 30 Q57 25 63 23 Q67 27 60 32" fill="#ddd"/>
            <!-- Front Legs -->
            <path class="leg-front-left" d="M55 65 L50 88 L56 88 L58 65" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="0.5"/>
            <path class="leg-front-right" d="M62 65 L65 88 L71 88 L65 65" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="0.5"/>
            <!-- Back Legs -->
            <path class="leg-back-left" d="M85 65 L78 88 L84 88 L88 65" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="0.5"/>
            <path class="leg-back-right" d="M92 65 L98 88 L104 88 L95 65" fill="#f5f5f5" stroke="#e0e0e0" stroke-width="0.5"/>
            <!-- Hooves -->
            <ellipse cx="53" cy="89" rx="4" ry="2" fill="#333"/>
            <ellipse cx="68" cy="89" rx="4" ry="2" fill="#333"/>
            <ellipse cx="81" cy="89" rx="4" ry="2" fill="#333"/>
            <ellipse cx="101" cy="89" rx="4" ry="2" fill="#333"/>
            <!-- Tail -->
            <path class="tail" d="M110 50 Q125 45 130 55 Q128 65 115 60 Q120 55 110 52" fill="#ddd"/>
            <!-- Tail strands -->
            <path class="tail" d="M115 55 Q125 52 128 60" stroke="#ccc" stroke-width="1" fill="none"/>
            <path class="tail" d="M115 58 Q123 58 126 65" stroke="#ccc" stroke-width="1" fill="none"/>
          </svg>
        </div>
        <h2>Hermes Agent</h2>
        <p>开始一段新对话，或从左侧选择历史会话</p>
      </div>
    </div>

    <!-- Messages -->
    <div v-else class="messages-container" ref="messagesContainer">
      <div
        v-for="msg in currentSession.messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
        <!-- AI message: avatar left, bubble left -->
        <template v-if="msg.role === 'assistant'">
          <div class="avatar ai-avatar">H</div>
          <div class="bubble ai-bubble">
            <div class="bubble-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.toolCalls?.length" class="tool-calls">
              <div v-for="(tc, idx) in msg.toolCalls" :key="idx" class="tool-call">
                <div class="tool-header">
                  <span class="tool-name">{{ tc.name }}</span>
                  <span class="tool-status" :class="tc.status">{{ tc.status }}</span>
                </div>
                <pre v-if="tc.result" class="tool-result">{{ tc.result }}</pre>
              </div>
            </div>
          </div>
        </template>

        <!-- User message: bubble right -->
        <template v-else-if="msg.role === 'user'">
          <div class="bubble user-bubble">
            <div class="bubble-content">{{ msg.content }}</div>
          </div>
          <div class="avatar user-avatar">Me</div>
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
    <div v-if="pendingCount > 0" class="pending-queue">
      <div class="pending-header">
        <span class="pending-icon">⏳</span>
        <span>待执行消息: {{ pendingCount }} 条</span>
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
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'

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

const currentSession = computed(() => chatStore.getCurrentSession())

const pendingCount = computed(() => {
  if (!currentSession.value) return 0
  const pending = chatStore.pendingMessages.get(currentSession.value.id)
  return pending?.length || 0
})

function renderMarkdown(content: string): string {
  if (!content) return ''
  return content
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
  scrollToBottom()
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
  padding: 20px 16px;
}

/* ── Message rows ── */
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 16px;
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
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 0.9rem;
  word-wrap: break-word;
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

.bubble-content :deep(code) {
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 5px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em;
}

/* ── System message ── */
.system-msg {
  background: #f38ba822;
  color: #f38ba8;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
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

.running-horse {
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
}

.running-horse .leg-front-left {
  animation: legRun1 0.4s ease-in-out infinite;
  transform-origin: 55px 65px;
}

.running-horse .leg-front-right {
  animation: legRun2 0.4s ease-in-out infinite;
  transform-origin: 62px 65px;
}

.running-horse .leg-back-left {
  animation: legRun2 0.4s ease-in-out infinite;
  transform-origin: 85px 65px;
}

.running-horse .leg-back-right {
  animation: legRun1 0.4s ease-in-out infinite;
  transform-origin: 92px 65px;
}

.running-horse .mane {
  animation: maneFlow 0.3s ease-in-out infinite;
}

.running-horse .tail {
  animation: tailWag 0.5s ease-in-out infinite;
  transform-origin: 110px 50px;
}

@keyframes legRun1 {
  0%, 100% { transform: rotate(-20deg); }
  50% { transform: rotate(20deg); }
}

@keyframes legRun2 {
  0%, 100% { transform: rotate(20deg); }
  50% { transform: rotate(-20deg); }
}

@keyframes maneFlow {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(-3px); }
}

@keyframes tailWag {
  0%, 100% { transform: rotate(-10deg); }
  50% { transform: rotate(10deg); }
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
