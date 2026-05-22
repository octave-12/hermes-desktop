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
            @click="memory.id === 'database' ? viewDatabase() : viewMemory(memory)"
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

    <!-- Database Memory Modal -->
    <div v-if="showDbModal" class="modal-overlay" @click.self="closeDbModal">
      <div class="modal-content db-modal">
        <div class="modal-header">
          <h2>💾 SQLite 记忆数据库</h2>
          <button class="close-btn" @click="closeDbModal">×</button>
        </div>
        <div class="modal-body">
          <!-- Category filter -->
          <div class="db-toolbar">
            <select v-model="selectedCategory" @change="loadDbEntries" class="category-select">
              <option value="">全部分类</option>
              <option v-for="cat in dbCategories" :key="cat.category" :value="cat.category">
                {{ cat.category }} ({{ cat.count }})
              </option>
            </select>
            <button class="btn btn-primary" @click="showAddDbEntry = true">➕ 新增记忆</button>
          </div>
          
          <div v-if="loadingDb" class="loading">加载中...</div>
          <div v-else-if="dbEntries.length > 0" class="db-entries">
            <div v-for="entry in dbEntries" :key="entry.id" class="db-entry">
              <div class="db-entry-header">
                <div class="db-entry-meta">
                  <span class="db-entry-id">#{{ entry.id }}</span>
                  <span class="db-entry-category">{{ entry.category }}</span>
                  <span class="db-entry-importance">⭐{{ entry.importance }}</span>
                </div>
                <div class="db-entry-actions">
                  <button 
                    v-if="entry.content.length > 100" 
                    class="btn btn-sm btn-expand"
                    @click="toggleEntryExpand(entry.id)"
                    :title="expandedEntries.has(entry.id) ? '收起' : '展开'"
                  >
                    {{ expandedEntries.has(entry.id) ? '▲' : '▼' }}
                  </button>
                  <button class="btn btn-sm" @click="editDbEntry(entry)" title="编辑">✏️</button>
                  <button class="btn btn-sm btn-danger" @click="deleteDbEntry(entry.id)" title="删除">🗑️</button>
                </div>
              </div>
              <div class="db-entry-content-wrapper">
                <pre class="db-entry-content" :class="{ collapsed: !expandedEntries.has(entry.id) }">{{ 
                  expandedEntries.has(entry.id) ? entry.content : truncateContent(entry.content, 100) 
                }}</pre>
              </div>
              <div v-if="entry.tags?.length" class="db-entry-tags">
                <span v-for="tag in entry.tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-message">暂无记忆记录</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeDbModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- Add/Edit Database Entry Modal -->
    <div v-if="showAddDbEntry || editingDbEntry" class="modal-overlay" @click.self="closeDbEntryModal">
      <div class="modal-content db-entry-modal">
        <div class="modal-header">
          <h2>{{ editingDbEntry ? '✏️ 编辑记忆' : '➕ 新增记忆' }}</h2>
          <button class="close-btn" @click="closeDbEntryModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>内容</label>
            <textarea v-model="dbEntryForm.content" rows="5" placeholder="输入记忆内容..."></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>分类</label>
              <input v-model="dbEntryForm.category" placeholder="general" />
            </div>
            <div class="form-group">
              <label>重要性 (1-5)</label>
              <input v-model.number="dbEntryForm.importance" type="number" min="1" max="5" />
            </div>
          </div>
          <div class="form-group">
            <label>标签 (逗号分隔)</label>
            <input v-model="dbEntryForm.tagsInput" placeholder="tag1, tag2" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeDbEntryModal">取消</button>
          <button class="btn btn-primary" @click="saveDbEntry" :disabled="savingDb">
            {{ savingDb ? '保存中...' : '保存' }}
          </button>
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

interface DbEntry {
  id: number
  content: string
  category: string
  importance: number
  tags: string[]
  created_at: string
  updated_at: string
}

interface DbCategory {
  category: string
  count: number
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

// Database memory state
const showDbModal = ref(false)
const showAddDbEntry = ref(false)
const editingDbEntry = ref<DbEntry | null>(null)
const dbEntries = ref<DbEntry[]>([])
const dbCategories = ref<DbCategory[]>([])
const selectedCategory = ref('')
const loadingDb = ref(false)
const savingDb = ref(false)
const expandedEntries = ref(new Set<number>())
const dbEntryForm = ref({
  content: '',
  category: 'general',
  importance: 1,
  tagsInput: ''
})

const backendUrl = 'http://localhost:8765'

function truncateContent(content: string, maxLength: number): string {
  if (content.length <= maxLength) return content
  return content.substring(0, maxLength) + '...'
}

function toggleEntryExpand(entryId: number) {
  if (expandedEntries.value.has(entryId)) {
    expandedEntries.value.delete(entryId)
  } else {
    expandedEntries.value.add(entryId)
  }
  // Force reactivity update
  expandedEntries.value = new Set(expandedEntries.value)
}

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

// Database memory functions
async function viewDatabase() {
  showDbModal.value = true
  await loadDbCategories()
  await loadDbEntries()
}

async function loadDbCategories() {
  try {
    const response = await fetch(`${backendUrl}/api/memories/database/categories`)
    const data = await response.json()
    dbCategories.value = data.categories || []
  } catch (e: any) {
    console.error('Failed to load categories:', e)
  }
}

async function loadDbEntries() {
  loadingDb.value = true
  try {
    const url = selectedCategory.value
      ? `${backendUrl}/api/memories/database/entries?category=${selectedCategory.value}`
      : `${backendUrl}/api/memories/database/entries`
    const response = await fetch(url)
    const data = await response.json()
    dbEntries.value = data.entries || []
  } catch (e: any) {
    console.error('Failed to load entries:', e)
  } finally {
    loadingDb.value = false
  }
}

function closeDbModal() {
  showDbModal.value = false
  dbEntries.value = []
  selectedCategory.value = ''
}

function editDbEntry(entry: DbEntry) {
  editingDbEntry.value = entry
  dbEntryForm.value = {
    content: entry.content,
    category: entry.category,
    importance: entry.importance,
    tagsInput: entry.tags?.join(', ') || ''
  }
}

function closeDbEntryModal() {
  showAddDbEntry.value = false
  editingDbEntry.value = null
  dbEntryForm.value = {
    content: '',
    category: 'general',
    importance: 1,
    tagsInput: ''
  }
}

async function saveDbEntry() {
  savingDb.value = true
  try {
    const tags = dbEntryForm.value.tagsInput
      .split(',')
      .map(t => t.trim())
      .filter(t => t)
    
    if (editingDbEntry.value) {
      // Update existing
      const response = await fetch(`${backendUrl}/api/memories/database/entries/${editingDbEntry.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: dbEntryForm.value.content,
          category: dbEntryForm.value.category,
          importance: dbEntryForm.value.importance,
          tags
        })
      })
      const data = await response.json()
      if (data.status !== 'ok') {
        alert('更新失败')
        return
      }
    } else {
      // Add new
      const response = await fetch(`${backendUrl}/api/memories/database/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: dbEntryForm.value.content,
          category: dbEntryForm.value.category,
          importance: dbEntryForm.value.importance,
          tags
        })
      })
      const data = await response.json()
      if (data.status !== 'ok') {
        alert('添加失败')
        return
      }
    }
    
    closeDbEntryModal()
    await loadDbCategories()
    await loadDbEntries()
  } catch (e: any) {
    alert(`保存失败: ${e.message}`)
  } finally {
    savingDb.value = false
  }
}

async function deleteDbEntry(entryId: number) {
  if (!confirm(`确定要删除这条记忆吗？`)) return
  
  try {
    const response = await fetch(`${backendUrl}/api/memories/database/entries/${entryId}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.status === 'ok') {
      await loadDbCategories()
      await loadDbEntries()
    } else {
      alert('删除失败')
    }
  } catch (e: any) {
    alert(`删除失败: ${e.message}`)
  }
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

/* Database styles */
.db-modal {
  width: 900px;
  height: 700px;
}

.db-entry-modal {
  width: 600px;
}

.db-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.category-select {
  flex: 1;
  padding: 8px 12px;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 6px;
  color: #cdd6f4;
  font-size: 0.9rem;
}

.db-entries {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.db-entry {
  background: #313244;
  border-radius: 8px;
  overflow: hidden;
}

.db-entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #45475a;
}

.db-entry-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.db-entry-id {
  font-weight: 600;
  color: #89b4fa;
}

.db-entry-category {
  background: #89b4fa33;
  color: #89b4fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.db-entry-importance {
  color: #f9e2af;
  font-size: 0.85rem;
}

.db-entry-actions {
  display: flex;
  gap: 4px;
}

.db-entry-content-wrapper {
  position: relative;
}

.db-entry-content {
  margin: 0;
  padding: 12px;
  color: #cdd6f4;
  font-size: 0.85rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.db-entry-content.collapsed {
  max-height: 80px;
  overflow: hidden;
}

.btn-expand {
  color: #89b4fa;
}

.btn-expand:hover {
  color: #b4befe;
}

.db-entry-tags {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid #45475a;
}

.tag {
  background: #a6e3a133;
  color: #a6e3a1;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 0.8rem;
}

.btn-danger {
  color: #f38ba8;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  color: #a6adc8;
  font-size: 0.85rem;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 6px;
  color: #cdd6f4;
  font-size: 0.9rem;
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #89b4fa;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}
</style>
