<template>
  <div class="dashboard">
    <header class="topbar">
      <div class="brand">
        <img src="/logo-bahniuk.png" alt="Grupo Bahniuk" />
        <h1>Portal de Automação</h1>
        <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
      </div>

      <div class="user">
        <span v-if="me">Olá, {{ me.name }} <small>({{ me.role }})</small></span>
        <button class="btn btn-add" @click="openAddModal" title="Adicionar nova automação">+ Adicionar Automação</button>
        <button class="btn" @click="logout">Sair</button>
      </div>
    </header>

    <main class="content">
      <div v-if="loading" class="state">Carregando…</div>
      <div v-else-if="errorMsg" class="state err">{{ errorMsg }}</div>

      <!-- ADMIN: mantém bloco de pessoais + agrupado legado + setores reais (sempre visíveis) -->
      <template v-else-if="isAdmin">
        <!-- pessoais -->
        <section v-if="personalAutomations.length" class="group">
          <h2>Automações pessoais</h2>
          <div class="grid">
            <AutomationCard
              v-for="a in personalAutomations"
              :key="a.id"
              :automation="a"
              :sector-id="resolveSectorId(a)"
              :sector-name="resolveSectorName(a)"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
        </section>

        <!-- agrupado legado por nome (se sua API retornar groups/setores nomeados) -->
        <section
          v-for="(automations, sectorName) in grouped"
          :key="'legacy-'+sectorName"
          class="group"
        >
          <h2>Setor (agrupado legado): {{ sectorName }}</h2>
          <div class="grid" v-if="automations && automations.length">
            <AutomationCard
              v-for="a in automations"
              :key="a.id"
              :automation="a"
              :sector-id="resolveSectorId(a)"
              :sector-name="sectorName"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
          <p v-else class="empty">Nenhuma automação para este setor.</p>
        </section>

        <!-- setores reais (lista completa mesmo vazios) -->
        <section v-for="sec in sectorsOrdered" :key="sec.id" class="group">
          <h2>Setor: {{ sec.name }}</h2>
          <div class="grid" v-if="(sectorAutomationsMap[sec.id] || []).length">
            <AutomationCard
              v-for="a in sectorAutomationsMap[sec.id]"
              :key="a.id"
              :automation="a"
              :sector-id="sec.id"
              :sector-name="sec.name"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
          <p v-else class="empty">Nenhuma automação para este setor.</p>
        </section>
      </template>

      <!-- MANAGER -->
      <template v-else-if="isManager">
        <section v-for="sec in sectorsOrdered" :key="sec.id" class="group">
          <h2>Setor: {{ sec.name }}</h2>
          <div class="grid" v-if="sectorAutomationsMap[sec.id]?.length">
            <AutomationCard
              v-for="a in sectorAutomationsMap[sec.id]"
              :key="a.id"
              :automation="a"
              :sector-id="sec.id"
              :sector-name="sec.name"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
          <p v-else class="empty">Nenhuma automação para este setor.</p>
        </section>
      </template>

      <!-- OPERATOR -->
      <template v-else>
        <section v-if="assignedAutomations.length" class="group">
          <h2>Minhas automações</h2>
          <div class="grid">
            <AutomationCard
              v-for="a in assignedAutomations"
              :key="a.id"
              :automation="a"
              :sector-id="resolveSectorId(a)"
              :sector-name="resolveSectorName(a)"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
        </section>

        <section v-for="sec in sectorsOrdered" :key="sec.id" class="group">
          <h2>Setor: {{ sec.name }}</h2>
          <div class="grid" v-if="sectorAutomationsMap[sec.id]?.length">
            <AutomationCard
              v-for="a in sectorAutomationsMap[sec.id]"
              :key="a.id"
              :automation="a"
              :sector-id="sec.id"
              :sector-name="sec.name"
              @scheduled="onScheduled"
              @ran="onRan"
            />
          </div>
          <p v-else class="empty">Nenhuma automação para este setor.</p>
        </section>
      </template>
    </main>

    <AddAutomationModal
      :is-open="showAddModal"
      @close="closeAddModal"
      @created="onAutomationCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import api from '@/api/client'
import AutomationCard from '@/components/AutomationCard.vue'
import AddAutomationModal from '@/components/AddAutomationModal.vue'

const router = useRouter()
const auth = useAuthStore()

const me = computed(() => auth.user)
const isAdmin = computed(() => auth.isAdmin)
const isManager = computed(() => auth.isManager)
const isOperator = computed(() => auth.isOperator)

const logout = () => { auth.logout(); router.push({ name: 'login' }) }

const loading = ref(false)
const errorMsg = ref(null)

const sectors = ref([])                 
const sectorsByName = computed(() => {
  const map = Object.create(null)
  for (const s of sectors.value) {
    map[String(s.name || '').toLowerCase()] = s
  }
  return map
})
const sectorsOrdered = computed(() =>
  [...sectors.value].sort((a, b) => a.name.localeCompare(b.name))
)

const automationsRaw = ref([])         
const groupedFromApi = ref(null)       

const sectorAutomationsMap = computed(() => {
  const byId = Object.create(null)
  for (const s of sectors.value) byId[s.id] = []
  for (const a of automationsRaw.value) {
    const sid = a.sector_id ||
      sectorsByName.value[String(a.sector || '').toLowerCase()]?.id ||
      null
    if (sid && byId[sid]) byId[sid].push(a)
  }
  return byId
})

const assignedAutomations = ref([])     
const personalAutomations = ref([])     

const grouped = computed(() => {
  if (groupedFromApi.value && typeof groupedFromApi.value === 'object') {
    return groupedFromApi.value
  }
  const by = {}
  for (const a of automationsRaw.value) {
    let setor =
      a.sector ||
      a.owner_type ||
      a.group ||
      (a.module_path ? (a.module_path.split('.')[0] || '').toLowerCase() : '') ||
      'Geral'
    if (!by[setor]) by[setor] = []
    by[setor].push(a)
  }
  return by
})

function resolveSectorId(a) {
  return a.sector_id ||
    sectorsByName.value[String(a.sector || '').toLowerCase()]?.id ||
    null
}

function resolveSectorName(a) {
  if (a.sector) return a.sector
  const sid = resolveSectorId(a)
  if (!sid) return '—'
  const s = sectors.value.find(x => x.id === sid)
  return s?.name || '—'
}

async function fetchAutomations() {
  const res = await api.getAutomations(true)
  let allAutomations = []
  if (Array.isArray(res)) {
    // Se o backend retorna um array de grupos (grouped=true)
    if (res.length > 0 && res[0].automations) {
      groupedFromApi.value = res
      for (const group of res) {
        if (Array.isArray(group.automations)) {
          allAutomations.push(...group.automations)
        }
      }
    } else {
      // Se o backend retorna um array simples de automações (grouped=false)
      automationsRaw.value = res
      allAutomations = res
    }
  } else if (Array.isArray(res?.items)) {
    automationsRaw.value = res.items
    allAutomations = res.items
  } else {
    // Trata outros formatos de retorno (incluindo o formato legado)
    if (res?.setores && typeof res.setores === 'object') {
      groupedFromApi.value = res.setores
    } else if (res?.groups && typeof res.groups === 'object') {
      groupedFromApi.value = res.groups
    } else if (Array.isArray(res?.data)) {
      automationsRaw.value = res.data
      allAutomations = res.data
    } else {
      groupedFromApi.value = res
    }
  }
  
  // Se groupedFromApi foi preenchido, precisamos extrair as automações para automationsRaw
  if (groupedFromApi.value && !Array.isArray(groupedFromApi.value)) {
    // Trata o formato de objeto { groupName: [automations] }
    for (const groupName in groupedFromApi.value) {
      if (Array.isArray(groupedFromApi.value[groupName])) {
        allAutomations.push(...groupedFromApi.value[groupName])
      }
    }
  }

  automationsRaw.value = allAutomations
  personalAutomations.value = (automationsRaw.value || []).filter(a => a.owner_type === 'user' && a.owner_id === me.value?.id)
  assignedAutomations.value = (automationsRaw.value || []).filter(a => Array.isArray(a.assignees) && a.assignees.includes?.(me.value?.id))
}

async function fetchAll() {
  loading.value = true
  errorMsg.value = null
  try {
    const [secs] = await Promise.all([
      api.listSectors(),        
    ])
    sectors.value = Array.isArray(secs) ? secs : (secs?.items || [])
    await fetchAutomations()
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.response?.data?.message || err?.message
    errorMsg.value = msg || 'Falha ao carregar dados.'
  } finally {
    loading.value = false
  }
}

function onScheduled() { }
function onRan() { }

const showAddModal = ref(false)

function openAddModal() {
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
}

async function onAutomationCreated(newAutomation) {
  // Recarregar a lista de automações
  await fetchAll()
}

onMounted(fetchAll)
</script>

<style scoped>
.dashboard {
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
.btn-add {
  background-color: #42b883;
}
.btn-add:hover {
  background-color: #52d896;
}

.content {
  padding: 24px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

.state {
  padding: 24px;
  border: 1px dashed #555;
  border-radius: 12px;
  text-align: center;
  color: #ddd;
}
.state.err { color: #ff6b6b; border-color: #ff6b6b; }

.group { margin-bottom: 28px; }
.group h2 {
  color: #f2762e;
  margin: 0 0 12px 4px;
  font-size: 1.1rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.empty {
  color: #aaa;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 14px;
  margin-left: 4px;
}
.err { color: #ff6b6b; }
</style>
