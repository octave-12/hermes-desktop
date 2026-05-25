<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div v-if="visible" class="confirm-overlay" @click.self="cancel">
        <div class="confirm-dialog">
          <div class="confirm-header">
            <span class="confirm-icon">{{ icon }}</span>
            <h3 class="confirm-title">{{ title }}</h3>
          </div>
          <p class="confirm-message">{{ message }}</p>
          <div class="confirm-actions">
            <button class="btn btn-cancel" @click="cancel">
              {{ cancelText }}
            </button>
            <button class="btn btn-confirm" :class="type" @click="confirm">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const visible = ref(false)
const message = ref('')
const title = ref('确认')
const type = ref<'danger' | 'warning' | 'info'>('info')
const confirmText = ref('确定')
const cancelText = ref('取消')

const icon = computed(() => {
  const icons = {
    danger: '⚠',
    warning: '⚠',
    info: 'ℹ'
  }
  return icons[type.value]
})

let resolvePromise: ((value: boolean) => void) | null = null

function show(
  msg: string, 
  options?: {
    title?: string
    type?: 'danger' | 'warning' | 'info'
    confirmText?: string
    cancelText?: string
  }
): Promise<boolean> {
  message.value = msg
  title.value = options?.title || '确认'
  type.value = options?.type || 'info'
  confirmText.value = options?.confirmText || '确定'
  cancelText.value = options?.cancelText || '取消'
  visible.value = true
  
  return new Promise((resolve) => {
    resolvePromise = resolve
  })
}

function confirm() {
  visible.value = false
  if (resolvePromise) {
    resolvePromise(true)
    resolvePromise = null
  }
}

function cancel() {
  visible.value = false
  if (resolvePromise) {
    resolvePromise(false)
    resolvePromise = null
  }
}

defineExpose({ show, confirm, cancel })
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.confirm-dialog {
  background: #1e1e2e;
  border: 1px solid #45475a;
  border-radius: 12px;
  padding: 24px;
  min-width: 360px;
  max-width: 480px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.confirm-icon {
  font-size: 1.5rem;
}

.confirm-title {
  margin: 0;
  font-size: 1.1rem;
  color: #cdd6f4;
  font-weight: 600;
}

.confirm-message {
  margin: 0 0 24px;
  font-size: 0.95rem;
  color: #a6adc8;
  line-height: 1.6;
}

.confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-cancel {
  background: #45475a;
  color: #cdd6f4;
}

.btn-cancel:hover {
  background: #585b70;
}

.btn-confirm {
  background: #89b4fa;
  color: #1e1e2e;
}

.btn-confirm:hover {
  background: #74c7ec;
}

.btn-confirm.danger {
  background: #f38ba8;
  color: #1e1e2e;
}

.btn-confirm.danger:hover {
  background: #eba0ac;
}

.btn-confirm.warning {
  background: #f9e2af;
  color: #1e1e2e;
}

.btn-confirm.warning:hover {
  background: #f5c2e7;
}

/* Transition */
.confirm-enter-active,
.confirm-leave-active {
  transition: all 0.2s ease;
}

.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}

.confirm-enter-from .confirm-dialog,
.confirm-leave-to .confirm-dialog {
  transform: scale(0.95);
}
</style>
