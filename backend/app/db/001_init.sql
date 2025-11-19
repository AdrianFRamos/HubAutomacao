
-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- sector
CREATE TABLE IF NOT EXISTS sector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Setores padrões
INSERT INTO sector (id, name)
SELECT gen_random_uuid(), 'Comercial' WHERE NOT EXISTS (SELECT 1 FROM sector WHERE name = 'Comercial');
INSERT INTO sector (id, name)
SELECT gen_random_uuid(), 'Operações' WHERE NOT EXISTS (SELECT 1 FROM sector WHERE name = 'Operações');
INSERT INTO sector (id, name)
SELECT gen_random_uuid(), 'RH' WHERE NOT EXISTS (SELECT 1 FROM sector WHERE name = 'RH');
INSERT INTO sector (id, name)
SELECT gen_random_uuid(), 'Financeiro' WHERE NOT EXISTS (SELECT 1 FROM sector WHERE name = 'Financeiro');
INSERT INTO sector (id, name)
SELECT gen_random_uuid(), 'T.I' WHERE NOT EXISTS (SELECT 1 FROM sector WHERE name = 'T.I');

-- sector_members
CREATE TABLE IF NOT EXISTS sector_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector_id UUID NOT NULL REFERENCES sector(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(sector_id, user_id)
);

-- automations

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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_automations_owner ON automations(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_automations_name ON automations(name);

-- automation_operators
CREATE TABLE IF NOT EXISTS automation_operators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(automation_id, user_id)
);

-- runs
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

-- secrets
CREATE TABLE IF NOT EXISTS secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type VARCHAR(50) NOT NULL,
    owner_id UUID NOT NULL,
    key VARCHAR(255) NOT NULL,
    value_ciphertext TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_secrets_owner_key UNIQUE(owner_type, owner_id, key)
);

-- schedules
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

-- dashboard_configs
CREATE TABLE IF NOT EXISTS dashboard_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    menu_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    search_text VARCHAR(500),
    search_image VARCHAR(500),
    click_coords JSONB,
    menu_coords JSONB,
    screenshot_region JSONB NOT NULL DEFAULT '[0, 40, 1920, 1000]'::jsonb,
    has_period_selector BOOLEAN NOT NULL DEFAULT FALSE,
    available_periodicities JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE automations 
ADD COLUMN IF NOT EXISTS automation_type VARCHAR(50) NOT NULL DEFAULT 'generic';

ALTER TABLE automations 
ADD COLUMN IF NOT EXISTS dashboard_screenshot VARCHAR(500);

ALTER TABLE automations 
ADD COLUMN IF NOT EXISTS dashboard_name_image VARCHAR(500);

CREATE INDEX IF NOT EXISTS idx_automations_type ON automations(automation_type);
