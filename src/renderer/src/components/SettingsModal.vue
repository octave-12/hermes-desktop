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
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'voice' }"
          @click="activeTab = 'voice'"
        >
          🎤 语音模式
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
        
        <!-- Voice Settings Tab -->
        <div v-if="activeTab === 'voice'" class="voice-settings">
          <!-- Voice Mode Toggle -->
          <div class="setting-group">
            <label class="setting-label">语音模式</label>
            <div class="toggle-row">
              <label class="switch">
                <input type="checkbox" v-model="voiceSettings.enabled" />
                <span class="slider"></span>
              </label>
              <span class="toggle-label">{{ voiceSettings.enabled ? '开启' : '关闭' }}</span>
            </div>
            <p class="setting-hint">开启后可通过唤醒词进行语音对话</p>
          </div>

          <hr class="divider" />

          <!-- Wake Word -->
          <div class="setting-group">
            <label class="setting-label">唤醒词</label>
            <div class="wake-word-row">
              <input
                v-model="voiceSettings.wakeWord"
                class="setting-input wake-word-input"
                placeholder="例如: 小马"
                maxlength="10"
              />
              <button 
                class="btn btn-test" 
                @click="voiceInputWakeWord"
                :disabled="micTesting"
              >
                {{ micTesting ? '🎤 识别中...' : '🎤 语音录入' }}
              </button>
              <button 
                class="btn btn-test" 
                @click="testTTS"
                :disabled="ttsTesting"
              >
                {{ ttsTesting ? '🔊 测试中' : '🔊 测试语音' }}
              </button>
            </div>
            <p class="setting-hint">说出唤醒词来激活语音对话模式</p>
          </div>

          <hr class="divider" />

          <!-- TTS Voice Selection -->
          <div class="setting-group">
            <label class="setting-label">语音播报音色</label>
            <select v-model="voiceSettings.ttsVoice" class="setting-input">
              <option value="zh-CN-XiaoxiaoNeural">晓晓（女声，中文）</option>
              <option value="zh-CN-YunxiNeural">云希（男声，中文）</option>
              <option value="zh-CN-YunyangNeural">云扬（男声，新闻）</option>
              <option value="en-US-JennyNeural">Jenny（女声，英文）</option>
              <option value="ja-JP-NanamiNeural">Nanami（女声，日文）</option>
            </select>
            <p class="setting-hint">AI 回复时将使用所选音色朗读</p>
          </div>

          <hr class="divider" />

          <!-- Speech Speed -->
          <div class="setting-group">
            <label class="setting-label">朗读语速</label>
            <div class="speed-row">
              <span class="speed-label">0.5x</span>
              <input
                type="range"
                v-model.number="voiceSettings.speed"
                min="0.5"
                max="2.0"
                step="0.1"
                class="speed-slider"
              />
              <span class="speed-label">2.0x</span>
              <span class="speed-value">{{ voiceSettings.speed.toFixed(1) }}x</span>
            </div>
            <p class="setting-hint">调整 AI 语音播报的朗读速度</p>
          </div>

          <hr class="divider" />

          <!-- Usage Guide -->
          <div class="usage-guide">
            <div class="guide-header">📖 使用说明</div>
            <div class="guide-steps">
              <div class="guide-step">① 开启「语音模式」，用「🎤 语音录入」设置唤醒词</div>
              <div class="guide-step">② 对麦克风说唤醒词「{{ voiceSettings.wakeWord }}」，看到提示后说出问题</div>
              <div class="guide-step">③ AI 回复后自动朗读，直接说下句话继续对话，长时间无对话自动暂停</div>
            </div>
            <div class="guide-note">
              需要 Chrome/Edge · 语速可调（0.5x~2.0x） · 唤醒不灵敏？试试更长的词（如「你好小马」）
            </div>
          </div>
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
            <input v-model="newModel.id" class="setting-input" placeholder="例如: gpt-4o, deepseek-v4-pro" />
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

const activeTab = ref<'model' | 'memory' | 'wechat' | 'voice'>('model')

const localConfig = ref({
  model: '',
  provider: '',
  temperature: 0.7,
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
        model: data.model || 'deepseek-v4-pro',
        provider: data.provider || 'deepseek',
        temperature: data.temperature || 0.7,

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

// ── Voice Settings ─────────────────────────────────────────
interface VoiceSettingsData {
  enabled: boolean
  wakeWord: string
  ttsVoice: string
  continuousMode: boolean
  speed: number
}

function loadVoiceSettings(): VoiceSettingsData {
  const defaults: VoiceSettingsData = { enabled: false, wakeWord: '小马', ttsVoice: 'zh-CN-XiaoxiaoNeural', continuousMode: true, speed: 1.0 }
  try {
    const saved = localStorage.getItem('hermes_voice_settings')
    if (saved) {
      return { ...defaults, ...JSON.parse(saved) }
    }
  } catch { /* ignore */ }
  return defaults
}

const voiceSettings = ref<VoiceSettingsData>(loadVoiceSettings())
const micTesting = ref(false)
const ttsTesting = ref(false)

watch(voiceSettings, (newVal) => {
  localStorage.setItem('hermes_voice_settings', JSON.stringify(newVal))
  // Notify other components (e.g. useVoiceMode in ChatView)
  window.dispatchEvent(new CustomEvent('voice-settings-changed', { detail: newVal }))
}, { deep: true })

async function voiceInputWakeWord() {
  micTesting.value = true
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach(t => t.stop())

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) {
      toast.warning('⚠️ 当前环境不支持语音识别，请使用 Chrome/Edge')
      return
    }

    toast.info('🎤 请说出唤醒词...')
    await new Promise<void>((resolve, reject) => {
      const sr = new SR()
      sr.lang = 'zh-CN'
      sr.continuous = false
      sr.interimResults = false
      const timer = setTimeout(() => {
        try { sr.stop() } catch {}
        toast.warning('⚠️ 5秒内未检测到语音，请检查麦克风')
        resolve()
      }, 5000)

      sr.onresult = (e: any) => {
        clearTimeout(timer)
        const text = e.results[0][0].transcript.trim()
        voiceSettings.value.wakeWord = text
        toast.success(`✅ 唤醒词已设为「${text}」`)
        try { sr.stop() } catch {}
        resolve()
      }
      sr.onerror = (e: any) => {
        clearTimeout(timer)
        if (e.error === 'not-allowed') {
          toast.error('❌ 麦克风权限被拒绝')
          reject(new Error('mic denied'))
        } else if (e.error === 'no-speech') {
          toast.warning('⚠️ 未检测到声音，麦克风可能未连接')
          resolve()
        } else {
          toast.warning(`⚠️ 语音识别错误: ${e.error}`)
          resolve()
        }
      }
      try { sr.start() } catch (e) { reject(e) }
    })
  } catch (e) {
    console.error('[VoiceSettings] Voice input failed:', e)
    if (e instanceof DOMException && e.name === 'NotAllowedError') {
      toast.error('❌ 请在浏览器设置中允许麦克风权限')
    } else if (e instanceof DOMException && e.name === 'NotFoundError') {
      toast.error('❌ 未检测到麦克风设备')
    } else {
      toast.warning('语音录入失败')
    }
  } finally {
    micTesting.value = false
  }
}

async function testTTS() {
  ttsTesting.value = true
  try {
    const response = await fetchWithAuth('/api/tts/speak', {
      method: 'POST',
      body: JSON.stringify({
        text: `语音测试完成，唤醒词「${voiceSettings.value.wakeWord}」已设置`,
        voice: voiceSettings.value.ttsVoice,
      }),
    })
    if (!response.ok) throw new Error('TTS failed')
    const data = await response.json()
    if (data.success && data.audio_url) {
      const audio = new Audio(`${window.location.protocol}//${window.location.hostname}:8765${data.audio_url}`)
      audio.play()
    }
  } catch (e) {
    console.error('[VoiceSettings] TTS test failed:', e)
    toast.warning('语音播报测试失败，请确认后端已安装 edge-tts')
  } finally {
    ttsTesting.value = false
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

/* ── Voice Settings ── */
.wake-word-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.wake-word-input {
  flex: 1;
  font-size: 1.1rem;
  font-weight: 600;
  text-align: center;
  letter-spacing: 2px;
}

.usage-guide {
  background: #181825;
  border: 1px solid #313244;
  border-radius: 8px;
  padding: 16px;
  margin-top: 12px;
}

.guide-header {
  font-weight: 600;
  color: #cdd6f4;
  margin-bottom: 12px;
  font-size: 0.95rem;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guide-step {
  color: #a6adc8;
  font-size: 0.85rem;
  line-height: 1.5;
}

.guide-note {
  margin-top: 12px;
  padding: 10px 12px;
  background: #1e1e2e;
  border-left: 3px solid #89b4fa;
  border-radius: 0 6px 6px 0;
  color: #a6adc8;
  font-size: 0.8rem;
  line-height: 1.6;
}

.guide-note strong {
  color: #cdd6f4;
}

.speed-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.speed-label {
  font-size: 12px;
  color: #6c7086;
  min-width: 28px;
  text-align: center;
}
.speed-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  outline: none;
  margin: 0;
}
.speed-slider::-webkit-slider-runnable-track {
  height: 6px;
  background: #313244;
  border-radius: 3px;
  border: none;
}
.speed-slider::-moz-range-track {
  height: 6px;
  background: #313244;
  border-radius: 3px;
  border: none;
}
.speed-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #89b4fa;
  cursor: pointer;
  box-shadow: 0 0 6px rgba(137, 180, 250, 0.4);
  margin-top: -6px;
}
.speed-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #89b4fa;
  cursor: pointer;
  border: none;
  box-shadow: 0 0 6px rgba(137, 180, 250, 0.4);
}
.speed-value {
  font-size: 13px;
  font-weight: 600;
  color: #89b4fa;
  min-width: 36px;
  text-align: right;
}
</style>
