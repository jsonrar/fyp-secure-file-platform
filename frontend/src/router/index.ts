import { createRouter, createWebHistory } from 'vue-router'
import DashboardPage from '../pages/DashboardPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import RegisterPage from '../pages/RegisterPage.vue'
import UploadPage from '../pages/UploadPage.vue'
import FileListPage from '../pages/FileListPage.vue'
import AuditLogPage from '../pages/AuditLogPage.vue'
import AdminPage from '../pages/AdminPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardPage },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/upload', component: UploadPage },
    { path: '/files', component: FileListPage },
    { path: '/audit-logs', component: AuditLogPage },
    { path: '/admin', component: AdminPage },
  ],
})

export default router
