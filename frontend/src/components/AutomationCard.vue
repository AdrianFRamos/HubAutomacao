<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ automation?.name || 'Automação' }}</h3>
      <small class="muted">{{ sectorName }}</small>
    </div>

    <small class="muted">ID: {{ automationId || '— sem ID —' }}</small>
    <p class="desc">{{ automation?.description || '—' }}</p>

    <div class="actions">
      <button class="btn-run" @click="run(false)" :disabled="loading">
        <span v-if="loading && action==='queue'">Enfileirando…</span>
        <span v-else>Executar</span>
      </button>
      <button class="btn-run outline" @click="run(true)" :disabled="loading">
        <span v-if="loading && action==='sync'">Rodando…</span>
        <span v-else>Executar agora</span>
      </button>
      <button class="btn-run ghost" @click="showSched=true" :disabled="loading">Agendar</button>
    </div>

    <p v-if="success" class="ok">{{ success }}</p>
    <pre v-if="error" class="err">{{ error }}</pre>

    <div v-if="showSched" class="modal" @click.self="showSched=false">
      <div class="modal-box">
        <h4>Agendar execução</h4>

        <label>Dia da semana</label>
        <select v-model="form.dow">
          <option v-for="d in days" :key="d.value" :value="d.value">{{ d.label }}</option>
        </select>

        <label>Horário</label>
        <input type="time" v-model="form.time" />

        <label>Prioridade</label>
        <input type="number" v-model.number="form.priority" min="1" max="10" />

        <div class="modal-actions">
          <button class="btn-run" @click="schedule" :disabled="saving">
            {{ saving ? 'Agendando…' : 'Salvar' }}
          </button>
          <button class="btn-run outline" @click="showSched=false" :disabled="saving">Cancelar</button>
        </div>

        <p v-if="schedOk" class="ok">{{ schedOk }}</p>
        <pre v-if="schedErr" class="err">{{ schedErr }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, ref, computed } from 'vue'
import api from '@/api/client'

const props = defineProps({
  automation: { type: Object, required: true },
  sectorId: { type: String, required: true },
  sectorName: { type: String, default: '' },
})

const emit = defineEmits(['scheduled', 'ran'])

const automationId = computed(() => props.automation?.id || props.automation?.automation_id || null)

const loading = ref(false)
const action = ref(null)
const success = ref(null)
const error = ref(null)

function resolvePayload() {
  return props.automation?.payload ?? props.automation?.default_payload ?? {}
}
function explainError(e) {
  const d = e?.response?.data?.detail ?? e?.message ?? e
  if (typeof d === 'string') return d
  try { return JSON.stringify(d, null, 2) } catch { return 'Falha.' }
}

async function run(sync = false) {
  console.log('[CARD] run called', { sync, automation: props.automation })
  success.value = null; error.value = null
  const id = automationId.value
  if (!id) { error.value = 'Automação sem ID. Confira o retorno de /automations.'; return }

  loading.value = true; action.value = sync ? 'sync' : 'queue'
  try {
    const payload = resolvePayload()
    const mode = sync ? 'sync' : 'async'
    const logPrefix = sync ? '[RUN SYNC]' : '[RUN ASYNC]'
    console.log(`${logPrefix} POST /runs`, { automation_id: id, payload, mode })
    
    const run = await api.createRun({ automation_id: id, payload, mode })
    
    if (sync) {
      // Retorno síncrono é um objeto com run_id e ok: true/false
      if (run.ok) {
        success.value = `Execução concluída (run_id=${run.run_id}).`
      } else {
        error.value = `Execução falhou (run_id=${run.run_id}). Detalhes: ${explainError(run)}`
      }
    } else {
      // Retorno assíncrono é o objeto Run criado
      success.value = `Execução enfileirada (run_id=${run.id}).`
    }
    emit('ran')
  } catch (e) {
    error.value = explainError(e)
    console.error('[RUN ERROR]', e)
  } finally {
    loading.value = false; action.value = null
  }
}

const showSched = ref(false)
const saving = ref(false)
const schedOk = ref(null)
const schedErr = ref(null)

const days = [
  { value: 1, label: 'Segunda' },
  { value: 2, label: 'Terça' },
  { value: 3, label: 'Quarta' },
  { value: 4, label: 'Quinta' },
  { value: 5, label: 'Sexta' },
  { value: 6, label: 'Sábado' },
  { value: 0, label: 'Domingo' },
]
const form = ref({ dow: 1, time: '07:30', priority: 5 })

function toCron(timeStr, dow) {
  const [hh, mm] = String(timeStr || '00:00').split(':').map(n => parseInt(n || '0', 10))
  return `${isNaN(mm)?0:mm} ${isNaN(hh)?0:hh} * * ${dow}`
}

async function schedule() {
  schedOk.value = null; schedErr.value = null; saving.value = true
  const id = automationId.value
  if (!id) { schedErr.value = 'Automação sem ID'; saving.value=false; return }

  const body = {
    automation_id: id,
    name: `${props.automation.name} - ${props.sectorName}`,
    enabled: true,
    owner_type: 'sector',
    owner_id: props.sectorId,
    type: 'cron',
    cron: toCron(form.value.time, form.value.dow),
    timezone: 'America/Sao_Paulo',
    payload: { ...(resolvePayload()), __priority: form.value.priority },
  }
  try {
    console.log('[SCHEDULE] POST /schedules', body)
    const res = await api.createSchedule(body)
    schedOk.value = 'Agendado com sucesso.'
    emit('scheduled', res)
  } catch (e) {
    schedErr.value = explainError(e)
    console.error('[SCHEDULE ERROR]', e)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.card, .actions, .btn-run { pointer-events:auto; }
.card{ background:rgba(20,20,20,.95); border:1px solid #c46b2f; border-radius:10px; padding:20px; display:flex; flex-direction:column; gap:10px; box-shadow:0 0 10px rgba(242,118,46,.1); }
.card:hover{ transform:translateY(-4px); box-shadow:0 0 15px rgba(242,118,46,.3); }
.card-header{ display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
.card-header h3{ color:#f2762e; margin:0; font-size:1.1rem; }
.muted{ color:#aaa; }
.desc{ color:#ccc; margin:0; font-size:.95rem; }
.actions{ display:flex; gap:8px; flex-wrap:wrap; }
.btn-run{ background:#f2762e; color:#fff; border:none; padding:10px; border-radius:6px; cursor:pointer; }
.btn-run:hover{ background:#ff934f; transform:scale(1.05); }
.btn-run.outline{ background:transparent; border:1px solid #f2762e; color:#f2762e; }
.btn-run.outline:hover{ background:#f2762e22; }
.btn-run.ghost{ background:transparent; border:1px dashed #f2762e; color:#f2762e; }
.ok{ color:#42b883; white-space:pre-wrap; }
.err{ color:#ff6b6b; white-space:pre-wrap; }

.modal{ position:fixed; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; padding:16px; z-index:50; }
.modal-box{ width:100%; max-width:420px; background:#141414; border:1px solid #c46b2f; border-radius:12px; padding:16px; display:flex; flex-direction:column; gap:8px; }
.modal-box h4{ color:#f2762e; margin:0 0 6px; }
.modal-box label{ font-size:.9rem; color:#ddd; }
.modal-box input, .modal-box select{ background:#0e0e0e; border:1px solid #c46b2f; color:#fff; border-radius:6px; padding:8px; }
.modal-actions{ display:flex; gap:8px; margin-top:8px; }
</style>
