// Global confirm instance
let confirmInstance: any = null

export function setConfirmInstance(instance: any) {
  confirmInstance = instance
}

export function useConfirm() {
  async function show(
    message: string,
    options?: {
      title?: string
      type?: 'danger' | 'warning' | 'info'
      confirmText?: string
      cancelText?: string
    }
  ): Promise<boolean> {
    if (confirmInstance) {
      return await confirmInstance.show(message, options)
    } else {
      console.warn('Confirm instance not set')
      return false
    }
  }

  async function danger(
    message: string,
    title?: string
  ): Promise<boolean> {
    return await show(message, { title, type: 'danger' })
  }

  async function warning(
    message: string,
    title?: string
  ): Promise<boolean> {
    return await show(message, { title, type: 'warning' })
  }

  async function info(
    message: string,
    title?: string
  ): Promise<boolean> {
    return await show(message, { title, type: 'info' })
  }

  return {
    show,
    danger,
    warning,
    info
  }
}
