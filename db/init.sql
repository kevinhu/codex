CREATE TABLE IF NOT EXISTS topic (
    id SERIAL PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    is_primary BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finding (
    id SERIAL PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_finding (
    topic_id INT NOT NULL,
    finding_id INT NOT NULL,
    PRIMARY KEY (topic_id, finding_id),
    FOREIGN KEY (topic_id) REFERENCES topic (id),
    FOREIGN KEY (finding_id) REFERENCES finding (id)
);