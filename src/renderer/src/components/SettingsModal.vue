<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>⚙️ 设置</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- Model Selection -->
        <div class="setting-group">
          <label class="setting-label">AI 模型</label>
          <select v-model="localConfig.model" class="setting-select">
            <option value="">加载中...</option>
            <option v-for="model in availableModels" :key="model.id" :value="model.id">
              {{ model.name }}
            </option>
          </select>
          <p class="setting-hint">选择 Hermes Agent 使用的大语言模型</p>
        </div>

        <!-- API Key -->
        <div class="setting-group">
          <label class="setting-label">API Key</label>
          <div class="input-with-toggle">
            <input
              v-model="localConfig.apiKey"
              :type="showApiKey ? 'text' : 'password'"
              class="setting-input"
              placeholder="输入您的 API Key"
            />
            <button class="toggle-visibility" @click="showApiKey = !showApiKey" type="button">
              {{ showApiKey ? '🙈' : '👁️' }}
            </button>
          </div>
          <p class="setting-hint">用于访问 AI 模型的 API 密钥</p>
        </div>

        <!-- API Base URL (optional) -->
        <div class="setting-group">
          <label class="setting-label">API Base URL <span class="optional">(可选)</span></label>
          <input
            v-model="localConfig.apiBaseUrl"
            class="setting-input"
            placeholder="例如: https://api.openai.com/v1"
          />
          <p class="setting-hint">自定义 API 端点地址（留空使用默认值）</p>
        </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useSettingsStore, type ModelConfig } from '@/stores/settings'

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

const availableModels = ref<Array<{ id: string; name: string }>>([
  { id: 'gpt-4o', name: 'GPT-4o' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
  { id: 'claude-3-5-sonnet', name: 'Claude 3.5 Sonnet' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus' },
  { id: 'qwen-max', name: '通义千问 Max' },
  { id: 'qwen-plus', name: '通义千问 Plus' },
  { id: 'deepseek-chat', name: 'DeepSeek Chat' },
  { id: 'glm-4', name: '智谱 GLM-4' }
])

const showApiKey = ref(false)
const saving = ref(false)
const restarting = ref(false)

// Watch for modal open and reload config
watch(
  () => props.show,
  async (newVal) => {
    if (newVal) {
      // Reload config every time modal opens
      await loadCurrentConfig()
    }
  }
)

async function loadCurrentConfig() {
  try {
    const response = await fetch('http://localhost:8765/api/config')
    if (response.ok) {
      const data = await response.json()
      localConfig.value = {
        model: data.model || 'gpt-4o',
        apiKey: data.apiKey || '',
        apiBaseUrl: data.apiBaseUrl || '',
        temperature: data.temperature || 0.7,
        maxTokens: data.maxTokens || 2048
      }
      console.log('[Settings] Loaded config:', localConfig.value)
    }
  } catch (error) {
    console.error('[Settings] Failed to load config:', error)
  }
}

onMounted(async () => {
  // Load current config
  await loadCurrentConfig()
})

async function saveSettings() {
  saving.value = true
  try {
    await settingsStore.saveConfig(localConfig.value)
    emit('close')
  } catch (error) {
    console.error('Failed to save settings:', error)
    alert('保存设置失败，请重试')
  } finally {
    saving.value = false
  }
}

async function restartAllServices() {
  if (!confirm('确定要重启所有服务吗？这将关闭并重新启动客户端和后端服务。')) {
    return
  }

  restarting.value = true
  try {
    console.log('[Restart] Requesting full restart...')
    // Restart all services via IPC
    const result = await (window as any).api.restartAll()
    
    if (result.success) {
      console.log('[Restart] Restart initiated, app will relaunch')
      // App will relaunch automatically, no need to do anything
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
  max-width: 500px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
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
  margin-bottom: 24px;
}

.setting-label {
  display: block;
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 8px;
}

.optional {
  color: #6c7086;
  font-weight: normal;
  font-size: 0.8rem;
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
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 0.9rem;
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
</style>
