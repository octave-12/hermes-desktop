import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ModelConfig {
  model: string
  apiKey: string
  apiBaseUrl: string
  temperature: number
  maxTokens: number
}

export const useSettingsStore = defineStore('settings', () => {
  const config = ref<ModelConfig>({
    model: 'gpt-4o',
    apiKey: '',
    apiBaseUrl: '',
    temperature: 0.7,
    maxTokens: 2048
  })

  // Load config from backend
  async function loadConfig(): Promise<ModelConfig | null> {
    try {
      const response = await fetch('http://localhost:8765/api/config')
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

  // Save config to backend
  async function saveConfig(newConfig: ModelConfig): Promise<boolean> {
    try {
      const response = await fetch('http://localhost:8765/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
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

  // Update specific config field
  function updateField<K extends keyof ModelConfig>(key: K, value: ModelConfig[K]) {
    config.value[key] = value
  }

  return {
    config,
    loadConfig,
    saveConfig,
    updateField
  }
})
