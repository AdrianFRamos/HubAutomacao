CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela: users
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  password TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','manager','operator')),
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (LOWER(email));

-- Tabela: sector
CREATE TABLE IF NOT EXISTS sector (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabela: sector_members
CREATE TABLE IF NOT EXISTS sector_members (
  sector_id UUID REFERENCES sector(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT CHECK (role IN ('admin','manager','member')) DEFAULT 'member',
  PRIMARY KEY (sector_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_sector_members_user_id ON sector_members (user_id);
CREATE INDEX IF NOT EXISTS idx_sector_members_sector_id ON sector_members (sector_id);

-- Tabela: automations
CREATE TABLE IF NOT EXISTS automations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  module_path TEXT NOT NULL,
  func_name   TEXT NOT NULL,
  owner_type TEXT NOT NULL CHECK (owner_type IN ('user','sector')) DEFAULT 'user',
  owner_id UUID NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Ajuda nas buscas por dono (user/sector)
CREATE INDEX IF NOT EXISTS idx_automations_owner ON automations(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_automations_enabled ON automations(enabled);

-- Tabela: runs
CREATE TABLE IF NOT EXISTS runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  status TEXT NOT NULL CHECK (status IN ('queued','running','success','failed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  result  JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_runs_automation_id ON runs(automation_id);
CREATE INDEX IF NOT EXISTS idx_runs_user_id ON runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

-- Tabela: secrets
CREATE TABLE IF NOT EXISTS secrets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_type TEXT NOT NULL CHECK (owner_type IN ('user','sector')),
  owner_id UUID NOT NULL,
  key TEXT NOT NULL,
  value_ciphertext TEXT NOT NULL, 
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_secrets_owner_key ON secrets(owner_type, owner_id, key);

-- Tabela: automation_operators
CREATE TABLE IF NOT EXISTS automation_operators (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (automation_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_automation_operators_automation_id ON automation_operators (automation_id);
CREATE INDEX IF NOT EXISTS idx_automation_operators_user_id ON automation_operators (user_id);

-- Tabela: schedules
CREATE TABLE IF NOT EXISTS schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
  owner_type TEXT NOT NULL CHECK (owner_type IN ('user','sector')),
  owner_id UUID NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('once','interval','cron')),
  run_at TIMESTAMPTZ,
  interval_seconds INT,
  days_of_week TEXT,
  hour INT,
  minute INT,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_run_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (
    (type = 'once' AND run_at IS NOT NULL AND interval_seconds IS NULL AND days_of_week IS NULL AND hour IS NULL AND minute IS NULL)
    OR
    (type = 'interval' AND interval_seconds IS NOT NULL AND interval_seconds > 0 AND run_at IS NULL AND days_of_week IS NULL AND hour IS NULL AND minute IS NULL)
    OR
    (type = 'cron' AND days_of_week IS NOT NULL AND hour IS NOT NULL AND minute IS NOT NULL AND run_at IS NULL AND interval_seconds IS NULL)
  )
);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules (enabled, next_run_at);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules (enabled, next_run_at);
