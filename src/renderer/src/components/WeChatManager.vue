<template>
  <div class="wechat-manager">
    <!-- Connected State -->
    <div v-if="chatStore.wechatConnections.length > 0" class="wechat-connected">
      <div class="connected-header">
        <span class="connected-label">✅ 微信已连接</span>
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
            <p class="connection-id">ID: {{ conn.user_id.substring(0, 16) }}...</p>
            <p class="connection-time">
              连接时间: {{ formatTime(conn.connected_at) }}
            </p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- QR Code Section (only when not connected) -->
    <div v-else class="wechat-empty">
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
    
    <hr class="section-divider" />
    
    <!-- Gateway Status -->
    <div class="integration-status-card">
      <div class="status-header">
        <span class="status-label">微信集成方式</span>
        <span class="status-badge" :class="gatewayStatus.connected ? 'running' : 'stopped'">
          {{ gatewayStatus.connected ? '已连接' : '未连接' }}
        </span>
      </div>
      <div class="status-details">
        <p class="status-info">
          <span v-if="gatewayStatus.gateway_running">✅ Gateway 运行中</span>
          <span v-else>⚠️ Gateway 未运行</span>
          <br>
          💬 Gateway 自动处理微信消息
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { fetchWithAuth } from '@/utils/api'
import { useChatStore } from '@/stores/chat'
import { useToast } from '@/composables/useToast'
import QRCode from 'qrcode'

const chatStore = useChatStore()
const toast = useToast()

const defaultAvatar = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40"%3E%3Ccircle cx="20" cy="20" r="20" fill="%2307C160"/%3E%3Ctext x="20" y="25" text-anchor="middle" fill="white" font-size="16"%3E微%3C/text%3E%3C/svg%3E'

const qrStatus = ref('idle')
const qrCodeUrl = ref('')
const qrOperating = ref(false)
const qrcodeCanvas = ref<HTMLCanvasElement | null>(null)

const gatewayStatus = ref({
  gateway_running: false,
  connected: false
})

async function startQRLogin() {
  qrOperating.value = true
  try {
    const response = await fetchWithAuth('/api/wechat/qr-login')
    const data = await response.json()
    
    if (data.status === 'pending' && data.qrcode_url) {
      qrStatus.value = 'pending'
      qrCodeUrl.value = data.qrcode_url
      
      await nextTick()
      if (qrcodeCanvas.value && data.qrcode_url) {
        QRCode.toCanvas(qrcodeCanvas.value, data.qrcode_url, {
          width: 256,
          margin: 2,
          color: { dark: '#000000', light: '#ffffff' }
        })
      }
      
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
  const maxPolls = 120
  let pollCount = 0
  
  while (pollCount < maxPolls) {
    try {
      const response = await fetchWithAuth('/api/wechat/qr-status')
      const data = await response.json()
      
      if (data.status === 'confirmed') {
        qrStatus.value = 'confirmed'
        toast.success('微信授权成功！')
        await refreshWeChatConnections()
        return
      }
      
      if (data.status === 'expired' || data.status === 'error') {
        qrStatus.value = 'expired'
        toast.error('二维码已过期，请重新扫描')
        return
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000))
      pollCount++
    } catch (error) {
      console.error('Failed to poll QR status:', error)
      break
    }
  }
}

async function refreshQRLogin() {
  qrStatus.value = 'idle'
  qrCodeUrl.value = ''
  await startQRLogin()
}

async function refreshWeChatConnections() {
  try {
    const response = await fetchWithAuth('/api/wechat/connections')
    const data = await response.json()
    chatStore.wechatConnections = Array.isArray(data) ? data : (data.connections || [])
  } catch (error) {
    console.error('Failed to refresh WeChat connections:', error)
  }
}

async function checkGatewayStatus() {
  try {
    const response = await fetchWithAuth('/api/wechat/gateway/status')
    const data = await response.json()
    gatewayStatus.value = {
      gateway_running: data.gateway_running || false,
      connected: data.weixin_connected || false
    }
  } catch (error) {
    console.error('Failed to check gateway status:', error)
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
  await checkGatewayStatus()
})
</script>

<style scoped>
.wechat-manager {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.wechat-empty {
  text-align: center;
}

.wechat-connected {
  margin-bottom: 24px;
}

.connected-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.connected-label {
  font-size: 1rem;
  font-weight: 500;
  color: #a6e3a1;
}

.connection-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(7, 193, 96, 0.05);
  border: 1px solid rgba(7, 193, 96, 0.2);
  border-radius: 8px;
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
  font-weight: 500;
  margin-bottom: 4px;
}

.connection-id,
.connection-time {
  font-size: 0.8rem;
  color: #6c7086;
  margin: 0;
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

.qrcode-placeholder {
  padding: 40px 20px;
  text-align: center;
}

.qrcode-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.qrcode-title {
  font-size: 1.1rem;
  color: #cdd6f4;
  margin-bottom: 20px;
}

.btn {
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-scan {
  background: #07C160;
  color: white;
  border: none;
}

.btn-scan:hover {
  background: #06a050;
}

.btn-refresh {
  background: #45475a;
  color: #cdd6f4;
  border: 1px solid #585b70;
}

.btn-refresh:hover {
  background: #585b70;
}

.section-divider {
  border: none;
  border-top: 1px solid #313244;
  margin: 24px 0;
}

.integration-status-card {
  background: #1e1e2e;
  border: 1px solid #313244;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-label {
  font-weight: 500;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
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
  font-size: 0.9rem;
}

.status-info {
  color: #a6adc8;
  line-height: 1.6;
  margin: 0;
}

.usage-guide {
  background: rgba(137, 180, 250, 0.05);
  border: 1px solid rgba(137, 180, 250, 0.2);
  border-radius: 8px;
  padding: 16px;
}

.guide-title {
  font-size: 0.9rem;
  margin: 0 0 8px 0;
  color: #89b4fa;
}

.hint {
  font-size: 0.85rem;
  color: #6c7086;
  line-height: 1.6;
  margin: 0;
}
</style>
