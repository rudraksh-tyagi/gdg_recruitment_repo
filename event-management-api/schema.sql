-- ============================================================
-- Event Management API
-- Supabase PostgreSQL Schema
-- ============================================================

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    email VARCHAR(255) NOT NULL UNIQUE,

    hashed_password VARCHAR(255) NOT NULL,

    role VARCHAR(50) NOT NULL DEFAULT 'attendee',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    title VARCHAR(255) NOT NULL,

    description TEXT,

    location VARCHAR(255) NOT NULL,

    start_time TIMESTAMPTZ NOT NULL,

    end_time TIMESTAMPTZ NOT NULL,

    capacity INTEGER NOT NULL,

    organizer_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT events_capacity_positive
        CHECK (capacity > 0),

    CONSTRAINT events_valid_time_range
        CHECK (start_time < end_time),

    CONSTRAINT events_organizer_fk
        FOREIGN KEY (organizer_id)
        REFERENCES users(id)
        ON DELETE RESTRICT
);

-- ============================================================
-- REGISTRATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    event_id UUID NOT NULL,

    user_id UUID NOT NULL,

    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT registrations_event_fk
        FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE,

    CONSTRAINT registrations_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_registration_user_event
        UNIQUE (user_id, event_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_events_organizer_id
    ON events(organizer_id);

CREATE INDEX IF NOT EXISTS idx_events_start_time
    ON events(start_time);

CREATE INDEX IF NOT EXISTS idx_registrations_event_id
    ON registrations(event_id);

CREATE INDEX IF NOT EXISTS idx_registrations_user_id
    ON registrations(user_id);