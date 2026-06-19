-- Membuat tabel untuk menyimpan event yang diproses
CREATE TABLE IF NOT EXISTS processed_events (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ini adalah kunci Idempotency & Deduplication
    CONSTRAINT unique_topic_event UNIQUE (topic, event_id)
);

-- Membuat index untuk mempercepat pencarian data saat endpoint GET /events dipanggil
CREATE INDEX idx_topic_event ON processed_events(topic, event_id);