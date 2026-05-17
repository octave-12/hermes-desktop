<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>⚙️ 设置</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- Current Model Selection -->
        <div class="setting-group">
          <label class="setting-label">当前模型</label>
          <select v-model="selectedModelId" @change="onModelChange" class="setting-select">
            <option value="">加载中...</option>
            <option v-for="model in availableModels" :key="model.id" :value="model.id">
              {{ model.name }} {{ model.configured ? '✅' : '⚠️' }}
            </option>
          </select>
          <p class="setting-hint">
            {{ currentModelStatus }}
          </p>
        </div>

        <!-- API Base URL -->
        <div class="setting-group">
          <label class="setting-label">API Base URL</label>
          <input
            v-model="localConfig.apiBaseUrl"
            class="setting-input"
            placeholder="例如: https://api.deepseek.com/v1"
          />
          <p class="setting-hint">模型的 API 端点地址</p>
        </div>

        <!-- API Key -->
        <div class="setting-group">
          <label class="setting-label">API Key</label>
          <div class="input-with-toggle">
            <input
              v-model="apiKeyInput"
              :type="showApiKey ? 'text' : 'password'"
              class="setting-input"
              :placeholder="apiKeyPlaceholder"
            />
            <button class="toggle-visibility" @click="showApiKey = !showApiKey" type="button">
              {{ showApiKey ? '🙈' : '👁️' }}
            </button>
          </div>
          <p class="setting-hint">
            <span v-if="hasApiKey">✅ 已在 .env 中配置</span>
            <span v-else style="color: #f38ba8">⚠️ 未配置，请输入 API Key</span>
          </p>
        </div>

        <!-- Test Connection -->
        <div class="setting-group">
          <button 
            class="btn btn-test" 
            @click="testConnection"
            :disabled="testingConnection"
          >
            {{ testingConnection ? '测试中...' : '🔗 测试连接' }}
          </button>
          <p v-if="connectionMessage" class="setting-hint" :class="connectionSuccess ? 'success' : 'error'">
            {{ connectionMessage }}
          </p>
        </div>

        <hr class="divider" />

        <!-- Available Models List -->
        <div class="setting-group">
          <div class="section-header">
            <label class="setting-label">可用模型列表</label>
            <button class="btn btn-add" @click="showAddModel = true">➕ 添加模型</button>
          </div>
          <div class="models-list">
            <div 
              v-for="model in availableModels" 
              :key="model.id" 
              class="model-item"
              :class="{ active: model.id === localConfig.model }"
            >
              <div class="model-info">
                <span class="model-name">{{ model.name }}</span>
                <span class="model-status">
                  <span v-if="model.configured">✅ 已配置</span>
                  <span v-else style="color: #f38ba8">⚠️ 未配置</span>
                </span>
              </div>
              <div class="model-actions">
                <button 
                  v-if="model.id !== localConfig.model"
                  class="btn btn-use"
                  @click="selectModel(model.id)"
                >
                  使用
                </button>
                <span v-else class="current-label">当前</span>
              </div>
            </div>
          </div>
        </div>

        <hr class="divider" />

        <!-- Model Parameters -->
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

    <!-- Add Model Modal -->
    <div v-if="showAddModel" class="modal-overlay" @click.self="showAddModel = false">
      <div class="modal-content add-model-modal">
        <div class="modal-header">
          <h2>➕ 添加新模型</h2>
          <button class="close-btn" @click="showAddModel = false">×</button>
        </div>
        <div class="modal-body">
          <div class="setting-group">
            <label class="setting-label">模型 ID</label>
            <input v-model="newModel.id" class="setting-input" placeholder="例如: my-custom-model" />
          </div>
          <div class="setting-group">
            <label class="setting-label">显示名称</label>
            <input v-model="newModel.name" class="setting-input" placeholder="例如: My Custom Model" />
          </div>
          <div class="setting-group">
            <label class="setting-label">提供商</label>
            <input v-model="newModel.provider" class="setting-input" placeholder="例如: openai" />
          </div>
          <div class="setting-group">
            <label class="setting-label">API Base URL</label>
            <input v-model="newModel.api_base_url" class="setting-input" placeholder="https://api.example.com/v1" />
          </div>
          <div class="setting-group">
            <label class="setting-label">API Key</label>
            <input v-model="newModel.apiKey" type="password" class="setting-input" placeholder="输入 API Key" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showAddModel = false">取消</button>
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
import { useSettingsStore, type ModelConfig, type ModelProfile } from '@/stores/settings'

const emit = defineEmits<{
  close: []
}>()

const props = defineProps<{
  show?: boolean
}>()

const settingsStore = useSettingsStore()

const localConfig = ref<ModelConfig>({
  model: '',
  apiKey: '',
  apiBaseUrl: '',
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

const showAddModel = ref(false)
const addingModel = ref(false)
const newModel = ref({
  id: '',
  name: '',
  provider: '',
  api_base_url: '',
  apiKey: ''
})

const currentModelStatus = computed(() => {
  const model = availableModels.value.find(m => m.id === selectedModelId.value)
  if (!model) return ''
  return model.configured 
    ? '✅ 模型已配置，可以使用' 
    : '⚠️ API Key 未配置，请输入'
})

const apiKeyPlaceholder = computed(() => {
  return hasApiKey.value ? '已配置（输入可更新）' : '请输入 API Key'
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
    loadModels()
  ])
}

async function loadCurrentConfig() {
  try {
    const response = await fetch('http://localhost:8765/api/config')
    if (response.ok) {
      const data = await response.json()
      localConfig.value = {
        model: data.model || 'deepseek-chat',
        apiKey: '',
        apiBaseUrl: data.apiBaseUrl || '',
        temperature: data.temperature || 0.7,
        maxTokens: data.maxTokens || 2048
      }
      selectedModelId.value = localConfig.value.model
      
      // Check API key status
      await checkApiKeyStatus()
    }
  } catch (error) {
    console.error('[Settings] Failed to load config:', error)
  }
}

async function loadModels() {
  try {
    const response = await fetch('http://localhost:8765/api/models')
    if (response.ok) {
      const data = await response.json()
      availableModels.value = data.models || []
    }
  } catch (error) {
    console.error('[Settings] Failed to load models:', error)
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

async function onModelChange() {
  if (!selectedModelId.value) return
  
  try {
    const result = await settingsStore.switchModel(selectedModelId.value)
    
    if (result.success) {
      localConfig.value.model = selectedModelId.value
      if (result.apiBaseUrl) {
        localConfig.value.apiBaseUrl = result.apiBaseUrl
      }
      
      // Check API key for new model
      await checkApiKeyStatus()
      
      connectionMessage.value = ''
    }
  } catch (error) {
    console.error('[Settings] Failed to switch model:', error)
  }
}

async function selectModel(modelId: string) {
  selectedModelId.value = modelId
  await onModelChange()
}

async function testConnection() {
  if (!selectedModelId.value || !localConfig.value.apiBaseUrl) {
    connectionMessage.value = '请先选择模型并配置 API URL'
    connectionSuccess.value = false
    return
  }
  
  testingConnection.value = true
  connectionMessage.value = ''
  
  try {
    // First save API key if input
    if (apiKeyInput.value) {
      await settingsStore.setApiKey(selectedModelId.value, apiKeyInput.value)
      hasApiKey.value = true
    }
    
    const result = await settingsStore.testConnection(
      selectedModelId.value,
      localConfig.value.apiBaseUrl
    )
    
    connectionSuccess.value = result.success
    connectionMessage.value = result.message
  } catch (error) {
    connectionSuccess.value = false
    connectionMessage.value = '连接测试失败'
  } finally {
    testingConnection.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    // Save API key if changed
    if (apiKeyInput.value) {
      await settingsStore.setApiKey(selectedModelId.value, apiKeyInput.value)
    }
    
    // Save config
    await settingsStore.saveConfig(localConfig.value)
    emit('close')
  } catch (error) {
    console.error('Failed to save settings:', error)
    alert('保存设置失败，请重试')
  } finally {
    saving.value = false
  }
}

async function addCustomModel() {
  if (!newModel.value.id || !newModel.value.api_base_url) {
    alert('请填写模型 ID 和 API URL')
    return
  }
  
  addingModel.value = true
  try {
    const model: ModelProfile = {
      id: newModel.value.id,
      name: newModel.value.name || newModel.value.id,
      provider: newModel.value.provider || 'custom',
      api_base_url: newModel.value.api_base_url,
      api_key_env: `${newModel.value.id.toUpperCase()}_API_KEY`,
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
      showAddModel.value = false
      newModel.value = { id: '', name: '', provider: '', api_base_url: '', apiKey: '' }
    } else {
      alert('添加模型失败')
    }
  } catch (error) {
    console.error('Failed to add model:', error)
    alert('添加模型失败')
  } finally {
    addingModel.value = false
  }
}

async function restartAllServices() {
  if (!confirm('确定要重启所有服务吗？这将关闭并重新启动客户端和后端服务。')) {
    return
  }

  restarting.value = true
  try {
    console.log('[Restart] Requesting full restart...')
    const result = await (window as any).api.restartAll()
    
    if (result.success) {
      console.log('[Restart] Restart initiated')
    } else {
      alert('重启失败: ' + (result.error || '未知错误'))
      restarting.value = false
    }
  } catch (error) {
    console.error('[Restart] Failed to restart:', error)
    alert('重启服务失败，请手动重启')
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
  width: 90%;
  max-width: 550px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.add-model-modal {
  max-width: 450px;
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
  font-size: 1.3rem;
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
  padding: 24px;
}

.setting-group {
  margin-bottom: 20px;
}

.setting-label {
  display: block;
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 8px;
}

.setting-select,
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

.setting-select:focus,
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

.setting-range {
  width: 100%;
  margin: 8px 0;
  cursor: pointer;
}

.setting-hint {
  color: #6c7086;
  font-size: 0.8rem;
  margin: 6px 0 0;
  line-height: 1.4;
}

.setting-hint.success {
  color: #a6e3a1;
}

.setting-hint.error {
  color: #f38ba8;
}

.divider {
  border: none;
  border-top: 1px solid #313244;
  margin: 20px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header .setting-label {
  margin-bottom: 0;
}

.models-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #313244;
  border-radius: 8px;
  background: #181825;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #313244;
  transition: background 0.2s;
}

.model-item:last-child {
  border-bottom: none;
}

.model-item:hover {
  background: #1e1e2e;
}

.model-item.active {
  background: #313244;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-name {
  color: #cdd6f4;
  font-size: 0.9rem;
}

.model-status {
  font-size: 0.75rem;
}

.model-actions {
  display: flex;
  align-items: center;
}

.current-label {
  color: #89b4fa;
  font-size: 0.85rem;
  font-weight: 500;
}

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

.btn-test {
  background: #45475a;
  color: #cdd6f4;
  width: 100%;
}

.btn-test:hover:not(:disabled) {
  background: #585b70;
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-add {
  background: #45475a;
  color: #cdd6f4;
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-add:hover {
  background: #585b70;
}

.btn-use {
  background: #89b4fa;
  color: #1e1e2e;
  padding: 4px 12px;
  font-size: 0.8rem;
}

.btn-use:hover {
  background: #74c7ec;
}
</style>
