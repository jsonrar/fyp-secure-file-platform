import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth_store'
import DashboardPage from '@/pages/DashboardPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'
import ForgotPasswordPage from '@/pages/ForgotPasswordPage.vue'
import UploadPage from '@/pages/UploadPage.vue'
import FileListPage from '@/pages/FileListPage.vue'
import AuditLogPage from '@/pages/AuditLogPage.vue'
import AdminPage from '@/pages/AdminPage.vue'
import CommunityPage from '@/pages/CommunityPage.vue'
import TeamPage from '@/pages/TeamPage.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0, left: 0 }
  },
  routes: [
    { path: '/', component: DashboardPage },
    { path: '/login', component: LoginPage, meta: { guestOnly: true } },
    { path: '/register', component: RegisterPage, meta: { guestOnly: true } },
    { path: '/forgot-password', component: ForgotPasswordPage, meta: { guestOnly: true } },
    { path: '/upload', component: UploadPage, meta: { requiresAuth: true } },
    { path: '/files', component: FileListPage, meta: { requiresAuth: true } },
    { path: '/audit-logs', component: AuditLogPage, meta: { requiresAuth: true } },
    { path: '/admin', component: AdminPage, meta: { requiresAuth: true } },
    { path: '/education', component: CommunityPage },
    { path: '/team', component: TeamPage },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthed) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthed) {
    return '/upload'
  }
})

export default router
