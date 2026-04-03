from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict


VALID_STATUSES = {"not_started", "started", "done"}


@dataclass
class Task:
    id: int
    title: str
    status: str = "not_started"
    impact: int = 3
    frequency: int = 3
    risk: int = 3
    effort: int = 3
    priority: float = 0.0
    tag: str = "general"
    due_date: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    notes: list[str] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def priority_bucket(self) -> int:
        if self.priority < 1.5:
            return 1
        if self.priority < 2.5:
            return 2
        if self.priority < 3.5:
            return 3
        if self.priority < 4.5:
            return 4
        return 5

    def due_date_obj(self) -> date | None:
        if not self.due_date:
            return None
        return date.fromisoformat(self.due_date)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        notes = data.get("notes", [])
        if isinstance(notes, str):
            notes = json.loads(notes) if notes else []
        elif notes is None:
            notes = []

        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            status=str(data.get("status", "not_started")),
            impact=int(data.get("impact", 3)),
            frequency=int(data.get("frequency", 3)),
            risk=int(data.get("risk", 3)),
            effort=int(data.get("effort", 3)),
            priority=float(data.get("priority", 0.0)),
            tag=str(data.get("tag", "general")),
            due_date=data.get("due_date"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            notes=list(notes),
        )


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()
