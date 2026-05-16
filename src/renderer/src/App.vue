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
        <div class="connection-status" :class="{ connected: chatStore.isConnected }">
          <span class="status-dot"></span>
          {{ chatStore.isConnected ? '已连接' : '未连接' }}
        </div>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

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

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #a6adc8;
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

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #181825;
}
</style>
