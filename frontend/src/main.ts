import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setSessionExpiredHandler } from './api/session'
import { LOGIN_PATH } from './router/guard'
import { useAuthStore } from './stores/auth_store'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

/**
 * End a session that could not be renewed, visibly.
 *
 * Without this the store still reports `isAuthed` after the tokens are gone, so the app
 * keeps rendering a signed-in shell in which every request fails -- which is exactly the
 * confusing state this was reported from: an authorization error on a button press, no
 * explanation, and no hint that signing in again is the fix.
 */
setSessionExpiredHandler(() => {
  const auth = useAuthStore()
  if (!auth.isAuthed) return
  // Tokens are already unusable; do not call `POST /auth/logout` with a dead bearer.
  auth.clearLocalSession()

  const current = router.currentRoute.value
  // Only worth coming back to a page the user needed to be signed in for.
  const redirect = current.meta.requiresAuth ? current.fullPath : undefined
  router.push({ path: LOGIN_PATH, query: { expired: '1', ...(redirect ? { redirect } : {}) } })
})

app.mount('#app')
