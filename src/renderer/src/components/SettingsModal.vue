<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>⚙️ 设置</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <!-- Tab Navigation -->
      <div class="tab-nav">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'model' }"
          @click="activeTab = 'model'"
        >
          🤖 模型配置
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'memory' }"
          @click="activeTab = 'memory'"
        >
          🧠 记忆管理
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'wechat' }"
          @click="activeTab = 'wechat'"
        >
          📱 微信连接
        </button>
      </div>

      <div class="modal-body">
        <!-- Model Settings Tab -->
        <div v-if="activeTab === 'model'">
        <!-- Current Model Card -->
        <div class="current-model-card">
          <div class="card-header">
            <span class="card-title">当前模型</span>
            <button class="btn btn-switch" @click="showModelSelector = true">
              切换模型 ▼
            </button>
          </div>
          <div class="card-body">
            <div class="model-name">
              {{ currentModelName }}
              <span class="model-status-badge" :class="hasApiKey ? 'configured' : 'unconfigured'">
                {{ hasApiKey ? '✅ 已配置' : '⚠️ 未配置' }}
              </span>
            </div>
            <div class="model-provider">提供商: {{ localConfig.provider || '未设置' }}</div>
          </div>
        </div>

        <!-- Configuration Section -->
        <div class="config-section">
          <div class="setting-group">
            <label class="setting-label">API Key</label>
            <div class="input-with-toggle">
              <input
                v-model="apiKeyInput"
                :type="showApiKey ? 'text' : 'password'"
                class="setting-input"
                :placeholder="hasApiKey ? '已配置（输入可更新）' : '请输入 API Key'"
              />
              <button class="toggle-visibility" @click="showApiKey = !showApiKey" type="button">
                {{ showApiKey ? '🙈' : '👁️' }}
              </button>
            </div>
            <p class="setting-hint">
              <span v-if="hasApiKey">✅ 已在 .env 中配置</span>
              <span v-else class="warning">⚠️ 未配置，请输入 API Key</span>
            </p>
          </div>

          <div class="action-row">
            <button 
              class="btn btn-test" 
              @click="testConnection"
              :disabled="testingConnection"
            >
              {{ testingConnection ? '测试中...' : '🔗 测试连接' }}
            </button>
            <p v-if="connectionMessage" class="connection-result" :class="connectionSuccess ? 'success' : 'error'">
              {{ connectionMessage }}
            </p>
          </div>
        </div>

        <hr class="divider" />

        <!-- Advanced Settings -->
        <div class="setting-group">
          <button class="btn btn-advanced" @click="showAdvanced = !showAdvanced" type="button">
            {{ showAdvanced ? '▼ 高级设置' : '▶ 高级设置' }}
          </button>
          
          <div v-if="showAdvanced" class="advanced-settings">
            <!-- DeepSeek V4 深度思考设置 -->
            <div class="setting-group" v-if="isDeepSeekV4Model">
              <label class="setting-label">深度思考</label>
              <div class="toggle-row">
                <label class="switch">
                  <input type="checkbox" v-model="localDeepSeekSettings.thinking" />
                  <span class="slider"></span>
                </label>
                <span class="toggle-label">{{ localDeepSeekSettings.thinking ? '已开启' : '已关闭' }}</span>
              </div>
              <p class="setting-hint">启用 DeepSeek V4 的深度思考模式（thinking）</p>
            </div>
            
            <div class="setting-group" v-if="isDeepSeekV4Model && localDeepSeekSettings.thinking">
              <label class="setting-label">推理努力程度: {{ localDeepSeekSettings.reasoningEffort === 'high' ? '高' : '最高' }}</label>
              <input
                :value="localDeepSeekSettings.reasoningEffort === 'high' ? 0 : 1"
                @input="localDeepSeekSettings.reasoningEffort = ($event.target as HTMLInputElement).value === '0' ? 'high' : 'max'"
                type="range"
                min="0"
                max="1"
                step="1"
                class="setting-range"
              />
              <p class="setting-hint">复杂 Agent 任务建议使用最高级别</p>
            </div>

            <div class="setting-group">
              <label class="setting-label">Temperature: {{ localConfig.temperature }}</label>
              <input
                v-model.number="localConfig.temperature"
                type="range"
                min="0"
                max="2"
                step="0.1"
                class="setting-range"
              />
              <p class="setting-hint">控制回复的创造性（0 = 确定性强，2 = 更随机）</p>
            </div>

            <div class="setting-group">
              <label class="setting-label">Max Tokens: {{ localConfig.maxTokens }}</label>
              <input
                v-model.number="localConfig.maxTokens"
                type="range"
                min="256"
                max="8192"
                step="256"
                class="setting-range"
              />
              <p class="setting-hint">单次回复的最大 token 数量</p>
            </div>
          </div>
        </div>
        </div>

        <!-- Memory Management Tab -->
        <div v-if="activeTab === 'memory'">
          <MemoryManager />
        </div>
        
        <!-- WeChat Connection Tab -->
        <div v-if="activeTab === 'wechat'">
          <WeChatManager />
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-danger" @click="restartAllServices" :disabled="restarting">
          {{ restarting ? '重启中...' : '🔄 重启所有服务' }}
        </button>
        <div class="footer-right">
          <button class="btn btn-secondary" @click="$emit('close')">取消</button>
          <button class="btn btn-primary" @click="saveSettings" :disabled="saving">
            {{ saving ? '保存中...' : '保存设置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Model Selector Modal -->
    <div v-if="showModelSelector" class="modal-overlay" @click.self="showModelSelector = false">
      <div class="modal-content model-selector-modal">
        <div class="modal-header">
          <h2>选择模型</h2>
          <button class="close-btn" @click="showModelSelector = false">×</button>
        </div>
        
        <div class="modal-body">
          <div class="models-list">
            <div 
              v-for="model in availableModels" 
              :key="model.id" 
              class="model-item"
              :class="{ active: model.id === localConfig.model }"
            >
              <div class="model-info" @click="selectModel(model.id)">
                <div class="model-name-row">
                  <span class="model-name">{{ model.name }}</span>
                  <span v-if="model.id === localConfig.model" class="current-badge">当前</span>
                </div>
                <span class="model-status">
                  <span v-if="model.configured" class="configured">✅ 已配置</span>
                  <span v-else class="unconfigured">⚠️ 未配置</span>
                </span>
              </div>
              <div class="model-actions">
                <span class="model-provider">{{ model.provider }}</span>
                <button 
                  class="btn btn-delete-model" 
                  @click.stop="confirmDeleteModel(model.id, model.name)"
                  title="删除模型"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
          
          <div class="add-model-section">
            <button class="btn btn-add-full" @click="openAddModel">
              ➕ 添加新模型
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Model Modal -->
    <div v-if="showAddModel" class="modal-overlay" @click.self="showAddModel = false">
      <div class="modal-content add-model-modal">
        <div class="modal-header">
          <h2>➕ 添加新模型</h2>
          <button class="close-btn" @click="closeAddModel">×</button>
        </div>
        <div class="modal-body">
          <div class="setting-group">
            <label class="setting-label">模型 ID *</label>
            <input v-model="newModel.id" class="setting-input" placeholder="例如: gpt-4o, deepseek-chat" />
          </div>
          <div class="setting-group">
            <label class="setting-label">提供商</label>
            <select v-model="newModel.provider" class="setting-input">
              <option value="custom">自定义</option>
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="anthropic">Anthropic</option>
              <option value="openrouter">OpenRouter</option>
              <option value="xiaomi">Xiaomi</option>
            </select>
          </div>
          <div class="setting-group">
            <label class="setting-label">API Key *</label>
            <input v-model="newModel.apiKey" type="password" class="setting-input" placeholder="输入 API Key" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeAddModel">取消</button>
          <button class="btn btn-primary" @click="addCustomModel" :disabled="addingModel">
            {{ addingModel ? '添加中...' : '添加模型' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { fetchWithAuth } from '@/utils/api'
import { useSettingsStore, type ModelProfile, type DeepSeekSettings } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import MemoryManager from './MemoryManager.vue'
import WeChatManager from './WeChatManager.vue'

const emit = defineEmits<{
  close: []
}>()

const props = defineProps<{
  show?: boolean
}>()

const settingsStore = useSettingsStore()
const toast = useToast()
const confirm = useConfirm()

const activeTab = ref<'model' | 'memory' | 'wechat'>('model')

const localConfig = ref({
  model: '',
  provider: '',
  temperature: 0.7,
  maxTokens: 2048
})

const availableModels = ref<ModelProfile[]>([])
const selectedModelId = ref('')
const apiKeyInput = ref('')
const hasApiKey = ref(false)

const showApiKey = ref(false)
const saving = ref(false)
const restarting = ref(false)
const testingConnection = ref(false)
const connectionMessage = ref('')
const connectionSuccess = ref(false)

const showModelSelector = ref(false)
const showAddModel = ref(false)
const showAdvanced = ref(false)
const addingModel = ref(false)
const localDeepSeekSettings = ref<DeepSeekSettings>({
  thinking: false,
  reasoningEffort: 'high'
})
const isDeepSeekV4Model = computed(() => {
  return localConfig.value.model.startsWith('deepseek-v4')
})
const newModel = ref({
  id: '',
  provider: 'custom',
  apiKey: ''
})

const currentModelName = computed(() => {
  const model = availableModels.value.find(m => m.id === localConfig.value.model)
  return model?.name || localConfig.value.model || '未选择'
})

watch(
  () => props.show,
  async (newVal) => {
    if (newVal) {
      await loadAllData()
    }
  }
)

async function loadAllData() {
  await Promise.all([
    loadCurrentConfig(),
    loadModels(),
    loadDeepSeekSettings()
  ])
}

async function loadCurrentConfig() {
  try {
    const response = await fetchWithAuth('/api/config')
    if (response.ok) {
      const data = await response.json()
      localConfig.value = {
        model: data.model || 'deepseek-chat',
        provider: data.provider || 'deepseek',
        temperature: data.temperature || 0.7,
        maxTokens: data.maxTokens || 2048
      }
      selectedModelId.value = localConfig.value.model
      await checkApiKeyStatus()
    }
  } catch (error) {
    console.error('[Settings] Failed to load config:', error)
  }
}

async function loadModels() {
  try {
    const response = await fetchWithAuth('/api/models')
    if (response.ok) {
      const data = await response.json()
      availableModels.value = data.models || []
    } else {
      console.error('[Settings] API error:', response.status)
    }
  } catch (error) {
    console.error('[Settings] Failed to load models:', error)
  }
}

async function loadDeepSeekSettings() {
  const settings = await settingsStore.loadDeepSeekSettings()
  if (settings) {
    localDeepSeekSettings.value = { ...settings }
  }
}

async function checkApiKeyStatus() {
  if (!selectedModelId.value) return
  
  try {
    const result = await settingsStore.checkApiKey(selectedModelId.value)
    hasApiKey.value = result.hasKey
    if (result.hasKey && result.maskedKey) {
      apiKeyInput.value = ''
    }
  } catch (error) {
    console.error('[Settings] Failed to check API key:', error)
  }
}

async function selectModel(modelId: string) {
  selectedModelId.value = modelId
  
  try {
    const result = await settingsStore.switchModel(modelId)
    
    if (result.success) {
      localConfig.value.model = modelId
      await checkApiKeyStatus()
      connectionMessage.value = ''
      showModelSelector.value = false
    }
  } catch (error) {
    console.error('[Settings] Failed to switch model:', error)
  }
}

async function testConnection() {
  if (!selectedModelId.value) {
    connectionMessage.value = '请先选择模型'
    connectionSuccess.value = false
    return
  }
  
  testingConnection.value = true
  connectionMessage.value = ''
  
  try {
    if (apiKeyInput.value) {
      await settingsStore.setApiKey(selectedModelId.value, apiKeyInput.value)
      hasApiKey.value = true
    }
    
    connectionSuccess.value = true
    connectionMessage.value = '✅ 配置已保存'
  } catch (error) {
    connectionSuccess.value = false
    connectionMessage.value = '配置失败'
  } finally {
    testingConnection.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    if (apiKeyInput.value) {
      await settingsStore.setApiKey(selectedModelId.value, apiKeyInput.value)
    }
    
    await settingsStore.saveConfig(localConfig.value)
    await settingsStore.saveDeepSeekSettings(localDeepSeekSettings.value)
    emit('close')
  } catch (error) {
    console.error('Failed to save settings:', error)
    toast.error('保存设置失败，请重试')
  } finally {
    saving.value = false
  }
}

function openAddModel() {
  showModelSelector.value = false
  showAddModel.value = true
}

function closeAddModel() {
  showAddModel.value = false
  newModel.value = { id: '', provider: 'custom', apiKey: '' }
}

async function addCustomModel() {
  if (!newModel.value.id) {
    toast.warning('请填写模型 ID')
    return
  }
  
  if (!newModel.value.apiKey) {
    toast.warning('请输入 API Key')
    return
  }
  
  addingModel.value = true
  try {
    const model: ModelProfile = {
      id: newModel.value.id,
      name: newModel.value.id,
      provider: newModel.value.provider,
      api_base_url: '',
      api_key_env: `${newModel.value.id.toUpperCase().replace(/-/g, '_')}_API_KEY`,
      temperature: 0.7,
      max_tokens: 2048,
      configured: false
    }
    
    const success = await settingsStore.addCustomModel(
      model,
      newModel.value.apiKey
    )
    
    if (success) {
      await loadModels()
      closeAddModel()
    } else {
      toast.error('添加模型失败')
    }
  } catch (error) {
    console.error('Failed to add model:', error)
    toast.error('添加模型失败')
  } finally {
    addingModel.value = false
  }
}

async function confirmDeleteModel(modelId: string, modelName: string) {
  const confirmed = await confirm.danger(
    `确定要删除模型 "${modelName}" 吗？\n\n这将同时删除：\n- 模型配置\n- API Key\n- API URL`,
    '删除模型'
  )
  
  if (!confirmed) {
    return
  }
  
  try {
    const success = await settingsStore.deleteModel(modelId)
    
    if (success) {
      await loadModels()
      
      // 如果删除的是当前模型，清空选择
      if (modelId === localConfig.value.model) {
        localConfig.value.model = ''
        localConfig.value.provider = ''
        hasApiKey.value = false
        apiKeyInput.value = ''
      }
      
      // 如果没有模型了，关闭选择器
      if (availableModels.value.length === 0) {
        showModelSelector.value = false
      }
    } else {
      toast.error('删除模型失败')
    }
  } catch (error) {
    console.error('Failed to delete model:', error)
    toast.error('删除模型失败')
  }
}

async function restartAllServices() {
  const confirmed = await confirm.warning(
    '确定要重启所有服务吗？\n\n这将重启：\n- 后端服务\n- 前端服务',
    '重启服务'
  )
  
  if (!confirmed) {
    return
  }

  restarting.value = true
  try {
    // 重启所有服务（会重启后端和前端）
    const result = await (window as any).api.restartAll()
    
    if (result.success) {
      console.log('[Restart] Restart initiated')
    } else {
      toast.error('重启失败: ' + (result.error || '未知错误'))
      restarting.value = false
    }
  } catch (error) {
    console.error('[Restart] Failed to restart:', error)
    toast.error('重启服务失败，请手动重启')
    restarting.value = false
  }
}

onMounted(async () => {
  await loadAllData()
})
</script>

<style scoped>
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
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1e1e2e;
  border-radius: 12px;
  width: 900px;
  max-width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.tab-nav {
  display: flex;
  padding: 0;
  border-bottom: 1px solid #313244;
  background: #1e1e2e;
  gap: 0;
}

.tab-btn {
  padding: 10px 24px;
  background: #181825;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6c7086;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  white-space: nowrap;
}

.tab-btn:hover {
  background: #1e1e2e;
  color: #cdd6f4;
}

.tab-btn.active {
  background: #1e1e2e;
  color: #cdd6f4;
  border-bottom-color: #89b4fa;
}

.model-selector-modal {
  max-width: 450px;
}

.add-model-modal {
  max-width: 420px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #313244;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #cdd6f4;
}

.close-btn {
  background: transparent;
  border: none;
  color: #6c7086;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #313244;
  color: #f38ba8;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

/* Current Model Card */
.current-model-card {
  background: linear-gradient(135deg, #313244 0%, #1e1e2e 100%);
  border: 1px solid #45475a;
  border-radius: 10px;
  margin-bottom: 20px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(137, 180, 250, 0.1);
  border-bottom: 1px solid #45475a;
}

.card-title {
  color: #89b4fa;
  font-size: 0.85rem;
  font-weight: 600;
}

.card-body {
  padding: 16px;
}

.model-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #cdd6f4;
  margin-bottom: 8px;
}

.model-status-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: normal;
}

.model-status-badge.configured {
  background: rgba(166, 227, 161, 0.2);
  color: #a6e3a1;
}

.model-status-badge.unconfigured {
  background: rgba(243, 139, 168, 0.2);
  color: #f38ba8;
}

.model-url {
  font-size: 0.8rem;
  color: #6c7086;
  font-family: monospace;
}

/* Config Section */
.config-section {
  margin-bottom: 20px;
}

.setting-group {
  margin-bottom: 16px;
}

.setting-label {
  display: block;
  color: #cdd6f4;
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 6px;
}

.setting-input {
  width: 100%;
  padding: 10px 12px;
  background: #181825;
  border: 1px solid #313244;
  border-radius: 8px;
  color: #cdd6f4;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}

.setting-input:focus {
  border-color: #89b4fa;
}

.input-with-toggle {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-toggle .setting-input {
  flex: 1;
  padding-right: 40px;
}

.toggle-visibility {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 4px;
  color: #6c7086;
  transition: color 0.2s;
}

.toggle-visibility:hover {
  color: #cdd6f4;
}

.setting-hint {
  color: #6c7086;
  font-size: 0.75rem;
  margin: 4px 0 0;
}

.setting-hint .warning {
  color: #f38ba8;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.connection-result {
  font-size: 0.8rem;
  flex: 1;
}

.connection-result.success {
  color: #a6e3a1;
}

.connection-result.error {
  color: #f38ba8;
}

.divider {
  border: none;
  border-top: 1px solid #313244;
  margin: 20px 0;
}

.setting-range {
  width: 100%;
  margin: 8px 0;
  cursor: pointer;
}

/* Models List */
.models-list {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #313244;
  border-radius: 8px;
  background: #181825;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #313244;
  cursor: pointer;
  transition: background 0.2s;
}

.model-item:last-child {
  border-bottom: none;
}

.model-item:hover {
  background: #1e1e2e;
}

.model-item.active {
  background: rgba(137, 180, 250, 0.1);
  border-left: 3px solid #89b4fa;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name-row .model-name {
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
  margin: 0;
}

.current-badge {
  background: #89b4fa;
  color: #1e1e2e;
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 600;
}

.model-status {
  font-size: 0.75rem;
}

.model-status .configured {
  color: #a6e3a1;
}

.model-status .unconfigured {
  color: #f38ba8;
}

.model-provider {
  font-size: 0.75rem;
  color: #6c7086;
  text-transform: uppercase;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-delete-model {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 4px;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.btn-delete-model:hover {
  opacity: 1;
}

.add-model-section {
  margin-top: 16px;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid #313244;
}

.footer-right {
  display: flex;
  gap: 12px;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  font-weight: 500;
}

.btn-secondary {
  background: #313244;
  color: #cdd6f4;
}

.btn-secondary:hover {
  background: #45475a;
}

.btn-primary {
  background: #89b4fa;
  color: #1e1e2e;
}

.btn-primary:hover:not(:disabled) {
  background: #74c7ec;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: #f38ba8;
  color: #1e1e2e;
}

.btn-danger:hover:not(:disabled) {
  background: #f5c2e7;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-switch {
  background: #45475a;
  color: #cdd6f4;
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-switch:hover {
  background: #585b70;
}

.btn-test {
  background: #45475a;
  color: #cdd6f4;
}

.btn-test:hover:not(:disabled) {
  background: #585b70;
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-advanced {
  background: transparent;
  color: #6c7086;
  width: 100%;
  padding: 8px 12px;
  text-align: left;
  font-size: 0.85rem;
  border: 1px dashed #313244;
}

.btn-advanced:hover {
  background: #181825;
  color: #cdd6f4;
  border-color: #45475a;
}

.btn-add-full {
  background: #45475a;
  color: #cdd6f4;
  width: 100%;
  padding: 10px;
}

.btn-add-full:hover {
  background: #585b70;
}

.advanced-settings {
  margin-top: 16px;
  padding: 16px;
  background: #181825;
  border-radius: 8px;
  border: 1px solid #313244;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toggle-label {
  font-size: 0.85rem;
  color: #a6adc8;
}
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #45475a;
  transition: 0.3s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px; width: 18px;
  left: 3px; bottom: 3px;
  background: #cdd6f4;
  transition: 0.3s;
  border-radius: 50%;
}
input:checked + .slider {
  background: #89b4fa;
}
input:checked + .slider:before {
  transform: translateX(20px);
}
.button-group {
  display: flex;
  gap: 8px;
}
.btn-effort {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #45475a;
  border-radius: 6px;
  background: #313244;
  color: #cdd6f4;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.85rem;
}
.btn-effort.active {
  background: #89b4fa;
  color: #1e1e2e;
  border-color: #89b4fa;
}
.btn-effort:hover:not(.active) {
  border-color: #89b4fa;
}
</style>
