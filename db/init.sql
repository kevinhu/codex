CREATE TABLE IF NOT EXISTS resolved_topic (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    type TEXT,
    is_primary BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_topic_id TEXT NOT NULL,
    FOREIGN KEY (resolved_topic_id) REFERENCES resolved_topic(id)
);

CREATE TABLE IF NOT EXISTS paper (
    id TEXT PRIMARY KEY,
    authors TEXT,
    title TEXT,
    update_date TIMESTAMP,
    abstract TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finding (
    id TEXT PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE finding
ADD COLUMN paper_id TEXT,
ADD FOREIGN KEY (paper_id) REFERENCES paper(id);

CREATE TABLE IF NOT EXISTS topic_finding (
    topic_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    resolved_topic_id TEXT NOT NULL,
    PRIMARY KEY (topic_id, finding_id),
    FOREIGN KEY (topic_id) REFERENCES topic (id),
    FOREIGN KEY (finding_id) REFERENCES finding (id),
    FOREIGN KEY (resolved_topic_id) REFERENCES resolved_topic (id)
);
CREATE INDEX topic_finding_topic_id_idx ON topic_finding(topic_id text_ops);
CREATE INDEX topic_finding_finding_id_idx ON topic_finding(finding_id text_ops);
CREATE INDEX topic_finding_resolved_topic_id_idx ON topic_finding(resolved_topic_id text_ops);