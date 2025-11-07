import { defineStore } from 'pinia'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    loadingProfile: false,
  }),

  getters: {
    isAuthenticated: (s) => !!s.token,
    role: (s) => s.user?.role || null,
    isAdmin: (s) => s.user?.role === 'admin' || s.user?.is_admin === true,
    isManager: (s) => s.user?.role === 'manager',
    isOperator: (s) => s.user?.role === 'operator',
  },

  actions: {
    restoreFromLocal() {
      this.token = localStorage.getItem('token') || null
      this.user = JSON.parse(localStorage.getItem('user') || 'null')
    },

    async login({ email, password }) {
      const payload = {
        email: String(email).trim().toLowerCase(),
        password: String(password)
      }

      const data = await api.login(payload.email, payload.password)

      if (data?.token) {
        this.token = data.token
        localStorage.setItem('token', data.token)
        await this.fetchMe()
        return this.user 
      } else {
        throw new Error('Credenciais inválidas.')
      }
    },

    async fetchMe() {
      this.loadingProfile = true
      try {
        const me = await api.me()
        this.user = me
        localStorage.setItem('user', JSON.stringify(me))
      } finally {
        this.loadingProfile = false
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
