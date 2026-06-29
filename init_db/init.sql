CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_name TEXT,
    raw_event JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);