-- Keep the original placement rows and immutable closed snapshots unchanged.
CREATE TABLE placement_positions (
    placement_id TEXT PRIMARY KEY NOT NULL REFERENCES planned_items(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0)
);

INSERT INTO placement_positions (placement_id, position)
SELECT id, ROW_NUMBER() OVER (PARTITION BY planned_date ORDER BY created_at, rowid) - 1
FROM planned_items;
