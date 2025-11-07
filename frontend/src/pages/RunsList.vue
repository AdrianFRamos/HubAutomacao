<template>
  <div class="page">
    <h2>Execuções</h2>

    <div class="filters">
      <input v-model="automationId" placeholder="Filtrar por automation_id (opcional)" />
      <button @click="load">Buscar</button>
    </div>

    <table v-if="items.length">
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Automation</th>
          <th>Status</th>
          <th>Criado</th>
          <th>Início</th>
          <th>Fim</th>
          <th>ms</th>
          <th>Resultado</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in items" :key="r.id">
          <td>{{ r.id }}</td>
          <td>{{ r.automation?.name || r.automation_id }}</td>
          <td>{{ r.status }}</td>
          <td>{{ fmt(r.created_at) }}</td>
          <td>{{ fmt(r.started_at) }}</td>
          <td>{{ fmt(r.finished_at) }}</td>
          <td>{{ duration(r.started_at, r.finished_at) }}</td>
          <td>
            <details>
              <summary>ver</summary>
              <pre>{{ pretty(r.result) }}</pre>
            </details>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-else-if="!loading">Nenhum registro.</p>
    <p v-if="error" class="err">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/api/client'

const items = ref([])
const automationId = ref('')
const loading = ref(false)
const error = ref(null)

function fmt(v) { return v ? new Date(v).toLocaleString() : '-' }
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
    error.value = e?.response?.data?.detail || 'Falha ao carregar runs.'
  } finally {
    loading.value = false
  }
}

load()
</script>

<style scoped>
.page { padding: 16px; }
.filters { display: flex; gap: 8px; margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #333; padding: 8px; text-align: left; }
.err { color: #ff6b6b; }
pre { white-space: pre-wrap; word-break: break-word; }
</style>
