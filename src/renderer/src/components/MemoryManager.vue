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
            @click="memory.id === 'database' ? viewDatabase() : memory.id === 'maindb' ? viewMainDatabase() : memory.id === 'gatewaydb' ? viewGatewayDatabase() : memory.id === 'dragonballdb' ? viewDragonballDatabase('main') : memory.id === 'dragonball_checkpoint' ? viewDragonballDatabase('checkpoint') : viewMemory(memory)"
            :disabled="!memory.exists"
          >
            👁️ 查看
          </button>
          <button
            class="btn btn-edit"
            @click="editMemory(memory)"
            :disabled="!memory.exists || memory.id === 'database' || memory.id === 'maindb' || memory.id === 'gatewaydb' || memory.id === 'dragonballdb' || memory.id === 'dragonball_checkpoint'"
          >
            ✏️ 编辑
          </button>
        </div>
      </div>
    </div>

    <!-- Memory Content Modal (with entries) -->
    <div v-if="showContentModal" class="modal-overlay" @click.self="closeContentModal">
      <div class="modal-content memory-content-modal">
        <div class="modal-header">
          <h2>{{ getMemoryIcon(selectedMemory?.id || '') }} {{ selectedMemory?.name }}</h2>
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

    <!-- Main Database Modal -->
    <div v-if="showMainDbModal" class="modal-overlay" @click.self="closeMainDbModal">
      <div class="modal-content main-db-modal">
        <div class="modal-header">
          <h2>💾 应用主数据库</h2>
          <button class="close-btn" @click="closeMainDbModal">×</button>
        </div>
        <div class="modal-body">
          <div class="db-toolbar">
            <select v-model="selectedTable" @change="loadTableData(0)" class="table-select">
              <option value="">选择表</option>
              <option v-for="table in mainDbTables" :key="table.name" :value="table.name">
                {{ table.name }} ({{ table.count }})
              </option>
            </select>
          </div>

          <div v-if="loadingMainDb" class="loading">加载中...</div>
          <div v-else-if="tableData.rows.length > 0" class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in tableData.rows" :key="index">
                  <td v-for="col in tableData.columns" :key="col" class="table-cell">
                    {{ formatCellValue(row[col]) }}
                  </td>
                  <td>
                    <button
                      class="btn btn-sm btn-danger"
                      @click="deleteTableRow(row[tableData.primaryKey])"
                      title="删除"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="table-pagination">
              <button
                class="btn btn-sm"
                @click="loadTableData(0)"
                :disabled="tableData.offset === 0"
              >
                首页
              </button>
              <button
                class="btn btn-sm"
                @click="loadTableData(tableData.offset - tableData.limit)"
                :disabled="tableData.offset === 0"
              >
                上一页
              </button>
              <span class="page-info">
                第 <input
                  type="number"
                  :value="currentTablePage"
                  @change="jumpToPage"
                  min="1"
                  :max="totalTablePages"
                  class="page-input"
                /> / {{ totalTablePages }} 页
              </span>
              <button
                class="btn btn-sm"
                @click="loadTableData(tableData.offset + tableData.limit)"
                :disabled="tableData.offset + tableData.rows.length >= tableData.total"
              >
                下一页
              </button>
              <button
                class="btn btn-sm"
                @click="loadTableData((totalTablePages - 1) * tableData.limit)"
                :disabled="tableData.offset + tableData.rows.length >= tableData.total"
              >
                末页
              </button>
              <span class="total-info">共 {{ tableData.total }} 条</span>
            </div>
          </div>
          <div v-else-if="selectedTable" class="empty-message">表中暂无数据</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeMainDbModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- Gateway Database Modal -->
    <div v-if="showGatewayDbModal" class="modal-overlay" @click.self="closeGatewayDbModal">
      <div class="modal-content main-db-modal">
        <div class="modal-header">
          <h2>📱 Gateway 微信数据库</h2>
          <button class="close-btn" @click="closeGatewayDbModal">×</button>
        </div>
        <div class="modal-body">
          <div class="db-toolbar">
            <select v-model="selectedGatewayTable" @change="loadGatewayTableData(0)" class="table-select">
              <option value="">选择表</option>
              <option v-for="table in gatewayDbTables" :key="table.name" :value="table.name">
                {{ table.name }} ({{ table.count }})
              </option>
            </select>
            <span class="readonly-hint">只读模式</span>
          </div>

          <div v-if="loadingGatewayDb" class="loading">加载中...</div>
          <div v-else-if="gatewayTableData.rows.length > 0" class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in gatewayTableData.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in gatewayTableData.rows" :key="index">
                  <td v-for="col in gatewayTableData.columns" :key="col" class="table-cell">
                    {{ formatCellValue(row[col]) }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="table-pagination">
              <button
                class="btn btn-sm"
                @click="loadGatewayTableData(0)"
                :disabled="gatewayTableData.offset === 0"
              >
                首页
              </button>
              <button
                class="btn btn-sm"
                @click="loadGatewayTableData(gatewayTableData.offset - gatewayTableData.limit)"
                :disabled="gatewayTableData.offset === 0"
              >
                上一页
              </button>
              <span class="page-info">
                第 <input
                type="number"
                :value="currentGatewayTablePage"
                @change="jumpToGatewayTablePage"
                min="1"
                :max="totalGatewayTablePages"
                class="page-input"
              /> / {{ totalGatewayTablePages }} 页
              </span>
              <button
                class="btn btn-sm"
                @click="loadGatewayTableData(gatewayTableData.offset + gatewayTableData.limit)"
                :disabled="gatewayTableData.offset + gatewayTableData.rows.length >= gatewayTableData.total"
              >
                下一页
              </button>
              <button
                class="btn btn-sm"
                @click="loadGatewayTableData(gatewayTableData.total - gatewayTableData.limit)"
                :disabled="gatewayTableData.offset + gatewayTableData.rows.length >= gatewayTableData.total"
              >
                末页
              </button>
              <span class="total-info">共 {{ gatewayTableData.total }} 条</span>
            </div>
          </div>
          <div v-else-if="selectedGatewayTable" class="empty-message">表中暂无数据</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeGatewayDbModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- Dragonball Database Modal -->
    <div v-if="showDragonballDbModal" class="modal-overlay" @click.self="closeDragonballDbModal">
      <div class="modal-content main-db-modal">
        <div class="modal-header">
          <h2>{{ currentDragonballDb === 'checkpoint' ? '🔮 龙珠检查点库' : '🔮 龙珠知识库' }}</h2>
          <button class="close-btn" @click="closeDragonballDbModal">×</button>
        </div>
        <div class="modal-body">
          <div class="db-toolbar">
            <select v-model="selectedDragonballTable" @change="loadDragonballTableData(0)" class="table-select">
              <option value="">选择表</option>
              <option v-for="table in dragonballDbTables" :key="table.name" :value="table.name">
                {{ table.name === 'nodes' ? '节点' : table.name === 'edges' ? '关系边' : '自适应配置' }} ({{ table.count }})
              </option>
            </select>
            <span class="readonly-hint">只读模式</span>
          </div>

          <div v-if="loadingDragonballDb" class="loading">加载中...</div>
          <div v-else-if="dragonballTableData.rows.length > 0" class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in dragonballTableData.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in dragonballTableData.rows" :key="index">
                  <td v-for="col in dragonballTableData.columns" :key="col" class="table-cell"
                    :title="formatCellTitle(row[col])"
                    @click="showDragonballDetail(row, col)"
                    style="cursor: pointer;"
                  >
                    {{ formatCellValue(row[col]) }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="table-pagination">
              <button
                class="btn btn-sm"
                @click="loadDragonballTableData(0)"
                :disabled="dragonballTableData.offset === 0"
              >
                首页
              </button>
              <button
                class="btn btn-sm"
                @click="loadDragonballTableData(dragonballTableData.offset - dragonballTableData.limit)"
                :disabled="dragonballTableData.offset === 0"
              >
                上一页
              </button>
              <span class="page-info">
                第 <input
                type="number"
                :value="currentDragonballTablePage"
                @change="jumpToDragonballTablePage"
                min="1"
                :max="totalDragonballTablePages"
                class="page-input"
              /> / {{ totalDragonballTablePages }} 页
              </span>
              <button
                class="btn btn-sm"
                @click="loadDragonballTableData(dragonballTableData.offset + dragonballTableData.limit)"
                :disabled="dragonballTableData.offset + dragonballTableData.rows.length >= dragonballTableData.total"
              >
                下一页
              </button>
              <button
                class="btn btn-sm"
                @click="loadDragonballTableData(dragonballTableData.total - dragonballTableData.limit)"
                :disabled="dragonballTableData.offset + dragonballTableData.rows.length >= dragonballTableData.total"
              >
                末页
              </button>
              <span class="total-info">共 {{ dragonballTableData.total }} 条</span>
            </div>
          </div>
          <div v-else-if="selectedDragonballTable" class="empty-message">表中暂无数据</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeDragonballDbModal">关闭</button>
        </div>
      </div>
    </div>

    <!-- Dragonball Detail Modal -->
    <div v-if="showDragonballDetailModal" class="modal-overlay" @click.self="closeDragonballDetailModal">
      <div class="modal-content" style="max-width: 800px; max-height: 70vh;">
        <div class="modal-header">
          <h2>{{ dragonballDetailTitle }}</h2>
          <button class="close-btn" @click="closeDragonballDetailModal">×</button>
        </div>
        <div class="modal-body">
          <pre style="white-space: pre-wrap; word-break: break-all; font-size: 13px; line-height: 1.6; background: rgba(255,255,255,0.03); padding: 16px; border-radius: 8px; max-height: 50vh; overflow-y: auto; margin: 0;">{{ dragonballDetailContent }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeDragonballDetailModal">关闭</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchWithAuth } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const toast = useToast()
const confirm = useConfirm()

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

// Main database state
const showMainDbModal = ref(false)
const mainDbTables = ref<{name: string; count: number; columns: string[]}[]>([])
const selectedTable = ref('')
const tableData = ref<{table: string; columns: string[]; rows: any[]; total: number; limit: number; offset: number; primaryKey: string}>({
  table: '',
  columns: [],
  rows: [],
  total: 0,
  limit: 100,
  offset: 0,
  primaryKey: 'id'
})
const loadingMainDb = ref(false)

// Gateway database state
const showGatewayDbModal = ref(false)
const gatewayDbTables = ref<{name: string; count: number; columns: string[]}[]>([])
const selectedGatewayTable = ref('')
const gatewayTableData = ref<{table: string; columns: string[]; rows: any[]; total: number; limit: number; offset: number; primaryKey: string}>({
  table: '',
  columns: [],
  rows: [],
  total: 0,
  limit: 100,
  offset: 0,
  primaryKey: 'id'
})
const loadingGatewayDb = ref(false)

// Dragonball database state
const showDragonballDbModal = ref(false)
const dragonballDbTables = ref<{name: string; count: number; columns: string[]}[]>([])
const selectedDragonballTable = ref('')
const dragonballTableData = ref<{table: string; columns: string[]; rows: any[]; total: number; limit: number; offset: number; primaryKey: string}>({
  table: '',
  columns: [],
  rows: [],
  total: 0,
  limit: 100,
  offset: 0,
  primaryKey: 'id'
})
const loadingDragonballDb = ref(false)
const showDragonballDetailModal = ref(false)
const dragonballDetailContent = ref('')
const dragonballDetailTitle = ref('')
const currentDragonballDb = ref('main')  // 'main' or 'checkpoint'

// 使用 fetchWithAuth 替代硬编码 URL

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
    database: '💾',
    maindb: '🗃️',
    gatewaydb: '📱',
    dragonballdb: '🔮',
    dragonball_checkpoint: '📸'
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
    const response = await fetchWithAuth(`/api/memories`)
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
    const response = await fetchWithAuth(`/api/memories/${memory.id}/entries`)
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
    const response = await fetchWithAuth(`/api/memories/${memory.id}`)
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

  const confirmed = await confirm.danger(
    `确定要删除第 ${entryIndex + 1} 条记录吗？`,
    '删除记录'
  )
  if (!confirmed) return

  try {
    const response = await fetchWithAuth(
      `/api/memories/${selectedMemory.value.id}/entries/${entryIndex}`,
      { method: 'DELETE' }
    )
    const data = await response.json()
    if (data.status === 'ok') {
      await viewMemory(selectedMemory.value)
    } else {
      toast.error('删除失败')
    }
  } catch (e: any) {
    toast.error(`删除失败: ${e.message}`)
  }
}

async function confirmDeleteAll(memory: Memory) {
  const confirmed = await confirm.danger(
    `确定要清空 ${memory.name} 的所有内容吗？\n\n此操作不可恢复。`,
    '清空记忆'
  )
  if (!confirmed) return

  try {
    const response = await fetchWithAuth(`/api/memories/${memory.id}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.status === 'ok') {
      await loadMemories()
    } else {
      toast.error('清空失败')
    }
  } catch (e: any) {
    toast.error(`清空失败: ${e.message}`)
  }
}

async function saveMemory() {
  if (!selectedMemory.value) return

  saving.value = true
  try {
    const response = await fetchWithAuth(`/api/memories/${selectedMemory.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: editContent.value })
    })
    const data = await response.json()
    if (data.status === 'ok') {
      closeEditModal()
      await loadMemories()
    } else {
      toast.error('保存失败')
    }
  } catch (e: any) {
    toast.error(`保存失败: ${e.message}`)
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
    const response = await fetchWithAuth(`/api/memories/database/categories`)
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
      ? `/api/memories/database/entries?category=${selectedCategory.value}`
      : `/api/memories/database/entries`
    const response = await fetchWithAuth(url)
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
      const response = await fetchWithAuth(`/api/memories/database/entries/${editingDbEntry.value.id}`, {
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
        toast.error('更新失败')
        return
      }
    } else {
      // Add new
      const response = await fetchWithAuth(`/api/memories/database/entries`, {
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
        toast.error('添加失败')
        return
      }
    }

    closeDbEntryModal()
    await loadDbCategories()
    await loadDbEntries()
  } catch (e: any) {
    toast.error(`保存失败: ${e.message}`)
  } finally {
    savingDb.value = false
  }
}

async function deleteDbEntry(entryId: number) {
  const confirmed = await confirm.danger(
    '确定要删除这条记忆吗？',
    '删除记忆'
  )
  if (!confirmed) return

  try {
    const response = await fetchWithAuth(`/api/memories/database/entries/${entryId}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.status === 'ok') {
      await loadDbCategories()
      await loadDbEntries()
    } else {
      toast.error('删除失败')
    }
  } catch (e: any) {
    toast.error(`删除失败: ${e.message}`)
  }
}

// Main database functions
async function viewMainDatabase() {
  showMainDbModal.value = true
  await loadMainDbTables()
}

async function loadMainDbTables() {
  loadingMainDb.value = true
  try {
    const response = await fetchWithAuth('/api/database/tables')
    const data = await response.json()
    mainDbTables.value = data.tables || []
  } catch (e: any) {
    console.error('Failed to load tables:', e)
  } finally {
    loadingMainDb.value = false
  }
}

async function loadTableData(offset: number = 0) {
  if (!selectedTable.value) return

  loadingMainDb.value = true
  try {
    const response = await fetchWithAuth(`/api/database/tables/${selectedTable.value}?limit=100&offset=${offset}`)
    const data = await response.json()
    if (data.error) {
      toast.error(data.error)
      return
    }
    tableData.value = {
      table: data.table || '',
      columns: data.columns || [],
      rows: data.rows || [],
      total: data.total || 0,
      limit: data.limit || 100,
      offset: data.offset || 0,
      primaryKey: data.primaryKey || 'id'
    }
  } catch (e: any) {
    console.error('Failed to load table data:', e)
    toast.error(`加载失败: ${e.message}`)
  } finally {
    loadingMainDb.value = false
  }
}

async function deleteTableRow(rowId: string) {
  console.log('[Delete] Attempting to delete:', {
    table: selectedTable.value,
    rowId,
    primaryKey: tableData.value.primaryKey,
    encodedRowId: encodeURIComponent(rowId)
  })

  const confirmed = await confirm.danger(
    `确定要删除这条记录吗？\n\nID: ${rowId}`,
    '删除记录'
  )
  if (!confirmed) {
    console.log('[Delete] User cancelled')
    return
  }

  try {
    const encodedRowId = encodeURIComponent(rowId)
    const url = `/api/database/tables/${selectedTable.value}/${encodedRowId}`
    console.log('[Delete] Sending request to:', url)

    const response = await fetchWithAuth(url, {
      method: 'DELETE'
    })
    const data = await response.json()
    console.log('[Delete] Response:', data)

    if (data.status === 'ok') {
      toast.success('删除成功')
      await loadTableData(tableData.value.offset)
    } else {
      toast.error(data.error || '删除失败')
    }
  } catch (e: any) {
    console.error('[Delete] Error:', e)
    toast.error(`删除失败: ${e.message}`)
  }
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'string' && value.length > 50) {
    return value.substring(0, 50) + '...'
  }
  return String(value)
}

function formatCellTitle(value: any): string {
  if (value === null || value === undefined) return 'NULL'
  return String(value)
}

const currentTablePage = computed(() => {
  if (tableData.value.limit === 0) return 1
  return Math.floor(tableData.value.offset / tableData.value.limit) + 1
})

const totalTablePages = computed(() => {
  if (tableData.value.limit === 0) return 1
  return Math.ceil(tableData.value.total / tableData.value.limit)
})

function jumpToPage(event: Event) {
  const input = event.target as HTMLInputElement
  let page = parseInt(input.value)

  if (isNaN(page) || page < 1) page = 1
  if (page > totalTablePages.value) page = totalTablePages.value

  const offset = (page - 1) * tableData.value.limit
  loadTableData(offset)
}

function closeMainDbModal() {
  showMainDbModal.value = false
  selectedTable.value = ''
  tableData.value = {
    table: '',
    columns: [],
    rows: [],
    total: 0,
    limit: 100,
    offset: 0,
    primaryKey: 'id'
  }
}

async function viewGatewayDatabase() {
  showGatewayDbModal.value = true
  await loadGatewayDbTables()
}

async function loadGatewayDbTables() {
  loadingGatewayDb.value = true
  try {
    const response = await fetchWithAuth('/api/gateway/tables')
    const data = await response.json()
    gatewayDbTables.value = data.tables || []
  } catch (e: any) {
    console.error('Failed to load gateway tables:', e)
  } finally {
    loadingGatewayDb.value = false
  }
}

async function loadGatewayTableData(offset: number = 0) {
  if (!selectedGatewayTable.value) return

  loadingGatewayDb.value = true
  try {
    const response = await fetchWithAuth(`/api/gateway/tables/${selectedGatewayTable.value}?limit=100&offset=${offset}`)
    const data = await response.json()
    if (data.error) {
      toast.error(data.error)
      return
    }
    gatewayTableData.value = {
      table: data.table || '',
      columns: data.columns || [],
      rows: data.rows || [],
      total: data.total || 0,
      limit: data.limit || 100,
      offset: data.offset || 0,
      primaryKey: data.primaryKey || 'id'
    }
  } catch (e: any) {
    console.error('Failed to load gateway table data:', e)
    toast.error(`加载失败: ${e.message}`)
  } finally {
    loadingGatewayDb.value = false
  }
}

const currentGatewayTablePage = computed(() => {
  if (gatewayTableData.value.limit === 0) return 1
  return Math.floor(gatewayTableData.value.offset / gatewayTableData.value.limit) + 1
})

const totalGatewayTablePages = computed(() => {
  if (gatewayTableData.value.limit === 0) return 1
  return Math.ceil(gatewayTableData.value.total / gatewayTableData.value.limit)
})

function jumpToGatewayTablePage(event: Event) {
  const input = event.target as HTMLInputElement
  let page = parseInt(input.value)

  if (isNaN(page) || page < 1) page = 1
  if (page > totalGatewayTablePages.value) page = totalGatewayTablePages.value

  const offset = (page - 1) * gatewayTableData.value.limit
  loadGatewayTableData(offset)
}

function closeGatewayDbModal() {
  showGatewayDbModal.value = false
  selectedGatewayTable.value = ''
  gatewayTableData.value = {
    table: '',
    columns: [],
    rows: [],
    total: 0,
    limit: 100,
    offset: 0,
    primaryKey: 'id'
  }
}

// Dragonball database functions
async function viewDragonballDatabase(db: string = 'main') {
  currentDragonballDb.value = db
  showDragonballDbModal.value = true
  await loadDragonballDbTables()
}

async function loadDragonballDbTables() {
  loadingDragonballDb.value = true
  try {
    const response = await fetchWithAuth(`/api/dragonball/tables?db=${currentDragonballDb.value}`)
    const data = await response.json()
    dragonballDbTables.value = data.tables || []
  } catch (e: any) {
    console.error('Failed to load dragonball tables:', e)
  } finally {
    loadingDragonballDb.value = false
  }
}

async function loadDragonballTableData(offset: number = 0) {
  if (!selectedDragonballTable.value) return

  loadingDragonballDb.value = true
  try {
    const response = await fetchWithAuth(`/api/dragonball/tables/${selectedDragonballTable.value}?limit=100&offset=${offset}&db=${currentDragonballDb.value}`)
    const data = await response.json()
    if (data.error) {
      toast.error(data.error)
      return
    }
    dragonballTableData.value = {
      table: data.table || '',
      columns: data.columns || [],
      rows: data.rows || [],
      total: data.total || 0,
      limit: data.limit || 100,
      offset: data.offset || 0,
      primaryKey: data.primaryKey || 'id'
    }
  } catch (e: any) {
    console.error('Failed to load dragonball table data:', e)
    toast.error(`加载失败: ${e.message}`)
  } finally {
    loadingDragonballDb.value = false
  }
}

const currentDragonballTablePage = computed(() => {
  if (dragonballTableData.value.limit === 0) return 1
  return Math.floor(dragonballTableData.value.offset / dragonballTableData.value.limit) + 1
})

const totalDragonballTablePages = computed(() => {
  if (dragonballTableData.value.limit === 0) return 1
  return Math.ceil(dragonballTableData.value.total / dragonballTableData.value.limit)
})

function jumpToDragonballTablePage(event: Event) {
  const input = event.target as HTMLInputElement
  let page = parseInt(input.value)

  if (isNaN(page) || page < 1) page = 1
  if (page > totalDragonballTablePages.value) page = totalDragonballTablePages.value

  const offset = (page - 1) * dragonballTableData.value.limit
  loadDragonballTableData(offset)
}

function closeDragonballDbModal() {
  showDragonballDbModal.value = false
  selectedDragonballTable.value = ''
  dragonballTableData.value = {
    table: '',
    columns: [],
    rows: [],
    total: 0,
    limit: 100,
    offset: 0,
    primaryKey: 'id'
  }
}

function showDragonballDetail(row: any, col: string) {
  const value = row[col]
  if (value === null || value === undefined) {
    dragonballDetailContent.value = 'NULL'
  } else if (typeof value === 'string') {
    dragonballDetailContent.value = value
  } else if (typeof value === 'object') {
    dragonballDetailContent.value = JSON.stringify(value, null, 2)
  } else {
    dragonballDetailContent.value = String(value)
  }
  const tableName = dragonballTableData.value.table
  const tableLabel = tableName === 'nodes' ? '节点' : tableName === 'edges' ? '关系边' : '自适应配置'
  const rowId = row.id || row.key || ''
  if (tableName === 'nodes' && row.title) {
    dragonballDetailTitle.value = row.title
  } else if (tableName === 'edges' && row.relation_type) {
    dragonballDetailTitle.value = row.relation_type
  } else {
    dragonballDetailTitle.value = `${tableLabel} · ${col} · ${rowId}`
  }
  showDragonballDetailModal.value = true
}

function closeDragonballDetailModal() {
  showDragonballDetailModal.value = false
  dragonballDetailContent.value = ''
  dragonballDetailTitle.value = ''
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

.readonly-hint {
  font-size: 0.8rem;
  color: #f9e2af;
  padding: 4px 8px;
  background: rgba(249, 226, 175, 0.1);
  border-radius: 4px;
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
  background: #45475a;
  color: #cdd6f4;
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

/* Main Database Styles */
.main-db-modal {
  width: 1000px;
  height: 700px;
}

.table-select {
  padding: 8px 12px;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 6px;
  color: #cdd6f4;
  font-size: 0.9rem;
  min-width: 200px;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  border: 1px solid #313244;
  text-align: left;
}

.data-table th {
  background: #313244;
  color: #cdd6f4;
  font-weight: 600;
}

.data-table td {
  background: #1e1e2e;
  color: #a6adc8;
}

.data-table tr:hover td {
  background: #313244;
}

.table-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  color: #a6adc8;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 220px;
}

.page-input {
  width: 100px;
  padding: 4px 8px;
  background: #313244;
  border: 1px solid #45475a;
  border-radius: 4px;
  color: #cdd6f4;
  font-size: 0.85rem;
  text-align: center;
}

.page-input:focus {
  outline: none;
  border-color: #89b4fa;
}

.total-info {
  margin-left: 8px;
  color: #6c7086;
}

</style>
