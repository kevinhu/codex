CREATE TABLE IF NOT EXISTS topic (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    type TEXT,
    is_primary BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finding (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_finding (
    topic_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    PRIMARY KEY (topic_id, finding_id),
    FOREIGN KEY (topic_id) REFERENCES topic (id),
    FOREIGN KEY (finding_id) REFERENCES finding (id)
);