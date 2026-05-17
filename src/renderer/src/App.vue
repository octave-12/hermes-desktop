<template>
  <div id="app-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="app-title">Hermes</h1>
        <button class="new-chat-btn" @click="createNewSession">+ 新对话</button>
      </div>
      <div class="session-list">
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === chatStore.currentSessionId }"
          @click="chatStore.switchSession(session.id)"
          @dblclick.stop="startRename(session.id, session.title)"
        >
          <!-- Normal display -->
          <template v-if="renamingId !== session.id">
            <div class="session-info">
              <span class="session-title">{{ session.title }}</span>
              <span v-if="session.lastAiMessage" class="session-preview">{{ truncateText(session.lastAiMessage, 40) }}</span>
            </div>
            <button
              class="delete-btn"
              @click.stop="chatStore.deleteSession(session.id)"
              title="删除会话"
            >×</button>
          </template>
          <!-- Rename input -->
          <template v-else>
            <input
              class="rename-input"
              v-model="renameText"
              @keydown.enter="confirmRename(session.id)"
              @keydown.escape="cancelRename"
              @blur="confirmRename(session.id)"
              ref="renameInputRef"
              @click.stop
            />
          </template>
        </div>
      </div>
      <div class="sidebar-footer">
        <div class="footer-row">
          <div class="connection-status" :class="{ connected: chatStore.isConnected, reconnecting: chatStore.isReconnecting }">
            <span class="status-dot"></span>
            <span class="status-text">
              {{ chatStore.isConnected ? '已连接' : (chatStore.isReconnecting ? '重连中...' : '未连接') }}
            </span>
          </div>
          <button 
            v-if="!chatStore.isConnected" 
            class="refresh-btn" 
            @click="reconnect" 
            :disabled="chatStore.isReconnecting"
            :class="{ rotating: chatStore.isReconnecting }"
            title="重新连接"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
          <div class="model-info" v-if="currentModelName">
            <span class="model-label">🤖</span>
            <span class="model-name">{{ currentModelName }}</span>
          </div>
          <button class="settings-btn" @click="showSettings = true" title="设置">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
    
    <!-- Settings Modal -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import SettingsModal from '@/components/SettingsModal.vue'

const chatStore = useChatStore()
const showSettings = ref(false)
const currentModelName = ref('')

// Reconnect WebSocket
function reconnect() {
  if (!chatStore.isConnected && !chatStore.isReconnecting) {
    console.log('[App] Manual reconnect triggered')
    chatStore.disconnect()
    chatStore.isReconnecting = true
    setTimeout(() => {
      chatStore.connectWebSocket('ws://localhost:8765/ws')
    }, 500)
  }
}

// Refresh model name from backend
async function refreshModelName() {
  try {
    const response = await fetch('http://localhost:8765/api/config')
    if (response.ok) {
      const config = await response.json()
      const modelMap: Record<string, string> = {
        'gpt-4o': 'GPT-4o',
        'gpt-4o-mini': 'GPT-4o Mini',
        'gpt-3.5-turbo': 'GPT-3.5 Turbo',
        'claude-3-5-sonnet': 'Claude 3.5',
        'claude-3-opus': 'Claude 3 Opus',
        'qwen-max': '通义千问 Max',
        'qwen-plus': '通义千问 Plus',
        'deepseek-chat': 'DeepSeek Chat',
        'glm-4': '智谱 GLM-4'
      }
      currentModelName.value = modelMap[config.model] || config.model
    }
  } catch (error) {
    console.error('Failed to load model config:', error)
  }
}

// Load current model on mount
onMounted(async () => {
  await refreshModelName()
  
  try {
    const url = await (window as any).api.getBackendUrl()
    chatStore.connectWebSocket(url)
  } catch (e) {
    console.error('Failed to get backend URL:', e)
  }
})

// Watch settings modal close to refresh model name
import { watch } from 'vue'
watch(showSettings, async (newVal) => {
  if (!newVal) {
    // Modal closed, refresh model name
    await refreshModelName()
  }
})

const renamingId = ref<string | null>(null)
const renameText = ref('')
const renameInputRef = ref<HTMLInputElement[]>()

function createNewSession() {
  chatStore.createSession()
}

function startRename(id: string, currentTitle: string) {
  renamingId.value = id
  renameText.value = currentTitle
  nextTick(() => {
    if (renameInputRef.value && renameInputRef.value.length > 0) {
      renameInputRef.value[0].focus()
      renameInputRef.value[0].select()
    }
  })
}

function confirmRename(id: string) {
  const title = renameText.value.trim()
  if (title && renamingId.value === id) {
    chatStore.renameSession(id, title)
  }
  renamingId.value = null
}

function cancelRename() {
  renamingId.value = null
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
</script>

<style scoped>
#app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  background: #1e1e2e;
  border-right: 1px solid #313244;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #313244;
}

.app-title {
  font-size: 1.2rem;
  color: #cdd6f4;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: #45475a;
  color: #cdd6f4;
  border: 1px solid #585b70;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.new-chat-btn:hover {
  background: #585b70;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #a6adc8;
  font-size: 0.85rem;
  margin-bottom: 2px;
  transition: background 0.2s;
  gap: 8px;
}

.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-title {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.session-preview {
  font-size: 0.75rem;
  color: #6c7086;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.delete-btn {
  display: none;
  background: none;
  border: none;
  color: #6c7086;
  cursor: pointer;
  font-size: 1rem;
  padding: 0 4px;
  line-height: 1;
  border-radius: 4px;
  flex-shrink: 0;
}

.delete-btn:hover {
  color: #f38ba8;
  background: #f38ba822;
}

.session-item:hover .delete-btn {
  display: block;
}

.rename-input {
  flex: 1;
  min-width: 0;
  background: #11111b;
  border: 1px solid #89b4fa;
  border-radius: 4px;
  color: #cdd6f4;
  font-size: 0.85rem;
  padding: 4px 8px;
  outline: none;
}

.session-item:hover {
  background: #313244;
}

.session-item.active {
  background: #45475a;
  color: #cdd6f4;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #313244;
}

.footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #a6adc8;
  flex-shrink: 0;
  transition: opacity 0.2s;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: #6c7086;
  flex: 1;
  min-width: 0;
}

.model-label {
  font-size: 0.9rem;
}

.model-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
  color: #89b4fa;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f38ba8;
}

.connection-status.connected .status-dot {
  background: #a6e3a1;
}

.connection-status.reconnecting .status-dot {
  background: #f9e2af;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.refresh-btn {
  background: transparent;
  border: none;
  color: #f38ba8;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
  flex-shrink: 0;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(243, 139, 168, 0.1);
  color: #fab387;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-btn.rotating svg {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.settings-btn {
  background: transparent;
  border: none;
  color: #6c7086;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
  line-height: 0;
}

.settings-btn:hover {
  background: #313244;
  color: #cdd6f4;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #181825;
}
</style>
