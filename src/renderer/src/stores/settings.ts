import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchWithAuth } from '@/utils/api'

export interface ModelProfile {
  id: string
  name: string
  provider: string
  api_base_url: string
  api_key_env: string
  temperature: number
  max_tokens: number
  configured: boolean
}

export interface ModelConfig {
  model: string
  provider: string
  temperature: number
  maxTokens: number
}

export interface DeepSeekSettings {
  thinking: boolean
  reasoningEffort: 'high' | 'max'
}

export const useSettingsStore = defineStore('settings', () => {
  const config = ref<ModelConfig>({
    model: '',
    provider: '',
    temperature: 0.7,
    maxTokens: 2048
  })

  const availableModels = ref<ModelProfile[]>([])

  async function loadConfig(): Promise<ModelConfig | null> {
    try {
      const response = await fetchWithAuth('/api/config')
      if (response.ok) {
        const data = await response.json()
        config.value = { ...config.value, ...data }
        return config.value
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    }
    return null
  }

  async function saveConfig(newConfig: ModelConfig): Promise<boolean> {
    try {
      const response = await fetchWithAuth('/api/config', {
        method: 'POST',
        body: JSON.stringify(newConfig)
      })
      
      if (response.ok) {
        config.value = { ...newConfig }
        return true
      }
    } catch (error) {
      console.error('Failed to save config:', error)
    }
    return false
  }

  function updateField<K extends keyof ModelConfig>(key: K, value: ModelConfig[K]) {
    config.value[key] = value
  }

  async function loadModels(): Promise<ModelProfile[]> {
    try {
      const response = await fetchWithAuth('/api/models')
      if (response.ok) {
        const data = await response.json()
        availableModels.value = data.models || []
        return availableModels.value
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
    return []
  }

  const deepseekSettings = ref<DeepSeekSettings>({
    thinking: false,
    reasoningEffort: 'high'
  })

  async function loadDeepSeekSettings(): Promise<DeepSeekSettings> {
    try {
      const response = await fetchWithAuth('/api/deepseek/settings')
      if (response.ok) {
        const data = await response.json()
        deepseekSettings.value = {
          thinking: data.thinking === true,
          reasoningEffort: data.reasoningEffort || 'high'
        }
        return deepseekSettings.value
      }
    } catch (error) {
      console.error('Failed to load DeepSeek settings:', error)
    }
    return deepseekSettings.value
  }

  async function saveDeepSeekSettings(settings: DeepSeekSettings): Promise<boolean> {
    try {
      const response = await fetchWithAuth('/api/deepseek/settings', {
        method: 'POST',
        body: JSON.stringify(settings)
      })
      if (response.ok) {
        deepseekSettings.value = { ...settings }
        return true
      }
    } catch (error) {
      console.error('Failed to save DeepSeek settings:', error)
    }
    return false
  }

  async function switchModel(modelId: string): Promise<{ success: boolean; needsApiKey?: boolean; apiBaseUrl?: string }> {
    try {
      const response = await fetchWithAuth('/api/model/switch', {
        method: 'POST',
        body: JSON.stringify({ model: modelId })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.status === 'ok') {
          config.value.model = modelId
          return { 
            success: true, 
            needsApiKey: data.needsApiKey,
            apiBaseUrl: data.apiBaseUrl
          }
        }
      }
    } catch (error) {
      console.error('Failed to switch model:', error)
    }
    return { success: false }
  }

  async function setApiKey(modelId: string, apiKey: string): Promise<boolean> {
    try {
      const response = await fetchWithAuth('/api/env/set', {
        method: 'POST',
        body: JSON.stringify({ model: modelId, apiKey })
      })
      
      return response.ok
    } catch (error) {
      console.error('Failed to set API key:', error)
    }
    return false
  }

  async function checkApiKey(modelId: string): Promise<{ hasKey: boolean; maskedKey: string }> {
    try {
      const response = await fetchWithAuth(`/api/env/check/${modelId}`)
      if (response.ok) {
        const data = await response.json()
        return { hasKey: data.hasApiKey, maskedKey: data.apiKey }
      }
    } catch (error) {
      console.error('Failed to check API key:', error)
    }
    return { hasKey: false, maskedKey: '' }
  }

  async function testConnection(modelId: string, apiBaseUrl: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetchWithAuth('/api/test-connection', {
        method: 'POST',
        body: JSON.stringify({ model: modelId, apiBaseUrl })
      })
      
      if (response.ok) {
        const data = await response.json()
        return { 
          success: data.status === 'ok', 
          message: data.message 
        }
      }
    } catch (error) {
      console.error('Failed to test connection:', error)
    }
    return { success: false, message: 'Test failed' }
  }

  async function addCustomModel(model: ModelProfile, apiKey?: string): Promise<boolean> {
    try {
      const response = await fetchWithAuth(`/api/models/${model.id}`, {
        method: 'POST',
        body: JSON.stringify({
          name: model.name,
          provider: model.provider,
          apiBaseUrl: model.api_base_url,
          apiKeyEnv: model.api_key_env,
          temperature: model.temperature,
          maxTokens: model.max_tokens,
          apiKey
        })
      })
      
      return response.ok
    } catch (error) {
      console.error('Failed to add custom model:', error)
    }
    return false
  }

  async function deleteModel(modelId: string): Promise<boolean> {
    try {
      const response = await fetchWithAuth(`/api/models/${modelId}`, {
        method: 'DELETE'
      })
      
      return response.ok
    } catch (error) {
      console.error('Failed to delete model:', error)
    }
    return false
  }

  return {
    config,
    availableModels,
    loadConfig,
    saveConfig,
    updateField,
    loadModels,
    switchModel,
    setApiKey,
    checkApiKey,
    testConnection,
    addCustomModel,
    deleteModel,
    deepseekSettings,
    loadDeepSeekSettings,
    saveDeepSeekSettings
  }
})
