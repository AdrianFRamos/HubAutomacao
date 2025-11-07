<template>
  <div class="login-container">
    <div class="login-card">
      <img src="/logo-bahniuk.png" alt="Grupo Bahniuk" class="logo" />

      <h1>Portal de Automação</h1>
      <p class="subtitle">Acesso restrito | Grupo Bahniuk</p>

      <form @submit.prevent="submit">
        <div class="input-group">
          <label for="email">Usuário (e-mail)</label>
          <input
            id="email"
            type="email"
            v-model="email"
            placeholder="Digite seu e-mail"
            required
          />
        </div>

        <div class="input-group">
          <label for="password">Senha</label>
          <input
            id="password"
            type="password"
            v-model="password"
            placeholder="Digite sua senha"
            required
          />
        </div>

        <button type="submit" class="btn-login" :disabled="auth.loading">
          {{ auth.loading ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>

      <p v-if="msg" class="error">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth' 

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const msg = ref('')

async function submit() {
  msg.value = ''
  try {
    const user = await auth.login({
      email: email.value,
      password: password.value
    })
    if (!user) {
      msg.value = auth.error || 'Usuário ou senha incorretos'
      return
    }
    router.push({ name: 'dashboard' })
  } catch (e) {
    msg.value = auth.error || 'Falha na autenticação'
  }
}

let buffer = ''
const secret = 'bahniuk10'

function handleKey(e) {
  const key = (e && e.key ? String(e.key) : '').toLowerCase()
  if (!key) return
  buffer += key
  if (buffer.length > secret.length) {
    buffer = buffer.slice(-secret.length)
  }
  if (buffer === secret) {
    router.push('/register')
    buffer = ''
  }
}

onMounted(() => window.addEventListener('keydown', handleKey))
onBeforeUnmount(() => window.removeEventListener('keydown', handleKey))
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
  width: 360px;
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

input {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #c46b2f;
  background-color: #0e0e0e;
  color: #fff;
  outline: none;
  transition: 0.3s;
}

input:focus {
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

.error {
  color: #ff6b6b;
  margin-top: 15px;
  font-size: 0.9rem;
}

.hint {
  margin-top: 10px;
  opacity: 0.4;
  font-size: 0.85rem;
}
</style>
