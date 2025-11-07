<template>
  <div class="login-container">
    <div class="login-card">
      <img src="/logo-bahniuk.png" alt="Grupo Bahniuk" class="logo" />

      <h1>Registrar novo usuário</h1>
      <p class="subtitle">Somente administradores têm acesso a esta tela.</p>

      <form @submit.prevent="registerUser">
        <div class="input-group">
          <label for="name">Nome completo</label>
          <input
            id="name"
            type="text"
            v-model="form.name"
            placeholder="Nome"
            required
          />
        </div>

        <div class="input-group">
          <label for="email">E-mail</label>
          <input
            id="email"
            type="email"
            v-model="form.email"
            placeholder="usuario@email.com"
            required
          />
        </div>

        <div class="input-group">
          <label for="password">Senha</label>
          <input
            id="password"
            type="password"
            v-model="form.password"
            placeholder="********"
            required
          />
        </div>

        <div class="input-group">
          <label for="role">Função do usuário</label>
          <select id="role" v-model="form.role" required>
            <option disabled value="">Selecione...</option>
            <option value="operator">Operator</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? 'Cadastrando...' : 'Cadastrar' }}
        </button>
      </form>

      <p v-if="message" class="message" :class="{ error: isError }">{{ message }}</p>

      <p class="link" @click="goBack">Voltar ao painel</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

const router = useRouter()
const loading = ref(false)
const message = ref('')
const isError = ref(false)

const form = ref({
  name: '',
  email: '',
  password: '',
  role: ''
})

async function registerUser () {
  loading.value = true
  message.value = ''
  isError.value = false

  try {
    const payload = {
      name: form.value.name?.trim(),
      email: form.value.email?.trim(),
      password: form.value.password,
      role: (form.value.role || 'operator').toLowerCase(), 
      sectorId: form.value.sectorId ?? null,
    }

    const res = await api.register(payload)

    message.value = 'Cadastro realizado com sucesso!'
    isError.value = false
    setTimeout(() => router.push('/login'), 1200)
  } catch (err) {
    console.error(err)
    message.value = err?.response?.data?.detail || 'Erro ao cadastrar. Tente novamente.'
    isError.value = true
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/')
}
</script>

<style scoped>
.login-container {
  background: radial-gradient(circle at top, #1b1b1b 0%, #000 100%);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-image: url('/textures/metal-texture-dark.jpg');
  background-size: cover;
  background-position: center;
}

.login-card {
  background-color: rgba(15, 15, 15, 0.92);
  border: 1px solid #c46b2f;
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(255, 102, 0, 0.15);
  padding: 40px;
  width: 420px;
  text-align: center;
  color: #fff;
}

.logo {
  width: 140px;
  margin-bottom: 20px;
}

h1 {
  color: #f2762e;
  font-size: 1.6rem;
  margin-bottom: 6px;
  letter-spacing: 1px;
}

.subtitle {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 30px;
}

.input-group {
  margin-bottom: 18px;
  text-align: left;
}

label {
  font-size: 0.9rem;
  color: #f1f1f1;
  margin-bottom: 6px;
  display: block;
}

input, select {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #c46b2f;
  background-color: #0e0e0e;
  color: #fff;
  outline: none;
  transition: 0.3s;
}

input:focus, select:focus {
  border-color: #f2762e;
  box-shadow: 0 0 8px rgba(242, 118, 46, 0.4);
}

.btn-login {
  width: 100%;
  padding: 12px;
  background-color: #f2762e;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  cursor: pointer;
  transition: background-color 0.3s ease, transform 0.2s ease;
}

.btn-login:hover {
  background-color: #ff934f;
  transform: scale(1.03);
}

.message {
  margin-top: 12px;
}
.message.error { color: #ff6b6b; }

.link {
  margin-top: 14px;
  color: #ff934f;
  cursor: pointer;
}
.link:hover { text-decoration: underline; }
</style>
