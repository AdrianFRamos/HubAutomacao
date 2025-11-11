-- ============================================================================
-- SCRIPT SQL COMPLETO - PORTAL DE AUTOMAÇÃO V2
-- ============================================================================
-- Descrição: Cria banco de dados do zero com todas as tabelas, dados de 
--            exemplo, usuário de teste e dashboards configurados.
-- Data: 11 de Novembro de 2025
-- Versão: 2.0
-- ============================================================================

-- ============================================================================
-- PARTE 1: CRIAR BANCO DE DADOS E USUÁRIO
-- ============================================================================

-- Conectar como postgres (superusuário)
-- Execute: psql -U postgres

-- Criar banco de dados
DROP DATABASE IF EXISTS automacao_db;
CREATE DATABASE automacao_db;

-- Criar usuário
DROP USER IF EXISTS automacao_user;
CREATE USER automacao_user WITH PASSWORD 'senha123';

-- Conceder permissões
GRANT ALL PRIVILEGES ON DATABASE automacao_db TO automacao_user;

-- Conectar ao banco criado
\c automacao_db

-- Conceder permissões no schema public
GRANT ALL ON SCHEMA public TO automacao_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO automacao_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO automacao_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO automacao_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO automacao_user;

-- ============================================================================
-- PARTE 2: CRIAR TABELAS
-- ============================================================================

-- Tabela: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

COMMENT ON TABLE users IS 'Usuários do sistema';
COMMENT ON COLUMN users.role IS 'Papel do usuário: admin, manager, operator';

-- ============================================================================

-- Tabela: sector
CREATE TABLE IF NOT EXISTS sector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sector IS 'Setores da empresa';

-- ============================================================================

-- Tabela: sector_members
CREATE TABLE IF NOT EXISTS sector_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector_id UUID NOT NULL REFERENCES sector(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(sector_id, user_id)
);

CREATE INDEX idx_sector_members_sector_id ON sector_members(sector_id);
CREATE INDEX idx_sector_members_user_id ON sector_members(user_id);

COMMENT ON TABLE sector_members IS 'Membros de cada setor';
COMMENT ON COLUMN sector_members.role IS 'Papel no setor: manager, operator';

-- ============================================================================

-- Tabela: automations
CREATE TABLE IF NOT EXISTS automations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    module_path VARCHAR(500) NOT NULL,
    func_name VARCHAR(255) NOT NULL,
    owner_type VARCHAR(50) NOT NULL,
    owner_id UUID NOT NULL,
    default_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_automations_owner ON automations(owner_type, owner_id);
CREATE INDEX idx_automations_name ON automations(name);

COMMENT ON TABLE automations IS 'Automações configuradas no sistema';
COMMENT ON COLUMN automations.owner_type IS 'Tipo de proprietário: user, sector';
COMMENT ON COLUMN automations.config_schema IS 'Schema JSON para configuração dinâmica';

-- ============================================================================

-- Tabela: automation_operators
CREATE TABLE IF NOT EXISTS automation_operators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(automation_id, user_id)
);

CREATE INDEX idx_automation_operators_automation_id ON automation_operators(automation_id);
CREATE INDEX idx_automation_operators_user_id ON automation_operators(user_id);

COMMENT ON TABLE automation_operators IS 'Operadores autorizados para cada automação';

-- ============================================================================

-- Tabela: runs
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_runs_automation_id ON runs(automation_id);
CREATE INDEX idx_runs_user_id ON runs(user_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);

COMMENT ON TABLE runs IS 'Execuções de automações';
COMMENT ON COLUMN runs.status IS 'Status: queued, running, completed, failed';

-- ============================================================================

-- Tabela: secrets
CREATE TABLE IF NOT EXISTS secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type VARCHAR(50) NOT NULL,
    owner_id UUID NOT NULL,
    key VARCHAR(255) NOT NULL,
    value_ciphertext TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_secrets_owner_key UNIQUE(owner_type, owner_id, key)
);

CREATE INDEX idx_secrets_owner ON secrets(owner_type, owner_id);

COMMENT ON TABLE secrets IS 'Segredos criptografados (credenciais, tokens, etc)';

-- ============================================================================

-- Tabela: schedules
CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    owner_type VARCHAR(50) NOT NULL,
    owner_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL,
    run_at TIMESTAMP WITH TIME ZONE,
    interval_seconds INTEGER,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    days_of_week VARCHAR(50),
    hour INTEGER,
    minute INTEGER
);

CREATE INDEX idx_schedules_automation_id ON schedules(automation_id);
CREATE INDEX idx_schedules_next_run_at ON schedules(next_run_at);
CREATE INDEX idx_schedules_enabled ON schedules(enabled);

COMMENT ON TABLE schedules IS 'Agendamentos de automações';
COMMENT ON COLUMN schedules.type IS 'Tipo: once, interval, cron';

-- ============================================================================

-- Tabela: dashboard_configs
CREATE TABLE IF NOT EXISTS dashboard_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Navegação no menu
    menu_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Busca visual
    search_text VARCHAR(500),
    search_image VARCHAR(500),
    
    -- Coordenadas (fallback)
    click_coords JSONB,
    menu_coords JSONB,
    
    -- Screenshot
    screenshot_region JSONB NOT NULL DEFAULT '[0, 40, 1920, 1000]'::jsonb,
    
    -- Configuração de período
    has_period_selector BOOLEAN NOT NULL DEFAULT FALSE,
    available_periodicities JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dashboard_configs_name ON dashboard_configs(name);
CREATE INDEX idx_dashboard_configs_is_active ON dashboard_configs(is_active);

COMMENT ON TABLE dashboard_configs IS 'Configurações de dashboards do sistema DELPHOS.BI';
COMMENT ON COLUMN dashboard_configs.menu_path IS 'Caminho no menu hierárquico, ex: ["Dashboards", "Geradores", "Planilhas"]';
COMMENT ON COLUMN dashboard_configs.search_text IS 'Texto para buscar na lista de dashboards';
COMMENT ON COLUMN dashboard_configs.search_image IS 'Nome do arquivo de imagem de referência';
COMMENT ON COLUMN dashboard_configs.screenshot_region IS 'Região de captura [x, y, largura, altura]';
COMMENT ON COLUMN dashboard_configs.has_period_selector IS 'Se o dashboard possui seletor de período';
COMMENT ON COLUMN dashboard_configs.available_periodicities IS 'Periodicidades disponíveis: ["diario", "mensal", "anual"]';

-- ============================================================================
-- PARTE 3: INSERIR DADOS DE EXEMPLO
-- ============================================================================

-- Usuário de teste (admin)
-- Senha: teste123 (hash bcrypt)
INSERT INTO users (name, email, password, role)
VALUES (
    'Usuário Teste',
    'teste@bahniuk.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LS2LGYw5nQTK',
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Setor Comercial
INSERT INTO sector (id, name)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Comercial'
) ON CONFLICT DO NOTHING;

-- Adicionar usuário teste ao setor comercial como manager
INSERT INTO sector_members (sector_id, user_id, role)
SELECT 
    '00000000-0000-0000-0000-000000000001',
    id,
    'manager'
FROM users
WHERE email = 'teste@bahniuk.com'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- PARTE 4: INSERIR DASHBOARDS DE EXEMPLO
-- ============================================================================

INSERT INTO dashboard_configs (name, display_name, description, menu_path, search_text, screenshot_region, has_period_selector, available_periodicities, is_active)
VALUES 
    -- Dashboard 1: Comercial 2024 x 2025
    (
        'comercial_2024_2025',
        'Comercial - 2024 x 2025',
        'Dashboard comparativo de vendas entre 2024 e 2025',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'Comercial - 2024 x 2025 - Homologação - Adrian',
        '[0, 40, 1920, 1000]'::jsonb,
        TRUE,
        '["diario", "mensal", "anual"]'::jsonb,
        TRUE
    ),
    
    -- Dashboard 2: Comercial Comparativo
    (
        'comercial_comparativo',
        'Comercial - Comparativo',
        'Dashboard comparativo de vendas por período',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'Comercial - Comparativo',
        '[0, 40, 1920, 1000]'::jsonb,
        TRUE,
        '["mensal", "anual"]'::jsonb,
        TRUE
    ),
    
    -- Dashboard 3: Comercial Estoque
    (
        'comercial_estoque',
        'Comercial - Estoque',
        'Dashboard de controle de estoque',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'Comercial - Estoque',
        '[0, 40, 1920, 1000]'::jsonb,
        TRUE,
        '["diario", "mensal"]'::jsonb,
        TRUE
    ),
    
    -- Dashboard 4: Financeiro
    (
        'financeiro',
        'Financeiro - Contas a Receber',
        'Dashboard financeiro de contas a receber',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'Financeiro - Contas a Receber',
        '[0, 60, 1800, 950]'::jsonb,
        TRUE,
        '["mensal", "anual"]'::jsonb,
        TRUE
    ),
    
    -- Dashboard 5: Produção
    (
        'producao_diaria',
        'Produção - Diária',
        'Dashboard de produção diária',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'Produção - Diária',
        '[0, 40, 1920, 1000]'::jsonb,
        TRUE,
        '["diario"]'::jsonb,
        TRUE
    ),
    
    -- Dashboard 6: RH
    (
        'rh_folha_pagamento',
        'RH - Folha de Pagamento',
        'Dashboard de folha de pagamento',
        '["Dashboards", "Geradores De Dashboards", "Planilhas"]'::jsonb,
        'RH - Folha de Pagamento',
        '[0, 40, 1920, 1000]'::jsonb,
        TRUE,
        '["mensal"]'::jsonb,
        TRUE
    )
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- PARTE 5: INSERIR AUTOMAÇÃO DE EXEMPLO
-- ============================================================================

-- Automação de Dashboard (vinculada ao setor Comercial)
INSERT INTO automations (name, description, module_path, func_name, owner_type, owner_id, config_schema)
SELECT 
    'Relatório de Dashboard DELPHOS.BI',
    'Gera relatórios automatizados do sistema DELPHOS.BI com envio opcional via WhatsApp',
    'modules.comercial.dashboard.run_dashboard_v2',
    'main',
    'sector',
    '00000000-0000-0000-0000-000000000001',
    '{
        "type": "object",
        "properties": {
            "dashboard_name": {
                "type": "string",
                "title": "Dashboard",
                "description": "Nome do dashboard a ser executado",
                "enum_source": "dashboards"
            },
            "periodicidade": {
                "type": "string",
                "title": "Periodicidade",
                "enum": ["diario", "mensal", "anual"]
            },
            "dia": {
                "type": "integer",
                "title": "Dia",
                "minimum": 1,
                "maximum": 31,
                "condition": "periodicidade == \"diario\""
            },
            "mes": {
                "type": "integer",
                "title": "Mês",
                "minimum": 1,
                "maximum": 12,
                "condition": "periodicidade in [\"diario\", \"mensal\"]"
            },
            "ano": {
                "type": "integer",
                "title": "Ano",
                "minimum": 2020,
                "maximum": 2030
            },
            "enviar_whatsapp": {
                "type": "boolean",
                "title": "Enviar via WhatsApp",
                "default": false
            },
            "numeros_whatsapp": {
                "type": "array",
                "title": "Números WhatsApp",
                "items": {"type": "string"},
                "condition": "enviar_whatsapp == true"
            },
            "mensagem": {
                "type": "string",
                "title": "Mensagem",
                "condition": "enviar_whatsapp == true"
            }
        },
        "required": ["dashboard_name", "periodicidade", "ano"]
    }'::jsonb
ON CONFLICT DO NOTHING;

-- ============================================================================
-- PARTE 6: VERIFICAÇÃO
-- ============================================================================

-- Contar registros criados
SELECT 'users' AS tabela, COUNT(*) AS total FROM users
UNION ALL
SELECT 'sector', COUNT(*) FROM sector
UNION ALL
SELECT 'sector_members', COUNT(*) FROM sector_members
UNION ALL
SELECT 'automations', COUNT(*) FROM automations
UNION ALL
SELECT 'dashboard_configs', COUNT(*) FROM dashboard_configs;

-- ============================================================================
-- PARTE 7: INFORMAÇÕES DE ACESSO
-- ============================================================================

-- Exibir informações de acesso
SELECT 
    '=== INFORMAÇÕES DE ACESSO ===' AS info
UNION ALL
SELECT ''
UNION ALL
SELECT 'Banco de Dados: automacao_db'
UNION ALL
SELECT 'Usuário DB: automacao_user'
UNION ALL
SELECT 'Senha DB: senha123'
UNION ALL
SELECT ''
UNION ALL
SELECT 'Usuário Portal: teste@bahniuk.com'
UNION ALL
SELECT 'Senha Portal: teste123'
UNION ALL
SELECT 'Role: admin'
UNION ALL
SELECT ''
UNION ALL
SELECT 'Dashboards cadastrados: 6'
UNION ALL
SELECT 'Automações cadastradas: 1'
UNION ALL
SELECT ''
UNION ALL
SELECT '=== PRONTO PARA USO! ===';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
