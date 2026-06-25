"""Supabase database schema SQL for auto-provisioning.

Contains the SQL migrations needed to set up a fresh Supabase project
with the correct table structure for Home Unit Calculator.

The schema is inferred from src/core/supabase_manager.py usage patterns:
- main_calculations: stores month/year calculation data as JSONB
- room_calculations: stores per-room data as JSONB with image URLs
- rental_records: stores tenant rental info with image URLs

All statements use IF NOT EXISTS for idempotent application.
RLS is enabled with permissive policies (each user owns their own project).
"""


SCHEMA_VERSION = 2


def get_migration_sql() -> str:
    """Return the full SQL migration for initial schema setup.

    This is sent to the Supabase Management API's migration endpoint
    (POST /v1/projects/{ref}/database/migrations) to create all tables,
    policies, and the schema version marker in one shot.
    """
    return """
-- ============================================================
-- Home Unit Calculator Schema v1
-- Auto-provisioned by the app's OAuth2 onboarding flow
-- ============================================================

-- Table: main_calculations
-- Stores monthly calculation data as JSONB
CREATE TABLE IF NOT EXISTS main_calculations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    month TEXT,
    year INTEGER,
    main_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Security note: Each user gets their own isolated Supabase project, so the
-- anon key acts as the per-user credential. RLS is enabled as a defense-in-depth
-- measure. Policies allow anon access (the app uses the anon key, not Supabase Auth).
-- If the anon key leaks, an attacker can read/write data — protect it accordingly.
ALTER TABLE main_calculations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON main_calculations;
DROP POLICY IF EXISTS "Allow anon read-write" ON main_calculations;
CREATE POLICY "Allow anon read-write" ON main_calculations
    FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');

-- Table: room_calculations
-- Stores per-room calculation data, linked to main_calculations
CREATE TABLE IF NOT EXISTS room_calculations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    main_calculation_id BIGINT REFERENCES main_calculations(id) ON DELETE CASCADE,
    room_data JSONB,
    photo_url TEXT,
    nid_front_url TEXT,
    nid_back_url TEXT,
    police_form_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE room_calculations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON room_calculations;
DROP POLICY IF EXISTS "Allow anon read-write" ON room_calculations;
CREATE POLICY "Allow anon read-write" ON room_calculations
    FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');

-- Table: rental_records
-- Stores tenant rental information with image URLs
CREATE TABLE IF NOT EXISTS rental_records (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supabase_id TEXT UNIQUE,
    tenant_name TEXT,
    room_number TEXT,
    advanced_paid REAL,
    photo_url TEXT,
    nid_front_url TEXT,
    nid_back_url TEXT,
    police_form_url TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    start_year INTEGER,
    start_month INTEGER,
    end_year INTEGER,
    end_month INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE rental_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON rental_records;
DROP POLICY IF EXISTS "Allow anon read-write" ON rental_records;
CREATE POLICY "Allow anon read-write" ON rental_records
    FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');

-- Schema version marker (for idempotent provisioning checks)
CREATE TABLE IF NOT EXISTS _huc_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO _huc_schema_version (version) VALUES (2)
ON CONFLICT DO NOTHING;
"""


def get_version_check_sql() -> str:
    """Return SQL to check the current schema version on a project.

    Used to detect if a project already has the HUC schema applied.
    """
    return "SELECT COALESCE(MAX(version), 0) as version FROM _huc_schema_version;"
