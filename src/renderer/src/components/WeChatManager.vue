<template>
  <div class="wechat-manager">
    <!-- QR Code Section -->
    <div v-if="chatStore.wechatConnections.length === 0" class="wechat-empty">
      <!-- QR Login Active -->
      <div v-if="qrStatus === 'pending' && qrCodeUrl" class="qrcode-display">
        <p class="qrcode-title">📱 微信扫码授权</p>
        <div class="qrcode-container">
          <canvas ref="qrcodeCanvas" class="qrcode-canvas"></canvas>
        </div>
        <button 
          class="btn btn-refresh" 
          @click="refreshQRLogin"
          :disabled="qrOperating"
        >
          {{ qrOperating ? '刷新中...' : '🔄 刷新二维码' }}
        </button>
      </div>
      
      <!-- No QR Code -->
      <div v-else class="qrcode-placeholder">
        <div class="qrcode-icon">📱</div>
        <p class="qrcode-title">扫码授权连接</p>
        <button 
          class="btn btn-scan" 
          @click="startQRLogin"
          :disabled="qrOperating"
        >
          {{ qrOperating ? '生成中...' : '🔍 生成二维码' }}
        </button>
      </div>
    </div>
    
    <div v-else class="wechat-connected">
      <div class="connected-header">
        <span class="connected-label">当前连接的微信账号</span>
        <span class="connected-hint">（扫码新账号将替换当前连接）</span>
      </div>
      
      <div class="connection-list">
        <div 
          v-for="conn in chatStore.wechatConnections" 
          :key="conn.user_id"
          class="connection-item"
        >
          <img :src="conn.avatar || defaultAvatar" class="connection-avatar" />
          <div class="connection-info">
            <p class="connection-name">{{ conn.nickname }}</p>
            <p class="connection-id">ID: {{ conn.user_id.substring(0, 8) }}...</p>
            <p class="connection-time">
              连接时间: {{ formatTime(conn.connected_at) }}
            </p>
          </div>
          <button class="btn btn-disconnect" @click="disconnectWeChat(conn.user_id)">
            断开连接
          </button>
        </div>
      </div>
    </div>
    
    <hr class="section-divider" />
    
    <!-- WeChat Gateway Integration Status -->
    <div class="integration-status-card">
      <div class="status-header">
        <span class="status-label">微信集成方式</span>
        <span class="status-badge running">Gateway 集成</span>
      </div>
      <div class="status-details">
        <p class="status-info">
          ✅ 通过 Hermes Gateway 连接微信<br>
          💬 Gateway 自动处理并回复消息<br>
          🔄 Desktop 同步显示 Gateway 会话
        </p>
      </div>
    </div>
    
    <!-- Command Guide -->
    <div class="usage-guide">
      <h4 class="guide-title">💡 Gateway 模式说明</h4>
      <p class="hint">
        Gateway 独立运行并自动处理微信消息。<br>
        Desktop 从 Gateway 同步会话和消息显示。<br>
        在微信中直接发送消息即可与 AI 对话。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { fetchWithAuth } from '@/utils/api'
import { useChatStore } from '@/stores/chat'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import QRCode from 'qrcode'

const chatStore = useChatStore()
const toast = useToast()
const confirm = useConfirm()

const defaultAvatar = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40"%3E%3Ccircle cx="20" cy="20" r="20" fill="%2307C160"/%3E%3Ctext x="20" y="25" text-anchor="middle" fill="white" font-size="16"%3E微%3C/text%3E%3C/svg%3E'

// QR Login state
const qrStatus = ref('idle')
const qrCodeUrl = ref('')
const qrOperating = ref(false)
const qrcodeCanvas = ref<HTMLCanvasElement | null>(null)

// QR Login functions
async function startQRLogin() {
  qrOperating.value = true
  try {
    const response = await fetchWithAuth('/api/wechat/qr-login')
    const data = await response.json()
    
    if (data.status === 'pending' && data.qrcode_url) {
      qrStatus.value = 'pending'
      qrCodeUrl.value = data.qrcode_url
      
      // Render QR code to canvas
      await nextTick()
      if (qrcodeCanvas.value && data.qrcode_url) {
        QRCode.toCanvas(qrcodeCanvas.value, data.qrcode_url, {
          width: 256,
          margin: 2,
          color: { dark: '#000000', light: '#ffffff' }
        })
      }
      
      // Poll for status
      pollQRStatus()
    } else {
      toast.error('生成二维码失败: ' + (data.message || '未知错误'))
    }
  } catch (error) {
    console.error('Failed to start QR login:', error)
    toast.error('生成二维码失败')
  } finally {
    qrOperating.value = false
  }
}

async function pollQRStatus() {
  const maxPolls = 120 // 2 minutes
  let pollCount = 0
  
  const poll = async () => {
    if (pollCount >= maxPolls || qrStatus.value !== 'pending') {
      return
    }
    
    pollCount++
    
    try {
      const response = await fetchWithAuth('/api/wechat/qr-status')
      const data = await response.json()
      
      if (data.status === 'confirmed') {
        qrStatus.value = 'confirmed'
        qrCodeUrl.value = ''
        // Refresh connections
        await refreshWeChatConnections()
      } else if (data.status === 'expired') {
        qrStatus.value = 'expired'
        qrCodeUrl.value = ''
        toast.warning('二维码已过期，请重新生成')
      } else if (data.status === 'pending') {
        // Continue polling
        setTimeout(poll, 1000)
      }
    } catch (error) {
      console.error('Failed to poll QR status:', error)
      setTimeout(poll, 2000)
    }
  }
  
  poll()
}

async function cancelQRLogin() {
  try {
    await fetchWithAuth('/api/wechat/qr-cancel', { method: 'POST' })
    qrStatus.value = 'idle'
    qrCodeUrl.value = ''
  } catch (error) {
    console.error('Failed to cancel QR login:', error)
  }
}

async function refreshQRLogin() {
  // Cancel current login
  await cancelQRLogin()
  
  // Start new login
  await startQRLogin()
}

// WeChat connection functions
async function disconnectWeChat(userId: string) {
  const confirmed = await confirm.danger(
    '确定要断开此微信连接吗？',
    '断开连接'
  )
  
  if (!confirmed) {
    return
  }
  
  try {
    await fetchWithAuth('/api/wechat/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    })
    
    // Refresh connection list
    await refreshWeChatConnections()
  } catch (error) {
    console.error('Failed to disconnect WeChat:', error)
    toast.error('断开连接失败')
  }
}

async function refreshWeChatConnections() {
  try {
    const response = await fetchWithAuth('/api/wechat/connections')
    const data = await response.json()
    chatStore.wechatConnections = data.connections || []
  } catch (error) {
    console.error('Failed to refresh WeChat connections:', error)
  }
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return '未知'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  await refreshWeChatConnections()
})
</script>

<style scoped>
.wechat-manager {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

/* QR Code Section */
.wechat-empty {
  text-align: center;
}

.qrcode-display {
  padding: 32px 20px;
  background: rgba(7, 193, 96, 0.05);
  border: 2px solid #07C160;
  border-radius: 12px;
  margin-bottom: 24px;
  text-align: center;
}

.qrcode-container {
  display: inline-block;
  padding: 16px;
  background: white;
  border-radius: 8px;
  margin: 16px auto;
}

.qrcode-canvas {
  display: block;
}

.qrcode-url {
  font-size: 0.75rem;
  color: #6c7086;
  margin: 8px 0;
  word-break: break-all;
}

.btn-cancel {
  background: #45475a;
  color: #cdd6f4;
  padding: 8px 20px;
  border-radius: 6px;
  margin-top: 12px;
}

.btn-cancel:hover {
  background: #585b70;
}

.btn-refresh {
  display: block;
  background: #89b4fa;
  color: #1e1e2e;
  padding: 8px 20px;
  border-radius: 6px;
  margin: 12px auto 0;
}

.btn-refresh:hover {
  background: #74c7ec;
}

.btn-refresh:disabled {
  background: #45475a;
  color: #a6adc8;
  cursor: not-allowed;
}

.btn-scan {
  background: #07C160;
  color: white;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 1rem;
  margin-top: 16px;
}

.btn-scan:hover {
  background: #06a050;
}

.btn-scan:disabled {
  background: #45475a;
  color: #a6adc8;
  cursor: not-allowed;
}

.qrcode-placeholder {
  padding: 40px 20px;
  background: rgba(7, 193, 96, 0.05);
  border: 2px dashed #07C160;
  border-radius: 12px;
  margin-bottom: 24px;
}

.qrcode-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.qrcode-title {
  font-size: 1.1rem;
  color: #e0e0e0;
  margin: 0 0 8px;
}

.qrcode-hint {
  font-size: 0.9rem;
  color: #a0a0a0;
  margin: 0;
}

/* Connected Section */
.wechat-connected {
  text-align: left;
}

.connected-header {
  margin-bottom: 16px;
}

.connected-label {
  font-size: 0.95rem;
  color: #cdd6f4;
  font-weight: 500;
}

.connected-hint {
  font-size: 0.8rem;
  color: #6c7086;
  margin-left: 8px;
}

.connection-list {
  margin-bottom: 24px;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #181825;
  border: 1px solid #313244;
  border-radius: 8px;
  margin-bottom: 12px;
}

.connection-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #07C160;
}

.connection-info {
  flex: 1;
}

.connection-name {
  margin: 0;
  font-size: 1rem;
  color: #cdd6f4;
  font-weight: 500;
}

.connection-id {
  margin: 4px 0;
  font-size: 0.85rem;
  color: #a6adc8;
}

.connection-time {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: #6c7086;
}

.btn-disconnect {
  background: rgba(243, 139, 168, 0.1);
  color: #f38ba8;
  border: 1px solid #f38ba8;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-disconnect:hover {
  background: #f38ba8;
  color: white;
}

.usage-guide {
  padding: 16px;
  background: rgba(137, 180, 250, 0.05);
  border: 1px solid #45475a;
  border-radius: 8px;
}

.guide-title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  color: #89b4fa;
}

.command-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.command-list li {
  margin: 6px 0;
  font-size: 0.9rem;
  color: #a6adc8;
}

.command-list code {
  background: #313244;
  padding: 2px 8px;
  border-radius: 4px;
  color: #f9e2af;
  font-family: monospace;
}

/* Divider */
.section-divider {
  border: none;
  border-top: 1px solid #313244;
  margin: 24px 0;
}

.usage-guide .hint {
  margin-top: 12px;
  padding: 10px;
  background: rgba(137, 180, 250, 0.1);
  border-radius: 6px;
  font-size: 0.85rem;
  color: #89b4fa;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-label {
  font-size: 0.95rem;
  color: #cdd6f4;
  font-weight: 500;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-badge.running {
  background: rgba(166, 227, 161, 0.2);
  color: #a6e3a1;
}

.status-badge.stopped {
  background: rgba(243, 139, 168, 0.2);
  color: #f38ba8;
}

.status-details {
  margin-bottom: 16px;
}

.status-info {
  margin: 0;
  font-size: 0.85rem;
  color: #a6adc8;
}

.btn {
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-start {
  background: #a6e3a1;
  color: #1e1e2e;
}

.btn-start:hover {
  background: #94e2d5;
}

.btn-stop {
  background: #f38ba8;
  color: #1e1e2e;
}

.btn-stop:hover {
  background: #eba0ac;
}

.btn-refresh-status {
  background: #45475a;
  color: #cdd6f4;
}

.btn-refresh-status:hover {
  background: #585b70;
}
</style>
