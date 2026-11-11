-- Durable replay receipts for atomic task capture with optional planning.
CREATE TABLE task_capture_operations (
    operation_id TEXT PRIMARY KEY NOT NULL CHECK (length(operation_id) = 36),
    request_hash TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
