<template>
  <div class="memory-manager">
    <div class="memory-header">
      <h3>🧠 记忆管理</h3>
      <button class="btn btn-refresh" @click="loadMemories" :disabled="loading">
        {{ loading ? '加载中...' : '🔄 刷新' }}
      </button>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div class="memory-types">
      <div 
        v-for="memory in memories" 
        :key="memory.id"
        class="memory-card"
        :class="{ active: selectedMemory?.id === memory.id }"
      >
        <div class="memory-card-header" @click="selectMemory(memory)">
          <div class="memory-title">
            <span class="memory-icon">{{ getMemoryIcon(memory.id) }}</span>
            <span class="memory-name">{{ memory.name }}</span>
          </div>
          <div class="memory-meta">
            <span v-if="memory.exists" class="memory-size">{{ formatSize(memory.size) }}</span>
            <span v-else class="memory-empty">未创建</span>
          </div>
        </div>
        <div class="memory-card-body">
          <p class="memory-description">{{ memory.description }}</p>
        </div>
        <div class="memory-card-footer">
          <button 
            class="btn btn-view" 
            @click="viewMemory(memory)"
            :disabled="!memory.exists"
          >
            👁️ 查看
          </button>
          <button 
            class="btn btn-edit" 
            @click="editMemory(memory)"
            :disabled="!memory.exists || memory.id === 'database'"
          >
            ✏️ 编辑
          </button>
          <button 
            class="btn btn-delete-all" 
            @click="confirmDeleteAll(memory)"
            :disabled="!memory.exists"
          >
            🗑️ 清空
          </button>
        </div>
      </div>
    </div>

    <!-- Memory Content Modal (with entries) -->
    <div v-if="showContentModal" class="modal-overlay" @click.self="closeContentModal">
      <div class="modal-content memory-content-modal">
        <div class="modal-header">
          <h2>{{ getMemoryIcon(selectedMemory?.id) }} {{ selectedMemory?.name }}</h2>
          <button class="close-btn" @click="closeContentModal">×</button>
        </div>
        <div class="modal-body">
          <div v-if="loadingContent" class="loading">加载中...</div>
          <div v-else-if="memoryEntries.length > 0" class="memory-entries">
            <div 
              v-for="(entry, index) in memoryEntries" 
              :key="index"
              class="memory-entry"
            >
              <div class="entry-header">
                <span class="entry-index">#{{ index + 1 }}</span>
                <button 
                  class="btn btn-delete-entry" 
                  @click="deleteEntry(index)"
                  title="删除此条记录"
                >
                  🗑️
                </button>
              </div>
              <pre class="entry-content">{{ entry.content }}</pre>
            </div>
          </div>
          <div v-else class="empty-message">暂无记忆记录</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeContentModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- Edit Memory Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content memory-edit-modal">
        <div class="modal-header">
          <h2>✏️ 编辑 {{ selectedMemory?.name }}</h2>
          <button class="close-btn" @click="closeEditModal">×</button>
        </div>
        <div class="modal-body">
          <textarea 
            v-model="editContent" 
            class="memory-editor"
            placeholder="输入记忆内容...（多条记忆用 § 分隔）"
          ></textarea>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeEditModal">取消</button>
          <button class="btn btn-primary" @click="saveMemory" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Memory {
  id: string
  name: string
  file: string
  path: string
  exists: boolean
  size: number
  description: string
}

interface MemoryEntry {
  index: number
  content: string
  raw: string
}

const memories = ref<Memory[]>([])
const selectedMemory = ref<Memory | null>(null)
const loading = ref(false)
const error = ref('')
const memoryContent = ref('')
const memoryEntries = ref<MemoryEntry[]>([])
const loadingContent = ref(false)
const showContentModal = ref(false)
const showEditModal = ref(false)
const editContent = ref('')
const saving = ref(false)

const backendUrl = 'http://localhost:8765'

function getMemoryIcon(id: string): string {
  const icons: Record<string, string> = {
    project: '📝',
    user: '👤',
    soul: '🤖',
    database: '💾'
  }
  return icons[id] || '📄'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function loadMemories() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`${backendUrl}/api/memories`)
    const data = await response.json()
    memories.value = data.memories
  } catch (e: any) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

function selectMemory(memory: Memory) {
  selectedMemory.value = memory
}

async function viewMemory(memory: Memory) {
  selectedMemory.value = memory
  showContentModal.value = true
  loadingContent.value = true
  memoryContent.value = ''
  memoryEntries.value = []
  
  try {
    const response = await fetch(`${backendUrl}/api/memories/${memory.id}/entries`)
    const data = await response.json()
    memoryEntries.value = data.entries || []
  } catch (e: any) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loadingContent.value = false
  }
}

async function editMemory(memory: Memory) {
  selectedMemory.value = memory
  showEditModal.value = true
  loadingContent.value = true
  editContent.value = ''
  
  try {
    const response = await fetch(`${backendUrl}/api/memories/${memory.id}`)
    const data = await response.json()
    editContent.value = data.content || ''
  } catch (e: any) {
    editContent.value = `加载失败: ${e.message}`
  } finally {
    loadingContent.value = false
  }
}

async function deleteEntry(entryIndex: number) {
  if (!selectedMemory.value) return
  if (!confirm(`确定要删除第 ${entryIndex + 1} 条记录吗？`)) return
  
  try {
    const response = await fetch(
      `${backendUrl}/api/memories/${selectedMemory.value.id}/entries/${entryIndex}`,
      { method: 'DELETE' }
    )
    const data = await response.json()
    if (data.status === 'ok') {
      await viewMemory(selectedMemory.value)
    } else {
      alert('删除失败')
    }
  } catch (e: any) {
    alert(`删除失败: ${e.message}`)
  }
}

async function confirmDeleteAll(memory: Memory) {
  if (!confirm(`确定要清空 ${memory.name} 的所有内容吗？此操作不可恢复。`)) return
  
  try {
    const response = await fetch(`${backendUrl}/api/memories/${memory.id}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.status === 'ok') {
      await loadMemories()
    } else {
      alert('清空失败')
    }
  } catch (e: any) {
    alert(`清空失败: ${e.message}`)
  }
}

async function saveMemory() {
  if (!selectedMemory.value) return
  
  saving.value = true
  try {
    const response = await fetch(`${backendUrl}/api/memories/${selectedMemory.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: editContent.value })
    })
    const data = await response.json()
    if (data.status === 'ok') {
      closeEditModal()
      await loadMemories()
    } else {
      alert('保存失败')
    }
  } catch (e: any) {
    alert(`保存失败: ${e.message}`)
  } finally {
    saving.value = false
  }
}

function closeContentModal() {
  showContentModal.value = false
  memoryContent.value = ''
  memoryEntries.value = []
}

function closeEditModal() {
  showEditModal.value = false
  editContent.value = ''
}

onMounted(() => {
  loadMemories()
})
</script>

<style scoped>
.memory-manager {
  padding: 16px;
}

.memory-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.memory-header h3 {
  margin: 0;
  color: #cdd6f4;
}

.memory-types {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.memory-card {
  background: #1e1e2e;
  border: 1px solid #313244;
  border-radius: 8px;
  overflow: hidden;
}

.memory-card.active {
  border-color: #89b4fa;
}

.memory-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #313244;
  cursor: pointer;
}

.memory-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.memory-icon {
  font-size: 1.2rem;
}

.memory-name {
  font-weight: 600;
  color: #cdd6f4;
}

.memory-meta {
  font-size: 0.85rem;
  color: #a6adc8;
}

.memory-empty {
  color: #f38ba8;
}

.memory-card-body {
  padding: 12px;
}

.memory-description {
  margin: 0;
  font-size: 0.85rem;
  color: #a6adc8;
  line-height: 1.5;
}

.memory-card-footer {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #313244;
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-refresh {
  background: #45475a;
  color: #cdd6f4;
}

.btn-view {
  background: #89b4fa;
  color: #1e1e2e;
}

.btn-edit {
  background: #a6e3a1;
  color: #1e1e2e;
}

.btn-delete-all {
  background: #fab387;
  color: #1e1e2e;
}

.btn-delete-entry {
  background: transparent;
  color: #f38ba8;
  padding: 4px 8px;
  font-size: 0.8rem;
}

.btn-delete-entry:hover {
  background: #f38ba822;
}

.btn-secondary {
  background: #45475a;
  color: #cdd6f4;
}

.btn-primary {
  background: #89b4fa;
  color: #1e1e2e;
}

.error-message {
  padding: 12px;
  background: #f38ba822;
  border: 1px solid #f38ba8;
  border-radius: 6px;
  color: #f38ba8;
  margin-bottom: 16px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1e1e2e;
  border-radius: 12px;
  max-width: 90%;
  max-height: 90%;
  display: flex;
  flex-direction: column;
}

.memory-content-modal,
.memory-edit-modal {
  width: 800px;
  height: 600px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #313244;
}

.modal-header h2 {
  margin: 0;
  color: #cdd6f4;
}

.close-btn {
  background: none;
  border: none;
  color: #a6adc8;
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.memory-content {
  background: #313244;
  padding: 16px;
  border-radius: 8px;
  color: #cdd6f4;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  max-height: 100%;
  overflow-y: auto;
}

.memory-editor {
  width: 100%;
  height: 100%;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 8px;
  color: #cdd6f4;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.6;
  padding: 16px;
  resize: none;
}

.memory-entries {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.memory-entry {
  background: #313244;
  border-radius: 8px;
  overflow: hidden;
}

.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #45475a;
}

.entry-index {
  font-weight: 600;
  color: #89b4fa;
}

.entry-content {
  margin: 0;
  padding: 12px;
  color: #cdd6f4;
  font-size: 0.85rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.empty-message {
  text-align: center;
  color: #a6adc8;
  padding: 40px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #313244;
}

.loading {
  text-align: center;
  color: #a6adc8;
  padding: 40px;
}
</style>
