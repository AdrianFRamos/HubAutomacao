<template>
  <div class="dashboards-page">
    <DashboardsManager :userRole="userRole" />
  </div>
</template>

<script>
import { computed } from 'vue'
import { useAuthStore } from '../store/auth'
import DashboardsManager from '../components/DashboardsManager.vue'

export default {
  name: 'DashboardsPage',
  components: {
    DashboardsManager
  },
  setup() {
    const authStore = useAuthStore()
    const userRole = computed(() => authStore.user?.role || 'operator')

    return {
      userRole
    }
  }
}
</script>

<style scoped>
.dashboards-page {
  min-height: 100vh;
  background: #0e0e0e;
  padding: 20px;
}
</style>
