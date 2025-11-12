<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal">
      <header class="modal-header">
        <h2>Adicionar Automação</h2>
        <button class="close-btn" @click="close">✕</button>
      </header>

      <form @submit.prevent="submit" class="modal-form">
        <!-- Nome da Automação -->
        <div class="form-group">
          <label for="name">Nome da Automação *</label>
          <input
            id="name"
            v-model="form.name"
            type="text"
            placeholder="Ex: Relatório Comercial"
            required
          />
        </div>

        <!-- Tipo de Automação -->
        <div class="form-group">
          <label for="automation_type">Tipo de Automação *</label>
          <select id="automation_type" v-model="form.automation_type" required>
            <option value="">Selecione o tipo...</option>
            <option value="dashboard">Dashboard</option>
            <option value="report">Relatório</option>
            <option value="integration">Integração</option>
            <option value="generic">Genérica</option>
          </select>
          <small>Tipo de automação determina os campos disponíveis</small>
        </div>

        <!-- Descrição -->
        <div class="form-group">
          <label for="description">Descrição</label>
          <textarea
            id="description"
            v-model="form.description"
            placeholder="Descreva o que esta automação faz"
            rows="3"
          ></textarea>
        </div>

        <!-- Campos específicos para Dashboard -->
        <div v-if="form.automation_type === 'dashboard'" class="dashboard-section">
          <h3 class="section-title">📊 Configuração do Dashboard</h3>

          <!-- Upload: Print do Dashboard -->
          <div class="form-group">
            <label for="dashboard_screenshot">Print do Dashboard Original *</label>
            <input
              type="file"
              id="dashboard_screenshot"
              @change="handleFileUpload($event, 'screenshot')"
              accept="image/*"
            />
            <small>Captura de tela do dashboard no sistema externo</small>
            <div v-if="uploadedScreenshot" class="file-preview">
              <img :src="`http://localhost:8000/${uploadedScreenshot.path}`" alt="Preview" />
              <span>✓ {{ uploadedScreenshot.filename }}</span>
            </div>
          </div>

          <!-- Upload: Imagem do Nome -->
          <div class="form-group">
            <label for="dashboard_name_image">Imagem do Nome do Dashboard *</label>
            <input
              type="file"
              id="dashboard_name_image"
              @change="handleFileUpload($event, 'name')"
              accept="image/*"
            />
            <small>Imagem com o nome do dashboard para reconhecimento</small>
            <div v-if="uploadedNameImage" class="file-preview">
              <img :src="`http://localhost:8000/${uploadedNameImage.path}`" alt="Preview" />
              <span>✓ {{ uploadedNameImage.filename }}</span>
            </div>
          </div>

          <!-- Periodicidades -->
          <div class="form-group">
            <label>Periodicidades Disponíveis *</label>
            <div class="checkbox-group">
              <label>
                <input type="checkbox" v-model="form.periodicities" value="diario" />
                Diário
              </label>
              <label>
                <input type="checkbox" v-model="form.periodicities" value="mensal" />
                Mensal
              </label>
              <label>
                <input type="checkbox" v-model="form.periodicities" value="anual" />
                Anual
              </label>
            </div>
          </div>
        </div>

        <!-- Campos técnicos -->
        <div class="form-group">
          <label for="module_path">Caminho do Módulo *</label>
          <input
            id="module_path"
            v-model="form.module_path"
            type="text"
            :placeholder="modulePlaceholder"
            required
          />
          <small>Caminho Python do módulo que contém a lógica de execução</small>
        </div>

        <div class="form-group">
          <label for="func_name">Função de Entrada *</label>
          <input
            id="func_name"
            v-model="form.func_name"
            type="text"
            placeholder="Ex: main"
            required
          />
          <small>Nome da função que será chamada para executar a automação</small>
        </div>

        <!-- Parâmetros (apenas se não for dashboard) -->
        <fieldset class="form-fieldset" v-if="form.automation_type !== 'dashboard'">
          <legend>Configuração de Parâmetros</legend>
          
          <div class="params-section">
            <h3>Parâmetros Padrão</h3>
            <div class="param-item" v-for="(value, key) in form.default_payload" :key="key">
              <label>{{ key }}</label>
              <input
                v-model="form.default_payload[key]"
                type="text"
                :placeholder="`Valor para ${key}`"
              />
              <button type="button" @click="removeParam(key)" class="btn-remove">Remover</button>
            </div>
            <button type="button" @click="addParam" class="btn-add-param">+ Adicionar Parâmetro</button>
          </div>
        </fieldset>

        <!-- Ações -->
        <div class="form-actions">
          <button type="button" @click="close" class="btn-cancel">Cancelar</button>
          <button type="submit" class="btn-submit" :disabled="loading">
            {{ loading ? 'Criando...' : 'Criar Automação' }}
          </button>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api, { uploadDashboardImage } from '@/api/client'

const props = defineProps({
  isOpen: Boolean,
})

const emit = defineEmits(['close', 'created'])

const form = ref({
  name: '',
  automation_type: '',
  description: '',
  module_path: '',
  func_name: 'main',
  default_payload: {},
  periodicities: []
})

const uploadedScreenshot = ref(null)
const uploadedNameImage = ref(null)
const loading = ref(false)
const error = ref(null)
const success = ref(null)

const modulePlaceholder = computed(() => {
  if (form.value.automation_type === 'dashboard') {
    return 'Ex: modules.comercial.dashboard.run_dashboard_v2'
  }
  return 'Ex: modules.setor.modulo.funcao'
})

// Auto-preencher module_path para dashboard
watch(() => form.value.automation_type, (newVal) => {
  if (newVal === 'dashboard') {
    form.value.module_path = 'modules.comercial.dashboard.run_dashboard_v2'
  }
})

async function handleFileUpload(event, type) {
  const file = event.target.files[0]
  if (!file) return

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await uploadDashboardImage(formData)

    if (type === 'screenshot') {
      uploadedScreenshot.value = response
    } else if (type === 'name') {
      uploadedNameImage.value = response
    }
  } catch (err) {
    error.value = `Erro ao fazer upload: ${err.message}`
  }
}

function close() {
  emit('close')
  resetForm()
}

function resetForm() {
  form.value = {
    name: '',
    automation_type: '',
    description: '',
    module_path: '',
    func_name: 'main',
    default_payload: {},
    periodicities: []
  }
  uploadedScreenshot.value = null
  uploadedNameImage.value = null
  error.value = null
  success.value = null
}

function addParam() {
  const key = prompt('Nome do parâmetro:')
  if (key && key.trim()) {
    form.value.default_payload[key.trim()] = ''
  }
}

function removeParam(key) {
  delete form.value.default_payload[key]
}

async function submit() {
  error.value = null
  success.value = null

  // Validações básicas
  if (!form.value.name.trim()) {
    error.value = 'Nome da automação é obrigatório'
    return
  }

  if (!form.value.automation_type) {
    error.value = 'Selecione o tipo de automação'
    return
  }

  if (!form.value.module_path.trim()) {
    error.value = 'Caminho do módulo é obrigatório'
    return
  }

  // Validações específicas para dashboard
  if (form.value.automation_type === 'dashboard') {
    if (!uploadedScreenshot.value || !uploadedNameImage.value) {
      error.value = 'É necessário fazer upload das duas imagens para automação de dashboard'
      return
    }
    if (form.value.periodicities.length === 0) {
      error.value = 'Selecione pelo menos uma periodicidade'
      return
    }
  }

  loading.value = true
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description || null,
      module_path: form.value.module_path,
      func_name: form.value.func_name,
      automation_type: form.value.automation_type,
      owner_type: 'user',
      default_payload: form.value.default_payload,
      config_schema: {},
    }

    // Adicionar campos específicos de dashboard
    if (form.value.automation_type === 'dashboard') {
      payload.dashboard_screenshot = uploadedScreenshot.value.path
      payload.dashboard_name_image = uploadedNameImage.value.path
      payload.config_schema = {
        type: 'object',
        properties: {
          periodicidade: {
            type: 'string',
            title: 'Periodicidade',
            enum: form.value.periodicities
          },
          dia: {
            type: 'integer',
            title: 'Dia',
            minimum: 1,
            maximum: 31,
            condition: 'periodicidade == "diario"'
          },
          mes: {
            type: 'integer',
            title: 'Mês',
            minimum: 1,
            maximum: 12,
            condition: 'periodicidade in ["diario", "mensal"]'
          },
          ano: {
            type: 'integer',
            title: 'Ano',
            minimum: 2020,
            maximum: 2030
          }
        }
      }
    }

    const result = await api.createAutomation(payload)
    success.value = `Automação "${result.name}" criada com sucesso!`
    
    setTimeout(() => {
      emit('created', result)
      close()
    }, 1500)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'Erro ao criar automação'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1b1b1b;
  border: 1px solid #c46b2f;
  border-radius: 12px;
  box-shadow: 0 0 30px rgba(242, 118, 46, 0.2);
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  color: #fff;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #c46b2f;
  background: rgba(242, 118, 46, 0.05);
}

.modal-header h2 {
  margin: 0;
  color: #f2762e;
  font-size: 1.3rem;
}

.close-btn {
  background: none;
  border: none;
  color: #f2762e;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.close-btn:hover {
  background: rgba(242, 118, 46, 0.1);
}

.modal-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #f2762e;
  font-weight: 600;
  font-size: 0.9rem;
}

.form-group input[type="text"],
.form-group input[type="file"],
.form-group textarea,
.form-group select {
  background: #0e0e0e;
  border: 1px solid #c46b2f;
  color: #fff;
  padding: 10px 12px;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9rem;
  transition: border-color 0.3s ease;
}

.form-group select {
  cursor: pointer;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #f2762e;
  box-shadow: 0 0 8px rgba(242, 118, 46, 0.3);
}

.form-group small {
  color: #aaa;
  font-size: 0.8rem;
}

.dashboard-section {
  background: #0e0e0e;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  margin: 0;
  color: #f2762e;
  font-size: 1rem;
  font-weight: 600;
}

.file-preview {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: rgba(242, 118, 46, 0.1);
  border-radius: 6px;
  border: 1px solid #c46b2f;
}

.file-preview img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #c46b2f;
}

.file-preview span {
  color: #42b883;
  font-size: 0.85rem;
  font-weight: 500;
}

.checkbox-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff !important;
  font-weight: normal !important;
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  width: auto;
  cursor: pointer;
  accent-color: #f2762e;
}

.form-fieldset {
  border: 1px solid #333;
  border-radius: 6px;
  padding: 16px;
  margin: 0;
}

.form-fieldset legend {
  color: #f2762e;
  font-weight: 600;
  padding: 0 8px;
}

.params-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.params-section h3 {
  margin: 0;
  color: #ddd;
  font-size: 0.95rem;
}

.param-item {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.param-item label {
  flex: 0 0 120px;
  color: #aaa !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
}

.param-item input {
  flex: 1;
  background: #0e0e0e;
  border: 1px solid #333;
  color: #fff;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.param-item input:focus {
  border-color: #f2762e;
  box-shadow: 0 0 6px rgba(242, 118, 46, 0.2);
}

.btn-remove {
  background: #ff6b6b;
  color: #fff;
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-remove:hover {
  background: #ff8787;
}

.btn-add-param {
  background: rgba(242, 118, 46, 0.2);
  color: #f2762e;
  border: 1px dashed #c46b2f;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-add-param:hover {
  background: rgba(242, 118, 46, 0.3);
  border-style: solid;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 12px;
}

.btn-cancel,
.btn-submit {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background: #333;
  color: #fff;
}

.btn-cancel:hover {
  background: #444;
}

.btn-submit {
  background: #f2762e;
  color: #fff;
}

.btn-submit:hover:not(:disabled) {
  background: #ff934f;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid #ff6b6b;
  color: #ff6b6b;
  padding: 12px;
  border-radius: 6px;
  font-size: 0.9rem;
}

.success-message {
  background: rgba(66, 184, 131, 0.1);
  border: 1px solid #42b883;
  color: #42b883;
  padding: 12px;
  border-radius: 6px;
  font-size: 0.9rem;
}
</style>
