"""Atomic, replay-safe task capture with an optional planned date."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from pydantic import BaseModel

from backend.domain.errors import InvalidInput
from backend.domain.planning import Placement, WeekConflict, _create_placement_tx, _planned_date
from backend.domain.tasks import Task, _clean_deadline, _clean_estimate, _clean_notes, _clean_title, _create_task_tx
from backend.storage.db import Database, utc_now


class CaptureResult(BaseModel):
    task: Task
    placement: Placement | None


def capture_task(
    db: Database, operation_id: str, title: str, *, project_id: str | None = None,
    parent_id: str | None = None, notes: str | None = None,
    deadline: str | date | None = None, estimate_minutes: int | None = None,
    planned_date: str | date | None = None,
) -> CaptureResult:
    """Save a task and optional placement together, replaying the original result."""
    try:
        if not isinstance(operation_id, str) or str(UUID(operation_id)) != operation_id:
            raise ValueError
    except (ValueError, AttributeError):
        raise InvalidInput("operation_id", "Use a valid unique operation ID and keep it when retrying.") from None
    normalized = {
        "title": _clean_title(title), "project_id": project_id, "parent_id": parent_id,
        "notes": _clean_notes(notes), "deadline": _clean_deadline(deadline),
        "estimate_minutes": _clean_estimate(estimate_minutes),
        "planned_date": _planned_date(planned_date) if planned_date is not None else None,
    }
    fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    with db.write() as conn:
        prior = conn.execute("SELECT request_hash, result_json FROM task_capture_operations WHERE operation_id = ?", (operation_id,)).fetchone()
        if prior:
            if prior["request_hash"] != fingerprint:
                raise WeekConflict("operation_id", "This save was already used for different task details. Nothing was changed.")
            return CaptureResult.model_validate_json(prior["result_json"])
        task = _create_task_tx(conn, normalized["title"], project_id=project_id, parent_id=parent_id,
                               notes=normalized["notes"], deadline=normalized["deadline"], estimate_minutes=normalized["estimate_minutes"])
        placement = _create_placement_tx(conn, task.id, normalized["planned_date"]) if normalized["planned_date"] is not None else None
        result = CaptureResult(task=task, placement=placement)
        conn.execute("INSERT INTO task_capture_operations (operation_id, request_hash, result_json, created_at) VALUES (?, ?, ?, ?)",
                     (operation_id, fingerprint, result.model_dump_json(), utc_now()))
        return result
