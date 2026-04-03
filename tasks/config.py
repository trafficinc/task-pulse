from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_DB_TYPE = os.getenv("TASKS_DB_TYPE", "json").strip().lower() or "json"
TASKS_DIRNAME = ".tasks"
CONFIG_FILENAME = "config.json"
DEFAULT_SQLITE_FILENAME = "tasks.db"
DEFAULT_JSON_FILENAME = "tasks.json"
DEFAULT_BACKUP_DIRNAME = "backups"


class TasksConfigError(RuntimeError):
    pass


class TasksNotInitializedError(TasksConfigError):
    pass


def find_tasks_dir(start: Path | None = None) -> Path | None:
    current = Path(start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        candidate = path / TASKS_DIRNAME
        if candidate.is_dir():
            return candidate
    return None


def require_tasks_dir(start: Path | None = None) -> Path:
    tasks_dir = find_tasks_dir(start)
    if tasks_dir is None:
        raise TasksNotInitializedError(
            "No .tasks directory found. Run 'task init' in your project root."
        )
    return tasks_dir


def load_project_config(tasks_dir: Path) -> dict:
    config_path = tasks_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {
            "db_type": DEFAULT_DB_TYPE,
            "sqlite_file": DEFAULT_SQLITE_FILENAME,
            "json_file": DEFAULT_JSON_FILENAME,
            "backup_dir": DEFAULT_BACKUP_DIRNAME,
        }

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "db_type": str(data.get("db_type", DEFAULT_DB_TYPE)).strip().lower() or DEFAULT_DB_TYPE,
        "sqlite_file": str(data.get("sqlite_file", DEFAULT_SQLITE_FILENAME)).strip() or DEFAULT_SQLITE_FILENAME,
        "json_file": str(data.get("json_file", DEFAULT_JSON_FILENAME)).strip() or DEFAULT_JSON_FILENAME,
        "backup_dir": str(data.get("backup_dir", DEFAULT_BACKUP_DIRNAME)).strip() or DEFAULT_BACKUP_DIRNAME,
    }


def save_project_config(tasks_dir: Path, config: dict) -> Path:
    config_path = tasks_dir / CONFIG_FILENAME
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def get_paths(start: Path | None = None) -> dict[str, Path | str]:
    tasks_dir = require_tasks_dir(start)
    config = load_project_config(tasks_dir)
    db_type = config["db_type"]
    if db_type not in {"sqlite", "json"}:
        raise TasksConfigError("db_type must be 'sqlite' or 'json'")

    sqlite_path = tasks_dir / config["sqlite_file"]
    json_path = tasks_dir / config["json_file"]
    backup_dir = tasks_dir / config["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)

    return {
        "tasks_dir": tasks_dir,
        "db_type": db_type,
        "sqlite_path": sqlite_path,
        "json_path": json_path,
        "backup_dir": backup_dir,
        "config_path": tasks_dir / CONFIG_FILENAME,
    }


def init_project(start: Path | None = None, db_type: str | None = None) -> dict[str, Path | str]:
    root = Path(start or Path.cwd()).resolve()
    tasks_dir = root / TASKS_DIRNAME
    tasks_dir.mkdir(parents=True, exist_ok=True)

    chosen_db_type = (db_type or DEFAULT_DB_TYPE).strip().lower()
    if chosen_db_type not in {"sqlite", "json"}:
        raise TasksConfigError("db_type must be 'sqlite' or 'json'")

    config = {
        "db_type": chosen_db_type,
        "sqlite_file": DEFAULT_SQLITE_FILENAME,
        "json_file": DEFAULT_JSON_FILENAME,
        "backup_dir": DEFAULT_BACKUP_DIRNAME,
    }
    save_project_config(tasks_dir, config)

    if chosen_db_type == "json":
        json_path = tasks_dir / DEFAULT_JSON_FILENAME
        if not json_path.exists():
            json_path.write_text("[]\n", encoding="utf-8")
    else:
        sqlite_path = tasks_dir / DEFAULT_SQLITE_FILENAME
        sqlite_path.touch(exist_ok=True)

    return get_paths(root)
