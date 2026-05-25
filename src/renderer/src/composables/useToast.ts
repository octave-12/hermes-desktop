export interface ToastOptions {
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

// Global toast instance
let toastInstance: any = null

export function setToastInstance(instance: any) {
  toastInstance = instance
}

export function useToast() {
  function show(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', duration = 3000) {
    if (toastInstance) {
      toastInstance.show(message, type, duration)
    } else {
      console.warn('Toast instance not set')
    }
  }

  function success(message: string, duration?: number) {
    show(message, 'success', duration)
  }

  function error(message: string, duration?: number) {
    show(message, 'error', duration)
  }

  function warning(message: string, duration?: number) {
    show(message, 'warning', duration)
  }

  function info(message: string, duration?: number) {
    show(message, 'info', duration)
  }

  return {
    show,
    success,
    error,
    warning,
    info
  }
}
