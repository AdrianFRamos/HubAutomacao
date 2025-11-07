import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    profile: JSON.parse(localStorage.getItem('user') || 'null'),
    _unsubAuth: null,
  }),

  getters: {
    id: (s) => s.profile?.id ?? null,
    name: (s) => s.profile?.name ?? null,
    email: (s) => s.profile?.email ?? null,
    role: (s) => s.profile?.role ?? null,
    isAdmin: (s) => !!(s.profile?.is_admin) || s.profile?.role === 'admin',
    isManager: (s) => s.profile?.role === 'manager',
    isOperator: (s) => s.profile?.role === 'operator',
    isAuthenticated: (s) => !!s.profile,
  },

  actions: {
    setProfile(profile) {
      this.profile = profile ? { ...profile } : null
      if (this.profile) {
        localStorage.setItem('user', JSON.stringify(this.profile))
      } else {
        localStorage.removeItem('user')
      }
    },

    clear() {
      this.setProfile(null)
    },

    init() {
      const auth = useAuthStore()

      if (auth.user) {
        this.setProfile(auth.user)
      } else if (this.profile) {

      }

      if (this._unsubAuth) {
        try { this._unsubAuth() } catch {}
        this._unsubAuth = null
      }
      this._unsubAuth = auth.$subscribe((_mutation, state) => {
        this.setProfile(state.user || null)
      })
    },

    dispose() {
      if (this._unsubAuth) {
        try { this._unsubAuth() } catch {}
        this._unsubAuth = null
      }
    },
  },
})
