import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      getBackendUrl: () => Promise<string>
      restartAll: () => Promise<{ success: boolean; error?: string }>
    }
  }
}
