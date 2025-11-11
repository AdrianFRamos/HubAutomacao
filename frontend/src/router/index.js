import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/pages/Login.vue') },
  { path: '/register', name: 'register', component: () => import('@/pages/Register.vue') },
  { path: '/', name: 'dashboard', component: () => import('@/pages/Dashboard.vue'), meta: { requiresAuth: true } },
  { path: '/runs', name: 'runs', component: () => import('@/pages/RunsList.vue'), meta: { requiresAuth: true } },
  { path: '/dashboards', name: 'dashboards', component: () => import('@/pages/DashboardsPage.vue'), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }

  if (token && !auth.user) {
    auth.restoreFromLocal()
    auth.fetchMe().catch(() => {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      return { name: 'login' }
    })
  }
  return true
})

export default router
