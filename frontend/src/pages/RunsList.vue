<template>
  <div class="runs-page">
    <header class="topbar">
      <div class="brand">
        <img src="/logo-bahniuk.png" alt="Grupo Bahniuk" />
        <h1>Histórico de Execuções</h1>
      </div>
      <div class="user">
        <button class="btn" @click="$router.push({ name: 'dashboard' })">Voltar</button>
      </div>
    </header>

    <main class="content">
      <div class="filters">
        <input v-model="automationId" placeholder="Filtrar por automation_id (opcional)" class="filter-input" />
        <button @click="load" class="btn-search">Buscar</button>
      </div>

      <div v-if="loading" class="state">Carregando…</div>
      <div v-else-if="error" class="state err">{{ error }}</div>
      <div v-else-if="!items.length" class="state">Nenhum registro encontrado.</div>

      <table v-else class="runs-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Automação</th>
            <th class="status-col">Status</th>
            <th>Criado</th>
            <th>Duração (ms)</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in items" :key="r.id" :class="`status-${r.status}`">
            <td class="run-id">{{ r.id?.substring(0, 8) }}…</td>
            <td class="automation-name">{{ r.automation?.name || r.automation_id }}</td>
            <td class="status-col"><span class="status-badge" :class="r.status">{{ r.status }}</span></td>
            <td class="date">{{ fmt(r.created_at) }}</td>
            <td class="duration">{{ duration(r.started_at, r.finished_at) }}</td>
            <td class="result">
              <details>
                <summary>Detalhes</summary>
                <pre>{{ pretty(r.result) }}</pre>
              </details>
            </td>
          </tr>
        </tbody>
      </table>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

const router = useRouter()
const items = ref([])
const automationId = ref('')
const loading = ref(false)
const error = ref(null)

function fmt(v) { return v ? new Date(v).toLocaleString('pt-BR') : '-' }
function duration(a, b) {
  if (!a || !b) return '-'
  return new Date(b).getTime() - new Date(a).getTime()
}
function pretty(o) {
  try { return JSON.stringify(o, null, 2) } catch { return String(o) }
}

async function load() {
  loading.value = true
  error.value = null
  try {
    items.value = await api.listRuns({ automation_id: automationId.value || undefined })
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Falha ao carregar execuções.'
  } finally {
    loading.value = false
  }
}

load()
</script>

<style scoped>
.runs-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at top, #1b1b1b 0%, #000 100%);
  color: #fff;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #c46b2f;
  background: rgba(15,15,15,0.92);
  box-shadow: 0 0 16px rgba(255,102,0,0.12);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand img { width: 40px; height: 40px; }
.brand h1 { font-size: 1.2rem; color: #f2762e; margin: 0; }

.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn {
  background-color: #f2762e;
  color: #fff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}
.btn:hover { background-color: #ff934f; }

.content {
  padding: 24px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.filter-input {
  flex: 1;
  max-width: 400px;
  background: #0e0e0e;
  border: 1px solid #c46b2f;
  color: #fff;
  border-radius: 6px;
  padding: 10px;
  outline: none;
  transition: border-color 0.3s ease;
}

.filter-input:focus {
  border-color: #f2762e;
  box-shadow: 0 0 8px rgba(242, 118, 46, 0.3);
}

.btn-search {
  background-color: #f2762e;
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-search:hover {
  background-color: #ff934f;
}

.state {
  padding: 24px;
  border: 1px dashed #555;
  border-radius: 12px;
  text-align: center;
  color: #ddd;
}
.state.err { color: #ff6b6b; border-color: #ff6b6b; }

.runs-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(20,20,20,0.95);
  border: 1px solid #c46b2f;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 0 10px rgba(242,118,46,0.1);
}

.runs-table thead {
  background: rgba(242, 118, 46, 0.1);
  border-bottom: 2px solid #c46b2f;
}

.runs-table th {
  color: #f2762e;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 0.9rem;
}

.runs-table td {
  padding: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  color: #ccc;
  font-size: 0.9rem;
}

.runs-table tbody tr:hover {
  background: rgba(242, 118, 46, 0.05);
}

.run-id {
  font-family: monospace;
  color: #aaa;
  font-size: 0.85rem;
}

.automation-name {
  color: #f2762e;
  font-weight: 500;
}

.status-col {
  text-align: center;
  width: 100px;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.success {
  background: rgba(66, 184, 131, 0.2);
  color: #42b883;
  border: 1px solid #42b883;
}

.status-badge.failed {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  border: 1px solid #ff6b6b;
}

.status-badge.running {
  background: rgba(242, 118, 46, 0.2);
  color: #f2762e;
  border: 1px solid #f2762e;
}

.status-badge.queued {
  background: rgba(100, 150, 200, 0.2);
  color: #6496c8;
  border: 1px solid #6496c8;
}

.date {
  color: #aaa;
  font-size: 0.85rem;
}

.duration {
  text-align: right;
  color: #aaa;
  font-size: 0.85rem;
}

.result details {
  cursor: pointer;
}

.result summary {
  color: #f2762e;
  text-decoration: underline;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.result summary:hover {
  background: rgba(242, 118, 46, 0.1);
}

.result pre {
  background: #0e0e0e;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 12px;
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.8rem;
  color: #aaa;
  max-height: 300px;
  overflow-y: auto;
}
</style>
