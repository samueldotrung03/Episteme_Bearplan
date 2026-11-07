-- Pending provider creates survive crashes and account changes. No task content,
-- credential or foreign key is stored: local deletion must not erase uncertainty.
CREATE TABLE google_create_intents (
    operation_id TEXT PRIMARY KEY NOT NULL CHECK (length(operation_id) = 36),
    account_key TEXT NOT NULL CHECK (length(account_key) = 32),
    resource_kind TEXT NOT NULL CHECK (resource_kind IN ('task_list', 'task', 'calendar', 'event')),
    local_id TEXT NOT NULL CHECK (length(local_id) BETWEEN 1 AND 200),
    parent_id TEXT NOT NULL CHECK (length(parent_id) <= 300),
    created_at TEXT NOT NULL,
    UNIQUE (account_key)
);
