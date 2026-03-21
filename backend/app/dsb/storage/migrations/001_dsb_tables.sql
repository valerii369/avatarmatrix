"""
DSB Storage — SQL migration script.
Полная схема таблиц под все 8 учений.
Запустить вручную через psql или Supabase SQL editor.
"""

CREATE_DSB_TABLES_SQL = """
-- ─── Расширения ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Основная таблица портрета ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_digital_portraits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    birth_data JSONB NOT NULL,
    status TEXT DEFAULT 'generating'
        CHECK (status IN ('generating', 'ready', 'error')),
    version INTEGER DEFAULT 1,
    systems_used TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_portraits_user ON dsb_digital_portraits(user_id);
CREATE INDEX IF NOT EXISTS idx_dsb_portraits_status ON dsb_digital_portraits(status);

-- ─── Уровень 1: Атомарные факты ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    source_system TEXT NOT NULL,
    sphere_primary INTEGER NOT NULL CHECK (sphere_primary BETWEEN 1 AND 12),
    spheres_affected INTEGER[] DEFAULT '{}',
    position TEXT NOT NULL,
    influence_level TEXT NOT NULL CHECK (influence_level IN ('high', 'medium', 'low')),
    light_aspect TEXT,
    shadow_aspect TEXT,
    energy_description TEXT,
    core_theme TEXT,
    developmental_task TEXT,
    integration_key TEXT,
    triggers TEXT[],
    timing TEXT,
    book_references TEXT[],
    weight FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.5,
    raw_uis JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_facts_portrait ON dsb_portrait_facts(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_facts_sphere ON dsb_portrait_facts(sphere_primary);
CREATE INDEX IF NOT EXISTS idx_dsb_facts_system ON dsb_portrait_facts(source_system);
CREATE INDEX IF NOT EXISTS idx_dsb_facts_influence ON dsb_portrait_facts(influence_level);
CREATE INDEX IF NOT EXISTS idx_dsb_facts_embedding ON dsb_portrait_facts
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── Уровень 2: Аспектные цепочки ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_aspect_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    sphere INTEGER NOT NULL,
    chain_name TEXT NOT NULL,
    systems_involved TEXT[],
    convergence_score FLOAT NOT NULL CHECK (convergence_score BETWEEN 0 AND 1),
    description TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_chains_portrait ON dsb_portrait_aspect_chains(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_chains_embedding ON dsb_portrait_aspect_chains
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ─── Уровень 3: Синтезированные паттерны ────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    sphere INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    formula TEXT,
    description TEXT NOT NULL,
    systems_supporting TEXT[],
    convergence_score FLOAT,
    influence_level TEXT CHECK (influence_level IN ('high', 'medium', 'low')),
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_patterns_portrait ON dsb_portrait_patterns(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_patterns_sphere ON dsb_portrait_patterns(sphere);
CREATE INDEX IF NOT EXISTS idx_dsb_patterns_embedding ON dsb_portrait_patterns
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ─── Уровень 4: Рекомендации ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    sphere INTEGER NOT NULL,
    recommendation TEXT NOT NULL,
    source_systems TEXT[],
    influence_level TEXT CHECK (influence_level IN ('high', 'medium', 'low')),
    category TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_rec_portrait ON dsb_portrait_recommendations(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_rec_sphere ON dsb_portrait_recommendations(sphere);
CREATE INDEX IF NOT EXISTS idx_dsb_rec_embedding ON dsb_portrait_recommendations
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ─── Уровень 5: Теневой аудит ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_shadow_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    sphere INTEGER NOT NULL,
    risk_name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_systems TEXT[],
    convergence_score FLOAT,
    antidote TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_shadow_portrait ON dsb_portrait_shadow_audit(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_shadow_embedding ON dsb_portrait_shadow_audit
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ─── Уровень 6: Межсферные суперпаттерны ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_meta_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    pattern_name TEXT NOT NULL,
    spheres_involved INTEGER[],
    description TEXT NOT NULL,
    systems_supporting TEXT[],
    convergence_score FLOAT,
    key_manifestations JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_meta_portrait ON dsb_portrait_meta_patterns(portrait_id);
CREATE INDEX IF NOT EXISTS idx_dsb_meta_embedding ON dsb_portrait_meta_patterns
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- ─── Уровень 7: Краткий формат ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dsb_portrait_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portrait_id UUID REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
    sphere INTEGER,
    brief_text TEXT NOT NULL,
    is_overall BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dsb_summaries_portrait ON dsb_portrait_summaries(portrait_id);
"""
