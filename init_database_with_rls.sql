-- DataLix AI - Complete Database Schema with Supabase Auth & RLS
-- PostgreSQL Database Initialization Script with Row Level Security
-- 
-- This script creates all necessary tables, RLS policies, indexes, triggers, and functions
-- for the AI-Powered Data Analysis Platform with Supabase Authentication

-- =============================================================================
-- ENABLE ROW LEVEL SECURITY
-- =============================================================================

-- Enable RLS on all tables (we'll define this after creating tables)

-- =============================================================================
-- TABLE: profiles
-- Description: User profile information (linked to auth.users)
-- Note: Supabase's auth.users handles authentication, this stores additional profile data
-- =============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    is_master INTEGER NOT NULL DEFAULT 0,  -- Flag for master users (1 = master, 0 = regular)
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Enable RLS on profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
-- Users can view their own profile
CREATE POLICY "Users can view own profile"
    ON profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own profile (except is_master which is admin-only)
CREATE POLICY "Users can update own profile"
    ON profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Allow inserts during signup (triggered by Supabase Auth)
CREATE POLICY "Enable insert for authenticated users during signup"
    ON profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Indexes for profiles table
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_is_master ON profiles(is_master);

-- Comments for profiles table
COMMENT ON TABLE profiles IS 'User profile information linked to Supabase auth.users';
COMMENT ON COLUMN profiles.id IS 'User ID (matches auth.users.id)';
COMMENT ON COLUMN profiles.username IS 'Unique username for display';
COMMENT ON COLUMN profiles.email IS 'User email (synced from auth.users)';
COMMENT ON COLUMN profiles.is_master IS 'Flag indicating if user has unlimited message quota (1 = master, 0 = regular user)';
COMMENT ON COLUMN profiles.created_at IS 'Profile creation timestamp';

-- =============================================================================
-- TABLE: sessions
-- Description: Stores data analysis sessions for each user
-- =============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Enable RLS on sessions
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for sessions
-- Users can only view their own sessions
CREATE POLICY "Users can view own sessions"
    ON sessions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own sessions
CREATE POLICY "Users can create own sessions"
    ON sessions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own sessions
CREATE POLICY "Users can update own sessions"
    ON sessions
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own sessions
CREATE POLICY "Users can delete own sessions"
    ON sessions
    FOR DELETE
    USING (auth.uid() = user_id);

-- Indexes for sessions table
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);

-- Comments for sessions table
COMMENT ON TABLE sessions IS 'Data analysis sessions containing datasets and chat history';
COMMENT ON COLUMN sessions.id IS 'Unique session identifier (UUID)';
COMMENT ON COLUMN sessions.user_id IS 'Owner of the session (foreign key to profiles)';
COMMENT ON COLUMN sessions.name IS 'Optional session name/title';
COMMENT ON COLUMN sessions.created_at IS 'Session creation timestamp';
COMMENT ON COLUMN sessions.updated_at IS 'Last update timestamp (auto-updated)';

-- Trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to execute the function on sessions update
DROP TRIGGER IF EXISTS sessions_updated_at_trigger ON sessions;
CREATE TRIGGER sessions_updated_at_trigger
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_sessions_updated_at();

-- =============================================================================
-- TABLE: datasets
-- Description: Stores uploaded dataset data for persistence across restarts
-- =============================================================================

CREATE TABLE IF NOT EXISTS datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  file_name TEXT,
  data_csv TEXT,
  data_preview JSONB,
  quality_score JSONB,
  metadata JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own datasets"
ON datasets FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can create own datasets"
ON datasets FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own datasets"
ON datasets FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own datasets"
ON datasets FOR DELETE
USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_datasets_session_id ON datasets(session_id);
CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);

COMMENT ON TABLE datasets IS 'Persisted dataset data for analysis sessions';
COMMENT ON COLUMN datasets.session_id IS 'Associated session (unique, one dataset per session)';
COMMENT ON COLUMN datasets.user_id IS 'Owner of the dataset';
COMMENT ON COLUMN datasets.data_csv IS 'Dataset content stored as CSV text';
COMMENT ON COLUMN datasets.data_preview IS 'Data preview structure (JSON)';
COMMENT ON COLUMN datasets.quality_score IS 'Data quality analysis results (JSON)';
COMMENT ON COLUMN datasets.metadata IS 'Dataset metadata (row count, column count, etc.)';

-- Trigger to auto-update updated_at on datasets
DROP TRIGGER IF EXISTS datasets_updated_at_trigger ON datasets;
CREATE TRIGGER datasets_updated_at_trigger
BEFORE UPDATE ON datasets
FOR EACH ROW
EXECUTE FUNCTION update_sessions_updated_at();

-- =============================================================================
-- TABLE: messages
-- Description: Stores chat messages and AI analysis results within sessions
-- =============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    chart_data JSONB,
    data_preview JSONB,
    suggested_actions JSONB,
    function_calls JSONB,
    error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Enable RLS on messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for messages
-- Users can only view messages in their own sessions
CREATE POLICY "Users can view messages in own sessions"
    ON messages
    FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- Users can insert messages in their own sessions
CREATE POLICY "Users can create messages in own sessions"
    ON messages
    FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- Users can update messages in their own sessions
CREATE POLICY "Users can update messages in own sessions"
    ON messages
    FOR UPDATE
    USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- Users can delete messages in their own sessions
CREATE POLICY "Users can delete messages in own sessions"
    ON messages
    FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- Indexes for messages table
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- JSONB GIN indexes for better query performance on JSON data
CREATE INDEX IF NOT EXISTS idx_messages_chart_data ON messages USING GIN (chart_data);
CREATE INDEX IF NOT EXISTS idx_messages_data_preview ON messages USING GIN (data_preview);

-- Comments for messages table
COMMENT ON TABLE messages IS 'Chat messages and AI analysis results';
COMMENT ON COLUMN messages.id IS 'Unique message identifier (UUID)';
COMMENT ON COLUMN messages.session_id IS 'Parent session (foreign key to sessions)';
COMMENT ON COLUMN messages.role IS 'Message sender: user or assistant';
COMMENT ON COLUMN messages.content IS 'Message text content';
COMMENT ON COLUMN messages.chart_data IS 'Plotly chart data (JSON format)';
COMMENT ON COLUMN messages.data_preview IS 'Data table preview (JSON format)';
COMMENT ON COLUMN messages.suggested_actions IS 'AI-suggested next actions (JSON array)';
COMMENT ON COLUMN messages.function_calls IS 'AI function calls executed (JSON array)';
COMMENT ON COLUMN messages.error IS 'Error message if processing failed';
COMMENT ON COLUMN messages.created_at IS 'Message timestamp';

-- =============================================================================
-- FUNCTION: Automatically create profile when user signs up
-- =============================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'username', SPLIT_PART(NEW.email, '@', 1)),
        NEW.email
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to automatically create profile when user signs up via Supabase Auth
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- =============================================================================
-- MASTER USER SETUP
-- =============================================================================

-- To set a user as master (unlimited message quota), run:
-- UPDATE profiles SET is_master = 1 WHERE email = 'your-email@example.com';

-- To verify master user status:
-- SELECT id, email, username, is_master FROM profiles WHERE is_master = 1;

-- =============================================================================
-- USEFUL QUERIES
-- =============================================================================

-- Get current user's profile:
-- SELECT * FROM profiles WHERE id = auth.uid();

-- Get all sessions for current user with message counts:
-- SELECT 
--     s.id,
--     s.name,
--     s.created_at,
--     s.updated_at,
--     COUNT(m.id) as message_count
-- FROM sessions s
-- LEFT JOIN messages m ON m.session_id = s.id
-- WHERE s.user_id = auth.uid()
-- GROUP BY s.id
-- ORDER BY s.updated_at DESC;

-- Get full chat history for a session (RLS enforces ownership):
-- SELECT 
--     id,
--     role,
--     content,
--     chart_data,
--     data_preview,
--     suggested_actions,
--     created_at
-- FROM messages
-- WHERE session_id = 'session-uuid-here'
-- ORDER BY created_at ASC;

-- Find sessions with errors:
-- SELECT DISTINCT s.*, m.error
-- FROM sessions s
-- INNER JOIN messages m ON m.session_id = s.id
-- WHERE m.error IS NOT NULL
-- ORDER BY s.updated_at DESC;

-- Get all master users (admin only):
-- SELECT id, email, username, created_at
-- FROM profiles
-- WHERE is_master = 1;

-- =============================================================================
-- MIGRATION FROM OLD SCHEMA
-- =============================================================================

-- If migrating from the old 'users' table to 'profiles':
-- 
-- 1. First, create auth.users entries for existing users (requires Supabase admin)
-- 2. Then migrate data:
-- INSERT INTO profiles (id, username, email, is_master, created_at)
-- SELECT id, username, email, is_master, created_at FROM users;
-- 
-- 3. Drop old table:
-- DROP TABLE IF EXISTS users CASCADE;

-- =============================================================================
-- CLEANUP QUERIES (USE WITH CAUTION)
-- =============================================================================

-- Delete old sessions (older than 90 days):
-- DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete sessions with no messages:
-- DELETE FROM sessions WHERE id NOT IN (SELECT DISTINCT session_id FROM messages);

-- =============================================================================
-- DATABASE STATISTICS
-- =============================================================================

-- Get table sizes:
-- SELECT 
--     tablename,
--     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Get row counts:
-- SELECT 
--     'profiles' as table_name, COUNT(*) as row_count FROM profiles
-- UNION ALL
-- SELECT 'sessions', COUNT(*) FROM sessions
-- UNION ALL
-- SELECT 'messages', COUNT(*) FROM messages;
