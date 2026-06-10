import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'

// 设置 userData 路径到项目 out 目录（缓存数据）
const customUserDataPath = process.env.HERMES_DATA_DIR || join(__dirname, '../../out/electron-data')
app.setPath('userData', customUserDataPath)

// 单例锁：防止同时运行多个实例
const gotTheLock = app.requestSingleInstanceLock()

if (!gotTheLock) {
  // 如果已经有实例在运行，静默退出
  app.quit()
} else {

// 当尝试启动第二个实例时，聚焦到已有窗口并提示
app.on('second-instance', () => {
  const mainWindow = BrowserWindow.getAllWindows()[0]
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
    mainWindow.webContents.send('app:already-running')
  }
})

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    title: 'Hermes Desktop',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // Dev server URL or production file
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.hermes.desktop')

  // Default open or close DevTools by F12 in development
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // IPC: Get backend connection status
  // TODO: For production, use WSS (WebSocket Secure) and configurable URL
  ipcMain.handle('get-backend-url', () => {
    const protocol = process.env.NODE_ENV === 'production' ? 'wss' : 'ws'
    const host = process.env.BACKEND_HOST || 'localhost:8765'
    return `${protocol}://${host}/ws`
  })

  // IPC: Restart all services (including client)
  ipcMain.handle('restart-all', async () => {
    const { exec } = await import('child_process')
    
    console.log('[Restart] Starting full restart...')
    
    try {
      // Step 1: Kill only Hermes backend (not Gateway/Ollama/龙神)
      console.log('[Restart] Killing Hermes backend only...')
      await new Promise<void>((resolve) => {
        exec('wsl pkill -9 -f "python.*hermes-desktop.*main.py"', (error) => {
          if (error) {
            console.log('[Restart] Backend not running or already stopped')
          }
          console.log('[Restart] Backend killed')
          resolve()
        })
      })
      
      // Step 2: Wait for cleanup
      console.log('[Restart] Waiting 2 seconds for cleanup...')
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Step 3: Launch start.bat (only restarts backend + frontend, keeps Gateway/龙神/Ollama)
      console.log('[Restart] Launching start.bat...')
      const startBatPath = 'D:\\soso\\projects\\hermes-desktop\\start.bat'
      exec(`cmd /c start "" "${startBatPath}"`, (error) => {
        if (error) {
          console.error('[Restart] Failed to start bat:', error.message)
        } else {
          console.log('[Restart] start.bat launched successfully')
        }
      })
      
      // Step 5: Close current app
      console.log('[Restart] Closing current app...')
      app.quit()
      
      return { success: true }
    } catch (error: any) {
      console.error('[Restart] Failed:', error.message)
      return { success: false, error: error.message }
    }
  })

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Clean up all processes when app quits
app.on('will-quit', (event) => {
  console.log('[App] Closing Hermes services (keeping Gateway/龙神/Ollama)...')
  
  const { execSync } = require('child_process')
  
  try {
    // Kill only Hermes backend (not Gateway/龙神/Ollama)
    console.log('[App] Killing Hermes backend...')
    execSync('wsl pkill -9 -f "python.*hermes-desktop.*main.py"', { timeout: 3000 })
    console.log('[App] Hermes backend stopped')
  } catch (error: any) {
    console.error('[App] Failed to kill backend:', error.message)
  }
  
  // Don't prevent quit, just log
  console.log('[App] Quitting...')
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

} // end else (gotTheLock)
