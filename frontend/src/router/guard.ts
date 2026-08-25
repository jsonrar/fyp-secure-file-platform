import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth_store'

/**
 * Where a signed-in user lands when they have not asked for anywhere in particular.
 *
 * This used to be `/upload`, which assumed every visit begins with an upload. It does not:
 * someone signing in to share or download a file they uploaded last week was dropped on
 * the encryption form with no way through to the rest of the app.
 */
export const HOME_AFTER_LOGIN = '/dashboard'

/** Where an unauthenticated visitor is sent, carrying the page they were reaching for. */
export const LOGIN_PATH = '/login'

/**
 * Split out of the router so it can be exercised without a DOM: `createWebHistory()` runs
 * at import time in `./index.ts`, and the test environment here is node.
 */
export function authGuard(to: RouteLocationNormalized): RouteLocationRaw | undefined {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthed) {
    return { path: LOGIN_PATH, query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthed) {
    return HOME_AFTER_LOGIN
  }
  return undefined
}
