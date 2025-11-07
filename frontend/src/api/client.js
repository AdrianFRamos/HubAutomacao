import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const http = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
})

http.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  r => r,
  err => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    return Promise.reject(err)
  }
)

const api = {
  // ---------- AUTH ----------
  async login(email, password) {
    const { data } = await http.post('/auth/login', {
      email: String(email).trim().toLowerCase(),
      password: String(password),
    })
    // Backend retorna { access_token, token_type }
    const token = data?.access_token || data?.token
    if (!token) throw new Error('Token não recebido')
    // Devolve no formato que o teu store usa (data.token)
    return { token, token_type: data?.token_type || 'bearer' }
  },

  async me() {
    const { data } = await http.get('/auth/me')
    return data 
  },
  async register({ name, email, password, role }) {
    const { data } = await http.post('/auth/register', { name, email, password, role })
    return data
  },

  // ---------- AUTOMATIONS ----------
  async listAutomations({ grouped } = {}) {
    const { data } = await http.get('/automations', { params: { grouped } })
    return data
  },
  async createAutomation(body) {
    const { data } = await http.post('/automations', body)
    return data
  },
  async getAutomations(grouped = false) {
    const qs = grouped ? '?grouped=true' : ''
    const res = await http.get(`/automations${qs}`)
    return res.data
  },

  // ---------- RUNS ----------
  async createRun({ automation_id, payload }) {
    const { data } = await http.post('/runs', { automation_id, payload })
    return data 
  },
  async listRuns({ automation_id } = {}) {
    const { data } = await http.get('/runs', { params: { automation_id } })
    return data
  },
  async runSync({ automation_id, payload }) {
    const { data } = await http.post('/runs/sync', { automation_id, payload })
    return data
  },

  // ---------- SCHEDULES ----------
  async listSchedules({ automation_id } = {}) {
    const { data } = await http.get('/schedules', { params: { automation_id } })
    return data
  },
  async createSchedule(body) {
    const { data } = await http.post('/schedules', body)
    return data
  },
  async patchSchedule(id, body) {
    const { data } = await http.patch(`/schedules/${id}`, body)
    return data
  },
  async deleteSchedule(id) {
    await http.delete(`/schedules/${id}`)
    return true
  },

  // ---------- SECRETS ----------
  async upsertSecret(body) {
    const { data } = await http.post('/secrets', body)
    return data
  },
  async listSecrets(owner_type, owner_id) {
    const { data } = await http.get('/secrets', { params: { owner_type, owner_id } })
    return data
  },
  async readSecret(secret_id) {
    const { data } = await http.get(`/secrets/${secret_id}`)
    return data
  },
  async deleteSecret(secret_id) {
    await http.delete(`/secrets/${secret_id}`)
    return true
  },
  async listSectors() {
    const { data } = await http.get('/sectors/')
    return data
  },
}

export default api
