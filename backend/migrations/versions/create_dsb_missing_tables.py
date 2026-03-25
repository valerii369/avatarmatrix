"""Create missing DSB tables: dsb_digital_portraits, dsb_portrait_aspect_chains,
dsb_portrait_shadow_audit, dsb_portrait_meta_patterns, dsb_portrait_summaries

Also note: dsb_portrait_facts, dsb_portrait_patterns, dsb_portrait_recommendations
already exist in DB but have FK to dsb_digital_portraits, so the parent must be created first.

Revision ID: create_dsb_missing_tables
Revises: fix_add_sphere_desc
Create Date: 2026-03-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'create_dsb_missing'
down_revision: Union[str, None] = 'fix_add_sphere_desc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Parent table: dsb_digital_portraits ───────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS dsb_digital_portraits (
            id          TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            birth_data  JSONB NOT NULL,
            status      VARCHAR(32) DEFAULT 'generating',
            version     INTEGER DEFAULT 1,
            systems_used TEXT[] DEFAULT '{}',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_digital_portraits_user_id ON dsb_digital_portraits(user_id)")

    # ─── Add FK to existing tables that reference dsb_digital_portraits ────────
    # These tables already exist but without FK enforcement (no parent table).
    # We need to add FK constraints now.
    # First check if constraint already exists, add only if not
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'dsb_portrait_facts_portrait_id_fkey'
                  AND table_name = 'dsb_portrait_facts'
            ) THEN
                ALTER TABLE dsb_portrait_facts
                ADD CONSTRAINT dsb_portrait_facts_portrait_id_fkey
                FOREIGN KEY (portrait_id) REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'dsb_portrait_patterns_portrait_id_fkey'
                  AND table_name = 'dsb_portrait_patterns'
            ) THEN
                ALTER TABLE dsb_portrait_patterns
                ADD CONSTRAINT dsb_portrait_patterns_portrait_id_fkey
                FOREIGN KEY (portrait_id) REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'dsb_portrait_recommendations_portrait_id_fkey'
                  AND table_name = 'dsb_portrait_recommendations'
            ) THEN
                ALTER TABLE dsb_portrait_recommendations
                ADD CONSTRAINT dsb_portrait_recommendations_portrait_id_fkey
                FOREIGN KEY (portrait_id) REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)

    # ─── dsb_portrait_aspect_chains ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS dsb_portrait_aspect_chains (
            id              TEXT PRIMARY KEY,
            portrait_id     TEXT NOT NULL REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
            sphere          INTEGER NOT NULL
                                CHECK (sphere BETWEEN 1 AND 12),
            chain_name      TEXT NOT NULL,
            systems_involved TEXT[] DEFAULT '{}',
            convergence_score FLOAT NOT NULL
                                CHECK (convergence_score BETWEEN 0 AND 1),
            description     TEXT NOT NULL,
            embedding       JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_portrait_aspect_chains_portrait_id ON dsb_portrait_aspect_chains(portrait_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_portrait_aspect_chains_sphere ON dsb_portrait_aspect_chains(sphere)")

    # ─── dsb_portrait_shadow_audit ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS dsb_portrait_shadow_audit (
            id              TEXT PRIMARY KEY,
            portrait_id     TEXT NOT NULL REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
            sphere          INTEGER NOT NULL
                                CHECK (sphere BETWEEN 1 AND 12),
            risk_name       TEXT NOT NULL,
            description     TEXT NOT NULL,
            source_systems  TEXT[] DEFAULT '{}',
            convergence_score FLOAT,
            antidote        TEXT NOT NULL,
            embedding       JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_portrait_shadow_audit_portrait_id ON dsb_portrait_shadow_audit(portrait_id)")

    # ─── dsb_portrait_meta_patterns ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS dsb_portrait_meta_patterns (
            id              TEXT PRIMARY KEY,
            portrait_id     TEXT NOT NULL REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
            pattern_name    TEXT NOT NULL,
            spheres_involved INTEGER[] DEFAULT '{}',
            description     TEXT NOT NULL,
            systems_supporting TEXT[] DEFAULT '{}',
            convergence_score FLOAT,
            key_manifestations JSONB,
            embedding       JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_portrait_meta_patterns_portrait_id ON dsb_portrait_meta_patterns(portrait_id)")

    # ─── dsb_portrait_summaries ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS dsb_portrait_summaries (
            id              TEXT PRIMARY KEY,
            portrait_id     TEXT NOT NULL REFERENCES dsb_digital_portraits(id) ON DELETE CASCADE,
            sphere          INTEGER,
            brief_text      TEXT NOT NULL,
            is_overall      BOOLEAN DEFAULT FALSE,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dsb_portrait_summaries_portrait_id ON dsb_portrait_summaries(portrait_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dsb_portrait_summaries CASCADE")
    op.execute("DROP TABLE IF EXISTS dsb_portrait_meta_patterns CASCADE")
    op.execute("DROP TABLE IF EXISTS dsb_portrait_shadow_audit CASCADE")
    op.execute("DROP TABLE IF EXISTS dsb_portrait_aspect_chains CASCADE")
    op.execute("DROP TABLE IF EXISTS dsb_digital_portraits CASCADE")
