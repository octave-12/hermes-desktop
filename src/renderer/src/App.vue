<template>
  <div id="app-container">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="header-row">
          <img src="@/assets/horse-running.gif" alt="Hermes" class="logo-horse-icon" />
          <h1 class="app-title">Hermes</h1>
          <div class="header-actions">
            <button class="new-chat-icon-btn" @click="createNewSession" title="新对话">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
            </button>
            <button class="search-toggle-btn" @click="showSearch = !showSearch" title="搜索会话">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </button>
            <button class="collapse-btn" @click="sidebarCollapsed = true" title="收起侧边栏">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </button>
          </div>
        </div>
        <div v-if="showSearch" class="search-box">
          <div class="search-input-wrapper">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="搜索会话..." 
              class="search-input"
            />
            <button class="search-close-btn" @click="showSearch = false; searchQuery = ''" title="关闭">
              ×
            </button>
          </div>
        </div>
      </div>
      <div class="session-list">
        <div
          v-for="session in filteredSessions"
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
            <div class="session-menu">
              <button
                class="menu-btn"
                @click.stop="toggleMenu(session.id)"
                title="更多"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <circle cx="12" cy="5" r="2"/>
                  <circle cx="12" cy="12" r="2"/>
                  <circle cx="12" cy="19" r="2"/>
                </svg>
              </button>
              <div v-if="activeMenu === session.id" class="menu-dropdown">
                <button class="menu-item" @click.stop="startRename(session.id, session.title)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  <span>重命名</span>
                </button>
                <button class="menu-item delete" @click.stop="deleteSession(session.id)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                  <span>删除</span>
                </button>
              </div>
            </div>
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
          <div class="status-group">
            <div class="connection-status" :class="{ connected: chatStore.isConnected, reconnecting: chatStore.isReconnecting }">
              <span class="status-dot"></span>
              <span class="status-text">
                {{ chatStore.isConnected ? '在线' : (chatStore.isReconnecting ? '重连' : '离线') }}
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
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            </button>
          </div>
          <div class="model-info" v-if="currentModelName" title="当前模型">
            <span class="model-icon">
              <img src="@/assets/horse-running.gif" alt="Horse" class="model-horse-icon" />
            </span>
            <span class="model-name">{{ currentModelName }}</span>
          </div>
          <button class="settings-btn" @click="showSettings = true" title="设置">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <button v-if="sidebarCollapsed" class="sidebar-toggle" @click="sidebarCollapsed = false" title="展开侧边栏">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
      <router-view />
    </main>
    
    <!-- Settings Modal -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import SettingsModal from '@/components/SettingsModal.vue'
import { fetchWithAuth, getWsUrl } from '@/utils/api'

const chatStore = useChatStore()
const showSettings = ref(false)
const currentModelName = ref('')
const sidebarCollapsed = ref(false)
const showSearch = ref(false)
const searchQuery = ref('')

const filteredSessions = computed(() => {
  if (!searchQuery.value.trim()) {
    return chatStore.sessions
  } else {
    const query = searchQuery.value.toLowerCase()
    return chatStore.sessions.filter(s => 
      s.title.toLowerCase().includes(query) ||
      (s.lastAiMessage && s.lastAiMessage.toLowerCase().includes(query))
    )
  }
})

// Reconnect WebSocket
function reconnect() {
  if (!chatStore.isConnected && !chatStore.isReconnecting) {
    chatStore.disconnect()
    chatStore.isReconnecting = true
    setTimeout(() => {
      chatStore.connectWebSocket(getWsUrl())
    }, 500)
  }
}

// Refresh model name from backend
async function refreshModelName() {
  try {
    // Get model list
    const modelsResponse = await fetchWithAuth('/api/models')
    if (!modelsResponse.ok) {
      currentModelName.value = 'Unknown'
      return
    }
    
    const modelsData = await modelsResponse.json()
    const models = modelsData.models || []
    
    // Get current model config
    const configResponse = await fetchWithAuth('/api/config')
    if (!configResponse.ok) {
      currentModelName.value = 'Unknown'
      return
    }
    
    const config = await configResponse.json()
    
    // Find model name from list
    const model = models.find((m: any) => m.id === config.model)
    currentModelName.value = model?.name || config.model || 'Unknown'
  } catch (error) {
    console.error('Failed to load model config:', error)
    currentModelName.value = 'Unknown'
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
watch(showSettings, async (newVal) => {
  if (!newVal) {
    // Modal closed, refresh model name
    await refreshModelName()
  }
})

const renamingId = ref<string | null>(null)
const renameText = ref('')
const renameInputRef = ref<HTMLInputElement[]>()
const activeMenu = ref<string | null>(null)

function createNewSession() {
  chatStore.createSession()
}

function toggleMenu(sessionId: string) {
  activeMenu.value = activeMenu.value === sessionId ? null : sessionId
}

function deleteSession(sessionId: string) {
  chatStore.deleteSession(sessionId)
  activeMenu.value = null
}

function startRename(id: string, currentTitle: string) {
  activeMenu.value = null
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

// Close menu when clicking outside
function handleClickOutside(e: MouseEvent) {
  if (activeMenu.value && !(e.target as HTMLElement).closest('.session-menu')) {
    activeMenu.value = null
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
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
  transition: width 0.3s ease, opacity 0.3s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 0;
  border-right: none;
  opacity: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #313244;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-horse-icon {
  width: 28px;
  height: 28px;
  margin-left: -5px;
  margin-top: 2px;
}

.header-actions {
  display: flex;
  gap: 6px;
  position: relative;
  right: -8px;
}

.new-chat-icon-btn,
.search-toggle-btn,
.collapse-btn {
  background: transparent;
  border: none;
  color: #6c7086;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.new-chat-icon-btn:hover,
.search-toggle-btn:hover,
.collapse-btn:hover {
  background: #45475a;
  color: #cdd6f4;
}

.search-box {
  margin: 13px 0 0 0;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 8px 32px 8px 10px;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 6px;
  color: #cdd6f4;
  font-size: 0.85rem;
}

.search-input:focus {
  outline: none;
  border-color: #89b4fa;
}

.search-close-btn {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  color: #6c7086;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.search-close-btn:hover {
  color: #f38ba8;
}

.app-title {
  font-size: 1.2rem;
  color: #cdd6f4;
  margin: 0;
  font-weight: 600;
  margin-left: -13px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  padding-right: 4px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #a6adc8;
  font-size: 0.85rem;
  line-height: 1.4;
  margin-bottom: 2px;
  transition: background 0.2s;
  gap: 8px;
  flex-shrink: 0;
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

.session-menu {
  position: relative;
  flex-shrink: 0;
}

.menu-btn {
  display: none;
  background: none;
  border: none;
  color: #6c7086;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  line-height: 0;
}

.session-item:hover .menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-btn:hover {
  color: #cdd6f4;
  background: #45475a;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 100;
  min-width: 120px;
  padding: 4px;
  margin-top: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  background: none;
  border: none;
  color: #a6adc8;
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.85rem;
  text-align: left;
}

.menu-item:hover {
  background: #45475a;
  color: #cdd6f4;
}

.menu-item.delete {
  color: #f38ba8;
}

.menu-item.delete:hover {
  background: #f38ba822;
  color: #f38ba8;
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
  padding: 8px 16px;
  border-top: 1px solid #313244;
}

.footer-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: #a6adc8;
  flex-shrink: 0;
  transition: all 0.2s;
}

.connection-status.connected {
  color: #a6e3a1;
}

.connection-status.reconnecting {
  color: #f9e2af;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: #cdd6f4;
  flex: 1;
  min-width: 0;
  cursor: default;
}

.model-icon {
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-horse-icon {
  width: 20px;
  height: 20px;
  margin-top: 2px;
}

.model-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
  color: #89b4fa;
}

.status-dot {
  width: 6px;
  height: 6px;
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
  color: #89b4fa;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
  line-height: 0;
}

.settings-btn:hover {
  color: #b4befe;
  transform: rotate(45deg);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #181825;
  position: relative;
}

.sidebar-toggle {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  background: rgba(49, 50, 68, 0.6);
  border: 1px solid rgba(69, 71, 90, 0.6);
  color: #89b4fa;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
}

.sidebar-toggle:hover {
  background: rgba(69, 71, 90, 0.8);
  color: #b4befe;
}
</style>
