import { createRouter, createWebHistory } from 'vue-router'
import { authGuard } from './guard'
import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, top: 96, behavior: 'smooth' }
    }
    return { top: 0, left: 0 }
  },
  routes,
})

router.beforeEach(authGuard)

export default router
