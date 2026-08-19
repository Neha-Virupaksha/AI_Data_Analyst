CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    filename TEXT,
    uploaded_at TIMESTAMP,
    schema_json TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES datasets(id),
    question TEXT,
    plan TEXT,
    final_code TEXT,
    chart_path TEXT,
    summary TEXT,
    retry_count INTEGER,
    status TEXT, -- 'success' | 'failed'
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_attempts (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id),
    attempt_number INTEGER,
    code TEXT,
    error TEXT,
    succeeded BOOLEAN
);
