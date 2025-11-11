<template>
  <div class="dashboards-manager">
    <div class="header">
      <h2>Gerenciar Dashboards</h2>
      <button class="btn-primary" @click="showAddModal = true" v-if="isAdmin">
        + Adicionar Dashboard
      </button>
    </div>

    <div v-if="loading" class="loading">Carregando dashboards...</div>

    <div v-else-if="error" class="error-box">
      <p>Erro ao carregar dashboards:</p>
      <pre>{{ error }}</pre>
    </div>

    <div v-else class="dashboards-list">
      <div v-if="dashboards.length === 0" class="empty">
        <p>Nenhum dashboard configurado.</p>
        <p v-if="isAdmin">Clique em "Adicionar Dashboard" para começar.</p>
      </div>

      <div v-for="dashboard in dashboards" :key="dashboard.id" class="dashboard-card">
        <div class="dashboard-header">
          <h3>{{ dashboard.display_name }}</h3>
          <span :class="['status', dashboard.is_active ? 'active' : 'inactive']">
            {{ dashboard.is_active ? 'Ativo' : 'Inativo' }}
          </span>
        </div>

        <p class="dashboard-name">Nome: <code>{{ dashboard.name }}</code></p>
        <p class="dashboard-desc">{{ dashboard.description || 'Sem descrição' }}</p>

        <div class="dashboard-details">
          <div class="detail">
            <strong>Menu:</strong>
            <span>{{ dashboard.menu_path.join(' → ') }}</span>
          </div>
          <div class="detail">
            <strong>Região Screenshot:</strong>
            <span>[{{ dashboard.screenshot_region.join(', ') }}]</span>
          </div>
          <div class="detail">
            <strong>Periodicidades:</strong>
            <span>{{ dashboard.available_periodicities.join(', ') || 'Nenhuma' }}</span>
          </div>
        </div>

        <div class="dashboard-actions" v-if="isAdmin">
          <button class="btn-edit" @click="editDashboard(dashboard)">Editar</button>
          <button class="btn-delete" @click="confirmDelete(dashboard)">Excluir</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import api from '../api/client'

export default {
  name: 'DashboardsManager',
  props: {
    userRole: {
      type: String,
      default: 'operator'
    }
  },
  setup(props) {
    const dashboards = ref([])
    const loading = ref(false)
    const error = ref(null)
    const showAddModal = ref(false)
    const isAdmin = computed(() => props.userRole === 'admin')

    const loadDashboards = async () => {
      loading.value = true
      error.value = null
      try {
        dashboards.value = await api.listDashboards()
      } catch (err) {
        error.value = err.response?.data?.detail || err.message || 'Erro desconhecido'
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      loadDashboards()
    })

    return {
      dashboards,
      loading,
      error,
      showAddModal,
      isAdmin,
      loadDashboards
    }
  }
}
</script>

<style scoped>
.dashboards-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #666;
}

.error-box {
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  padding: 15px;
  color: #c33;
}

.dashboards-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.dashboard-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.btn-primary {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
