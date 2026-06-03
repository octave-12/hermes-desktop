import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import { initAuth } from './utils/api'
import { preloadHorseGif } from './utils/imagePreload'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Initialize authentication and preload images before mounting
Promise.all([
  initAuth(),
  preloadHorseGif()
]).then(() => {
  app.mount('#app')
}).catch((error) => {
  console.error('[Main] Initialization failed:', error)
  app.mount('#app') // Mount anyway
})
