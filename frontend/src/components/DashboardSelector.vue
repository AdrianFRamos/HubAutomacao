<template>
  <div class="dashboard-selector">
    <div class="form-group">
      <label for="dashboard">Dashboard *</label>
      <select 
        id="dashboard" 
        v-model="selectedDashboard" 
        @change="onDashboardChange"
        :disabled="loading"
        required
      >
        <option value="">Selecione um dashboard...</option>
        <option 
          v-for="dashboard in activeDashboards" 
          :key="dashboard.id" 
          :value="dashboard.name"
        >
          {{ dashboard.display_name }}
        </option>
      </select>
    </div>

    <div v-if="currentDashboard" class="dashboard-config">
      <div class="form-group">
        <label for="periodicidade">Periodicidade *</label>
        <select 
          id="periodicidade" 
          v-model="form.periodicidade" 
          @change="onPeriodChange"
          required
        >
          <option value="">Selecione...</option>
          <option 
            v-for="period in currentDashboard.available_periodicities" 
            :key="period" 
            :value="period"
          >
            {{ periodLabels[period] }}
          </option>
        </select>
      </div>

      <div v-if="form.periodicidade === 'diario'" class="form-group">
        <label for="dia">Dia *</label>
        <input 
          type="number" 
          id="dia" 
          v-model.number="form.dia" 
          min="1" 
          max="31" 
          required 
        />
      </div>

      <div v-if="form.periodicidade === 'mensal' || form.periodicidade === 'diario'" class="form-group">
        <label for="mes">Mês *</label>
        <select id="mes" v-model.number="form.mes" required>
          <option value="">Selecione...</option>
          <option v-for="m in 12" :key="m" :value="m">{{ monthNames[m-1] }}</option>
        </select>
      </div>

      <div class="form-group">
        <label for="ano">Ano *</label>
        <input 
          type="number" 
          id="ano" 
          v-model.number="form.ano" 
          min="2020" 
          :max="currentYear + 1" 
          required 
        />
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" v-model="form.enviar_whatsapp" />
          Enviar via WhatsApp
        </label>
      </div>

      <div v-if="form.enviar_whatsapp" class="form-group">
        <label for="numeros">Números WhatsApp (separados por vírgula)</label>
        <input 
          type="text" 
          id="numeros" 
          v-model="numerosStr" 
          placeholder="+5542998726282, +5542999999999"
        />
      </div>

      <div v-if="form.enviar_whatsapp" class="form-group">
        <label for="mensagem">Mensagem</label>
        <textarea 
          id="mensagem" 
          v-model="form.mensagem" 
          rows="3"
          placeholder="Relatório gerado automaticamente..."
        ></textarea>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api/client'

export default {
  name: 'DashboardSelector',
  emits: ['update:payload'],
  setup(props, { emit }) {
    const dashboards = ref([])
    const loading = ref(false)
    const selectedDashboard = ref('')
    
    const form = ref({
      dashboard_name: '',
      periodicidade: '',
      dia: null,
      mes: null,
      ano: new Date().getFullYear(),
      enviar_whatsapp: false,
      numeros_whatsapp: [],
      mensagem: ''
    })

    const numerosStr = ref('')

    const periodLabels = {
      diario: 'Diário',
      mensal: 'Mensal',
      anual: 'Anual'
    }

    const monthNames = [
      'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]

    const currentYear = new Date().getFullYear()

    const activeDashboards = computed(() => 
      dashboards.value.filter(d => d.is_active)
    )

    const currentDashboard = computed(() => 
      dashboards.value.find(d => d.name === selectedDashboard.value)
    )

    const loadDashboards = async () => {
      loading.value = true
      try {
        dashboards.value = await api.listDashboards({ is_active: true })
      } catch (err) {
        console.error('Erro ao carregar dashboards:', err)
      } finally {
        loading.value = false
      }
    }

    const onDashboardChange = () => {
      form.value.dashboard_name = selectedDashboard.value
      form.value.periodicidade = ''
      form.value.dia = null
      form.value.mes = null
      emitPayload()
    }

    const onPeriodChange = () => {
      if (form.value.periodicidade !== 'diario') {
        form.value.dia = null
      }
      if (form.value.periodicidade === 'anual') {
        form.value.mes = null
      }
      emitPayload()
    }

    const emitPayload = () => {
      const payload = { ...form.value }
      
      // Parse números WhatsApp
      if (numerosStr.value) {
        payload.numeros_whatsapp = numerosStr.value
          .split(',')
          .map(n => n.trim())
          .filter(Boolean)
      }

      // Remove campos nulos
      Object.keys(payload).forEach(key => {
        if (payload[key] === null || payload[key] === '') {
          delete payload[key]
        }
      })

      emit('update:payload', payload)
    }

    // Watch para emitir mudanças
    watch(form, emitPayload, { deep: true })
    watch(numerosStr, emitPayload)

    onMounted(() => {
      loadDashboards()
    })

    return {
      dashboards,
      loading,
      selectedDashboard,
      form,
      numerosStr,
      periodLabels,
      monthNames,
      currentYear,
      activeDashboards,
      currentDashboard,
      onDashboardChange,
      onPeriodChange
    }
  }
}
</script>

<style scoped>
.dashboard-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: rgba(242, 118, 46, 0.05);
  border: 1px solid #c46b2f;
  border-radius: 6px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  color: #f2762e;
  font-weight: 600;
  font-size: 0.9rem;
}

.form-group select,
.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea {
  background: #0e0e0e;
  border: 1px solid #c46b2f;
  color: #fff;
  padding: 10px 12px;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
}

.form-group select:focus,
.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #f2762e;
  box-shadow: 0 0 8px rgba(242, 118, 46, 0.3);
}

.form-group.checkbox label {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.form-group.checkbox input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}
</style>
