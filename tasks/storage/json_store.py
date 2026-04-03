from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from tasks.models import Task
from tasks.storage.base import BaseStorage


class JSONStorage(BaseStorage):
    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            self._write([])

    def _read(self) -> List[dict]:
        if not self.file_path.exists():
            return []
        raw = self.file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        return json.loads(raw)

    def _write(self, data: List[dict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, task: Task) -> None:
        data = self._read()
        data.append(task.to_dict())
        self._write(data)

    def list(self) -> List[Task]:
        tasks = [Task.from_dict(item) for item in self._read()]
        return sorted(tasks, key=lambda t: (-t.priority, t.id))

    def get(self, task_id: int) -> Optional[Task]:
        for item in self._read():
            if int(item["id"]) == task_id:
                return Task.from_dict(item)
        return None

    def update(self, task: Task) -> bool:
        data = self._read()
        updated = False
        for idx, item in enumerate(data):
            if int(item["id"]) == task.id:
                data[idx] = task.to_dict()
                updated = True
                break
        if updated:
            self._write(data)
        return updated

    def delete(self, task_id: int) -> bool:
        data = self._read()
        original_len = len(data)
        data = [t for t in data if int(t["id"]) != task_id]
        self._write(data)
        return len(data) != original_len
