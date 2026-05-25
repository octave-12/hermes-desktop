<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="visible" :class="['toast', type]">
        <span class="toast-icon">{{ icon }}</span>
        <span class="toast-message">{{ message }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const visible = ref(false)
const message = ref('')
const type = ref<'success' | 'error' | 'warning' | 'info'>('info')

const icon = computed(() => {
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }
  return icons[type.value]
})

let timer: NodeJS.Timeout | null = null

function show(msg: string, t: 'success' | 'error' | 'warning' | 'info' = 'info', duration = 3000) {
  message.value = msg
  type.value = t
  visible.value = true
  
  if (timer) clearTimeout(timer)
  
  timer = setTimeout(() => {
    visible.value = false
  }, duration)
}

function success(msg: string, duration?: number) {
  show(msg, 'success', duration)
}

function error(msg: string, duration?: number) {
  show(msg, 'error', duration)
}

function warning(msg: string, duration?: number) {
  show(msg, 'warning', duration)
}

function info(msg: string, duration?: number) {
  show(msg, 'info', duration)
}

defineExpose({ show, success, error, warning, info })
</script>

<style scoped>
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 10000;
  max-width: 400px;
  animation: slideIn 0.3s ease-out;
}

.toast.success {
  background: #a6e3a1;
  color: #1e1e2e;
}

.toast.error {
  background: #f38ba8;
  color: #1e1e2e;
}

.toast.warning {
  background: #f9e2af;
  color: #1e1e2e;
}

.toast.info {
  background: #89b4fa;
  color: #1e1e2e;
}

.toast-icon {
  font-size: 1.2rem;
  font-weight: bold;
}

.toast-message {
  font-size: 0.95rem;
  line-height: 1.4;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
