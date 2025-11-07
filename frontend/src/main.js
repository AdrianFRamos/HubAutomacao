import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/store/auth'
import { useUserStore } from '@/store/user'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

const auth = useAuthStore()
const user = useUserStore()

user.init()

const maybePromise = auth.hydrateFromSecureStorage?.()
if (maybePromise && typeof maybePromise.finally === 'function') {
  maybePromise.finally(() => app.mount('#app'))
} else {
  app.mount('#app')
}
