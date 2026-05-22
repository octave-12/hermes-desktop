import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import { initAuth } from './utils/api'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Initialize authentication before mounting
initAuth().then(() => {
  app.mount('#app')
}).catch((error) => {
  console.error('[Main] Failed to initialize auth:', error)
  app.mount('#app') // Mount anyway
})
