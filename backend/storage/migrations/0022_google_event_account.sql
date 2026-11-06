-- Keep imported tasks and deduplicate event imports within their verified account.
-- Old import rows do not identify the account that imported them. Preserve them unbound.
ALTER TABLE google_event_tasks RENAME TO google_event_tasks_previous;

CREATE TABLE google_event_tasks (
    account_key TEXT NOT NULL,
    calendar_id TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    task_id     TEXT NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (account_key, calendar_id, event_id)
);

INSERT INTO google_event_tasks (account_key, calendar_id, event_id, task_id, created_at)
SELECT '', calendar_id, event_id, task_id, created_at
FROM google_event_tasks_previous;

DROP TABLE google_event_tasks_previous;
