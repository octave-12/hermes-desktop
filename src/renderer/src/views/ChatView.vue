<template>
  <div class="chat-view">
    <!-- Empty state -->
    <div v-if="!currentSession || currentSession.messages.length === 0" class="empty-state">
      <div class="empty-content">
        <div class="horse-gallery">
          <!-- Horse 1: Simple running horse -->
          <svg width="60" height="60" viewBox="0 0 100 100" class="horse-option">
            <path d="M75 45 Q80 40 85 45 L90 50 Q87 55 83 55 L75 52 Z" fill="#89b4fa"/>
            <path d="M75 45 Q73 35 77 28 L81 30 Q83 38 80 45 Z" fill="#89b4fa"/>
            <path d="M77 28 Q83 25 87 28 L89 32 Q85 35 81 33 Z" fill="#89b4fa"/>
            <circle cx="85" cy="30" r="2" fill="#1e1e2e"/>
            <path d="M77 52 L75 65 L78 65 L80 52" fill="#89b4fa"/>
            <path d="M83 52 L87 65 L90 65 L85 52" fill="#89b4fa"/>
            <path d="M73 52 L67 68 L70 68 L75 52" fill="#89b4fa"/>
            <path d="M79 52 L77 68 L80 68 L83 52" fill="#89b4fa"/>
            <path d="M90 50 Q97 48 100 55 Q98 60 93 58" fill="#89b4fa"/>
            <path d="M73 35 Q70 32 73 28 Q77 30 75 35 Z" fill="#89b4fa"/>
          </svg>
          
          <!-- Horse 2: Galloping horse -->
          <svg width="60" height="60" viewBox="0 0 100 100" class="horse-option">
            <ellipse cx="60" cy="50" rx="25" ry="12" fill="#a6e3a1"/>
            <path d="M40 50 Q38 38 42 30 L48 32 Q50 42 45 50 Z" fill="#a6e3a1"/>
            <path d="M42 30 Q50 26 55 30 L57 35 Q52 38 46 34 Z" fill="#a6e3a1"/>
            <circle cx="53" cy="32" r="2" fill="#1e1e2e"/>
            <path d="M45 58 L35 75 L40 75 L50 60" fill="#a6e3a1"/>
            <path d="M55 58 L65 75 L70 75 L60 60" fill="#a6e3a1"/>
            <path d="M70 55 L80 70 L85 70 L75 55" fill="#a6e3a1"/>
            <path d="M50 55 L45 70 L50 70 L55 58" fill="#a6e3a1"/>
            <path d="M85 52 Q95 48 98 56 Q96 62 88 58" fill="#a6e3a1"/>
            <path d="M38 40 Q32 35 36 28 Q42 32 40 40 Z" fill="#a6e3a1"/>
          </svg>
          
          <!-- Horse 3: Standing horse -->
          <svg width="60" height="60" viewBox="0 0 100 100" class="horse-option">
            <ellipse cx="55" cy="45" rx="20" ry="10" fill="#f9e2af"/>
            <path d="M40 45 Q38 32 42 24 L48 26 Q50 36 46 45 Z" fill="#f9e2af"/>
            <path d="M42 24 Q50 20 55 24 L57 28 Q52 32 46 28 Z" fill="#f9e2af"/>
            <circle cx="53" cy="26" r="2" fill="#1e1e2e"/>
            <path d="M40 52 L40 75 L45 75 L45 52" fill="#f9e2af"/>
            <path d="M50 52 L50 75 L55 75 L55 52" fill="#f9e2af"/>
            <path d="M60 52 L60 75 L65 75 L65 52" fill="#f9e2af"/>
            <path d="M70 52 L70 75 L75 75 L75 52" fill="#f9e2af"/>
            <path d="M75 45 Q85 42 88 50 Q86 56 78 52" fill="#f9e2af"/>
            <path d="M38 36 Q32 32 35 26 Q40 30 38 36 Z" fill="#f9e2af"/>
          </svg>
          
          <!-- Horse 4: Jumping horse -->
          <svg width="60" height="60" viewBox="0 0 100 100" class="horse-option">
            <ellipse cx="55" cy="35" rx="22" ry="10" fill="#f38ba8"/>
            <path d="M38 35 Q36 22 40 14 L46 16 Q48 26 44 35 Z" fill="#f38ba8"/>
            <path d="M40 14 Q48 10 53 14 L55 18 Q50 22 44 18 Z" fill="#f38ba8"/>
            <circle cx="51" cy="16" r="2" fill="#1e1e2e"/>
            <path d="M38 42 L25 60 L30 60 L42 45" fill="#f38ba8"/>
            <path d="M50 42 L55 60 L60 60 L55 45" fill="#f38ba8"/>
            <path d="M65 40 L80 55 L85 55 L70 42" fill="#f38ba8"/>
            <path d="M72 42 L75 58 L80 58 L75 45" fill="#f38ba8"/>
            <path d="M77 35 Q87 32 90 40 Q88 46 80 42" fill="#f38ba8"/>
            <path d="M36 26 Q30 22 33 16 Q38 20 36 26 Z" fill="#f38ba8"/>
          </svg>
          
          <!-- Horse 5: Trotting horse -->
          <svg width="60" height="60" viewBox="0 0 100 100" class="horse-option">
            <ellipse cx="60" cy="48" rx="23" ry="11" fill="#cba6f7"/>
            <path d="M42 48 Q40 35 44 27 L50 29 Q52 39 48 48 Z" fill="#cba6f7"/>
            <path d="M44 27 Q52 23 57 27 L59 31 Q54 35 48 31 Z" fill="#cba6f7"/>
            <circle cx="55" cy="29" r="2" fill="#1e1e2e"/>
            <path d="M45 55 L40 72 L45 72 L50 58" fill="#cba6f7"/>
            <path d="M55 55 L60 72 L65 72 L60 58" fill="#cba6f7"/>
            <path d="M68 55 L72 72 L77 72 L73 58" fill="#cba6f7"/>
            <path d="M75 55 L70 72 L75 72 L78 58" fill="#cba6f7"/>
            <path d="M83 48 Q93 45 96 53 Q94 59 86 55" fill="#cba6f7"/>
            <path d="M40 38 Q34 34 37 28 Q43 32 41 38 Z" fill="#cba6f7"/>
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
.horse-gallery {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  justify-content: center;
  flex-wrap: wrap;
}

.horse-option {
  cursor: pointer;
  transition: transform 0.2s, opacity 0.2s;
  opacity: 0.8;
}

.horse-option:hover {
  transform: scale(1.1);
  opacity: 1;
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
