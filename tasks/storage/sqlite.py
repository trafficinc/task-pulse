from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from tasks.models import Task
from tasks.storage.base import BaseStorage


class SQLiteStorage(BaseStorage):
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                impact INTEGER NOT NULL,
                frequency INTEGER NOT NULL,
                risk INTEGER NOT NULL,
                effort INTEGER NOT NULL,
                priority REAL NOT NULL,
                tag TEXT NOT NULL,
                due_date TEXT,
                created_at TEXT,
                completed_at TEXT,
                notes TEXT
            )
            """
        )

        columns = {row["name"] for row in cur.execute("PRAGMA table_info(tasks)").fetchall()}
        if "due_date" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        if "created_at" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
        if "completed_at" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
        if "notes" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")

        self.conn.commit()

    def add(self, task: Task) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (
                id, title, status, impact, frequency, risk, effort, priority, tag,
                due_date, created_at, completed_at, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.title,
                task.status,
                task.impact,
                task.frequency,
                task.risk,
                task.effort,
                task.priority,
                task.tag,
                task.due_date,
                task.created_at,
                task.completed_at,
                json.dumps(task.notes or []),
            ),
        )
        self.conn.commit()

    def list(self) -> List[Task]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT * FROM tasks ORDER BY priority DESC, id ASC").fetchall()
        return [Task.from_dict(dict(row)) for row in rows]

    def get(self, task_id: int) -> Optional[Task]:
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return Task.from_dict(dict(row)) if row else None

    def update(self, task: Task) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE tasks
                SET title = ?, status = ?, impact = ?, frequency = ?, risk = ?, effort = ?,
                    priority = ?, tag = ?, due_date = ?, created_at = ?, completed_at = ?
                    , notes = ?
            WHERE id = ?
            """,
            (
                task.title,
                task.status,
                task.impact,
                task.frequency,
                task.risk,
                task.effort,
                task.priority,
                task.tag,
                task.due_date,
                task.created_at,
                task.completed_at,
                json.dumps(task.notes or []),
                task.id,
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return cur.rowcount > 0
