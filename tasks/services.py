import csv
import json
import re
import subprocess
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

from tasks.config import TasksNotInitializedError, get_paths, init_project
from tasks.models import Task, VALID_STATUSES, utc_now_iso
from tasks.storage.json_store import JSONStorage
from tasks.storage.sqlite import SQLiteStorage

_storage_instance = None
_storage_key = None


def reset_storage_cache() -> None:
    global _storage_instance, _storage_key
    _storage_instance = None
    _storage_key = None


def get_storage():
    global _storage_instance, _storage_key
    paths = get_paths()
    current_key = (paths["db_type"], str(paths["json_path"]), str(paths["sqlite_path"]))

    if _storage_instance is None or _storage_key != current_key:
        if paths["db_type"] == "json":
            _storage_instance = JSONStorage(paths["json_path"])
        else:
            _storage_instance = SQLiteStorage(paths["sqlite_path"])
        _storage_key = current_key
    return _storage_instance


def init_tasks_project(db_type: str | None = None) -> dict[str, Path | str]:
    result = init_project(db_type=db_type)
    reset_storage_cache()
    # create backing store now
    get_storage()
    return result


def calc_priority(impact: int, frequency: int, risk: int, effort: int) -> float:
    validate_score("impact", impact)
    validate_score("frequency", frequency)
    validate_score("risk", risk)
    validate_score("effort", effort)
    return round(((impact + frequency + risk) / 3) - (effort * 0.25), 2)


def validate_score(name: str, value: int) -> None:
    if value not in {1, 2, 3, 4, 5}:
        raise ValueError(f"{name} must be between 1 and 5")


def validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        allowed = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(f"status must be one of: {allowed}")


def validate_title(title: str) -> None:
    if not title or not title.strip():
        raise ValueError("title cannot be blank")


def validate_due_date(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    date.fromisoformat(value)
    return value


def matches_query(task: Task, query: str) -> bool:
    haystack = f"{task.title} {task.tag} {' '.join(task.notes or [])}".lower()
    return query.lower() in haystack


def next_task_id() -> int:
    tasks = get_storage().list()
    return max([t.id for t in tasks], default=0) + 1


def _import_task(title: str, tag: str, notes: list[str] | None = None, impact: int = 3, frequency: int = 2,
                 risk: int = 2, effort: int = 2) -> bool:
    store = get_storage()
    existing = {(t.title, t.tag) for t in store.list()}
    if (title, tag) in existing:
        return False

    task = Task(
        id=next_task_id(),
        title=title,
        status="not_started",
        impact=impact,
        frequency=frequency,
        risk=risk,
        effort=effort,
        priority=calc_priority(impact, frequency, risk, effort),
        tag=tag,
        due_date=None,
        created_at=utc_now_iso(),
        completed_at=None,
        notes=list(notes or []),
    )
    store.add(task)
    return True


def _portable_task(task: Task) -> dict:
    return {
        "title": task.title,
        "status": task.status,
        "impact": task.impact,
        "frequency": task.frequency,
        "risk": task.risk,
        "effort": task.effort,
        "priority": task.priority,
        "tag": task.tag,
        "due_date": task.due_date,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "notes": list(task.notes or []),
    }


def _infer_portable_format(path: Path, fmt: str | None) -> str:
    if fmt:
        fmt = fmt.strip().lower()
    else:
        suffix = path.suffix.lower()
        if suffix == ".json":
            fmt = "json"
        elif suffix == ".csv":
            fmt = "csv"
    if fmt not in {"json", "csv"}:
        raise ValueError("format must be 'json' or 'csv', or inferable from .json/.csv")
    return fmt


def export_tasks_file(dest_file: str, fmt: str | None = None) -> Path:
    dest = Path(dest_file)
    fmt = _infer_portable_format(dest, fmt)
    tasks = [_portable_task(task) for task in get_storage().list()]
    dest.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        payload = {
            "version": 1,
            "exported_at": utc_now_iso(),
            "tasks": tasks,
        }
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return dest

    fieldnames = [
        "title",
        "status",
        "impact",
        "frequency",
        "risk",
        "effort",
        "priority",
        "tag",
        "due_date",
        "created_at",
        "completed_at",
        "notes",
    ]
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            row = dict(task)
            row["notes"] = json.dumps(task["notes"])
            writer.writerow(row)
    return dest


def _portable_records_from_file(src: Path, fmt: str) -> list[dict]:
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")

    if fmt == "json":
        data = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            records = data.get("tasks", [])
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError("JSON import file must contain a task list")
        if not isinstance(records, list):
            raise ValueError("JSON import file must contain a task list")
        return records

    with src.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def import_tasks_file(src_file: str, fmt: str | None = None) -> int:
    src = Path(src_file)
    fmt = _infer_portable_format(src, fmt)
    records = _portable_records_from_file(src, fmt)

    store = get_storage()
    existing = {(task.title, task.tag) for task in store.list()}
    imported = 0

    for record in records:
        title = str(record.get("title", "")).strip()
        validate_title(title)
        tag = str(record.get("tag", "general")).strip() or "general"
        key = (title, tag)
        if key in existing:
            continue

        status = str(record.get("status", "not_started")).strip() or "not_started"
        validate_status(status)

        impact = int(record.get("impact", 3))
        frequency = int(record.get("frequency", 3))
        risk = int(record.get("risk", 3))
        effort = int(record.get("effort", 3))
        validate_score("impact", impact)
        validate_score("frequency", frequency)
        validate_score("risk", risk)
        validate_score("effort", effort)

        notes = record.get("notes", [])
        if isinstance(notes, str):
            notes = json.loads(notes) if notes.strip().startswith("[") else ([notes] if notes.strip() else [])
        elif notes is None:
            notes = []

        due_date = validate_due_date(record.get("due_date"))
        created_at = record.get("created_at") or utc_now_iso()
        completed_at = record.get("completed_at")
        if status == "done" and not completed_at:
            completed_at = utc_now_iso()
        if status != "done":
            completed_at = None

        task = Task(
            id=next_task_id(),
            title=title,
            status=status,
            impact=impact,
            frequency=frequency,
            risk=risk,
            effort=effort,
            priority=calc_priority(impact, frequency, risk, effort),
            tag=tag,
            due_date=due_date,
            created_at=created_at,
            completed_at=completed_at,
            notes=list(notes),
        )
        store.add(task)
        existing.add(key)
        imported += 1

    return imported


def git_repo_root() -> Path:
    project_root = get_paths()["tasks_dir"].parent
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ValueError("Current project is not inside a Git repository") from exc
    return Path(result.stdout.strip())


def git_output(*args: str) -> str:
    repo_root = git_repo_root()
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "git command failed"
        raise ValueError(stderr) from exc
    return result.stdout


def add_task(
    title: str,
    impact: int,
    frequency: int,
    risk: int,
    effort: int,
    tag: str = "general",
    due_date: str | None = None,
) -> Task:
    validate_title(title)
    due_date = validate_due_date(due_date)
    priority = calc_priority(impact, frequency, risk, effort)
    task = Task(
        id=next_task_id(),
        title=title.strip(),
        status="not_started",
        impact=impact,
        frequency=frequency,
        risk=risk,
        effort=effort,
        priority=priority,
        tag=(tag or "general").strip(),
        due_date=due_date,
        created_at=utc_now_iso(),
        completed_at=None,
        notes=[],
    )
    get_storage().add(task)
    return task


def list_tasks(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    query: Optional[str] = None,
) -> list[Task]:
    tasks = get_storage().list()
    if status:
        tasks = [t for t in tasks if t.status == status]
    if tag:
        tasks = [t for t in tasks if tag.lower() in t.tag.lower()]
    if query:
        tasks = [t for t in tasks if matches_query(t, query)]
    return tasks


def get_task(task_id: int) -> Optional[Task]:
    return get_storage().get(task_id)


def add_note(task_id: int, note: str) -> Optional[Task]:
    if not note or not note.strip():
        raise ValueError("note cannot be blank")

    store = get_storage()
    task = store.get(task_id)
    if not task:
        return None

    task.notes = list(task.notes or [])
    task.notes.append(note.strip())
    store.update(task)
    return task


def import_git_todo_tasks(pattern: str = r"TODO|FIXME") -> int:
    output = git_output("grep", "-nE", pattern, "--", ".")
    imported = 0

    for raw_line in output.splitlines():
        match = re.match(r"^(.*?):(\d+):(.*)$", raw_line)
        if not match:
            continue
        file_path, line_no, content = match.groups()
        title = f"Resolve TODO in {file_path}:{line_no}"
        notes = [content.strip(), f"Source: {file_path}:{line_no}"]
        if _import_task(title, "git-todo", notes=notes, impact=3, frequency=2, risk=2, effort=2):
            imported += 1
    return imported


def import_git_commit_tasks(count: int = 10) -> int:
    if count < 1:
        raise ValueError("count must be at least 1")

    output = git_output("log", f"-n{count}", "--pretty=format:%H%x09%s")
    imported = 0

    for raw_line in output.splitlines():
        if "\t" not in raw_line:
            continue
        sha, subject = raw_line.split("\t", 1)
        title = f"Review commit {sha[:7]}: {subject}"
        notes = [f"Commit: {sha}"]
        if _import_task(title, "git-commit", notes=notes, impact=3, frequency=1, risk=3, effort=2):
            imported += 1
    return imported


def import_git_changed_file_tasks() -> int:
    output = git_output("status", "--short")
    imported = 0

    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        status = raw_line[:2].strip() or "modified"
        file_path = raw_line[3:].strip()
        title = f"Review changed file: {file_path}"
        notes = [f"Git status: {status}", f"File: {file_path}"]
        if _import_task(title, "git-change", notes=notes, impact=3, frequency=2, risk=3, effort=2):
            imported += 1
    return imported


def import_git_branch_task() -> int:
    branch = git_output("branch", "--show-current").strip()
    if not branch:
        raise ValueError("Could not determine current branch")

    cleaned = branch.replace("-", " ").replace("_", " ").replace("/", " / ")
    title = f"Finish branch work: {cleaned}"
    notes = [f"Branch: {branch}"]
    return 1 if _import_task(title, "git-branch", notes=notes, impact=4, frequency=2, risk=3, effort=2) else 0


def edit_note(task_id: int, note_index: int, note: str) -> Optional[Task]:
    if not note or not note.strip():
        raise ValueError("note cannot be blank")
    if note_index < 1:
        raise ValueError("note index must be at least 1")

    store = get_storage()
    task = store.get(task_id)
    if not task:
        return None

    notes = list(task.notes or [])
    if note_index > len(notes):
        raise ValueError(f"note index out of range: {note_index}")

    notes[note_index - 1] = note.strip()
    task.notes = notes
    store.update(task)
    return task


def delete_note(task_id: int, note_index: int) -> Optional[Task]:
    if note_index < 1:
        raise ValueError("note index must be at least 1")

    store = get_storage()
    task = store.get(task_id)
    if not task:
        return None

    notes = list(task.notes or [])
    if note_index > len(notes):
        raise ValueError(f"note index out of range: {note_index}")

    del notes[note_index - 1]
    task.notes = notes
    store.update(task)
    return task


def update_status(task_id: int, status: str) -> Optional[Task]:
    validate_status(status)
    store = get_storage()
    task = store.get(task_id)
    if not task:
        return None

    task.status = status
    if status == "done":
        task.completed_at = utc_now_iso()
    else:
        task.completed_at = None

    store.update(task)
    return task


def delete_task(task_id: int) -> bool:
    return get_storage().delete(task_id)


def edit_task(
    task_id: int,
    title: str | None = None,
    impact: int | None = None,
    frequency: int | None = None,
    risk: int | None = None,
    effort: int | None = None,
    tag: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
) -> Optional[Task]:
    store = get_storage()
    task = store.get(task_id)
    if not task:
        return None

    if title is not None:
        validate_title(title)
        task.title = title.strip()
    if impact is not None:
        validate_score("impact", impact)
        task.impact = impact
    if frequency is not None:
        validate_score("frequency", frequency)
        task.frequency = frequency
    if risk is not None:
        validate_score("risk", risk)
        task.risk = risk
    if effort is not None:
        validate_score("effort", effort)
        task.effort = effort
    if tag is not None:
        task.tag = tag.strip() or "general"
    if due_date == "":
        task.due_date = None
    elif due_date is not None:
        task.due_date = validate_due_date(due_date)
    if status is not None:
        validate_status(status)
        task.status = status
        task.completed_at = utc_now_iso() if status == "done" else None

    task.priority = calc_priority(task.impact, task.frequency, task.risk, task.effort)
    store.update(task)
    return task


def next_task() -> Optional[Task]:
    tasks = [t for t in get_storage().list() if t.status != "done"]
    return tasks[0] if tasks else None


def overdue_tasks(tag: Optional[str] = None, query: Optional[str] = None) -> list[Task]:
    today = date.today()
    tasks = [
        task
        for task in get_storage().list()
        if task.status != "done"
        and task.due_date is not None
        and task.due_date_obj() is not None
        and task.due_date_obj() < today
    ]
    if tag:
        tasks = [t for t in tasks if tag.lower() in t.tag.lower()]
    if query:
        tasks = [t for t in tasks if matches_query(t, query)]
    return sorted(tasks, key=lambda t: (t.due_date_obj(), -t.priority, t.id))


def upcoming_tasks(days: int = 7, tag: Optional[str] = None, query: Optional[str] = None) -> list[Task]:
    if days < 1:
        raise ValueError("days must be at least 1")

    today = date.today()
    end_date = today.fromordinal(today.toordinal() + days)
    tasks = [
        task
        for task in get_storage().list()
        if task.status != "done"
        and task.due_date is not None
        and task.due_date_obj() is not None
        and today <= task.due_date_obj() <= end_date
    ]
    if tag:
        tasks = [t for t in tasks if tag.lower() in t.tag.lower()]
    if query:
        tasks = [t for t in tasks if matches_query(t, query)]
    return sorted(tasks, key=lambda t: (t.due_date_obj(), -t.priority, t.id))


def update_many_status(task_ids: list[int], status: str) -> tuple[list[Task], list[int]]:
    updated: list[Task] = []
    missing: list[int] = []
    for task_id in task_ids:
        task = update_status(task_id, status)
        if task is None:
            missing.append(task_id)
        else:
            updated.append(task)
    return updated, missing


def stats() -> dict:
    tasks = get_storage().list()
    total = len(tasks)
    by_status = defaultdict(int)
    by_tag = defaultdict(int)
    for task in tasks:
        by_status[task.status] += 1
        by_tag[task.tag] += 1
    avg_priority = round(sum(t.priority for t in tasks) / total, 2) if total else 0
    return {
        "total": total,
        "avg_priority": avg_priority,
        "by_status": dict(sorted(by_status.items())),
        "by_tag": dict(sorted(by_tag.items())),
    }


def backup(dest_file: str | None = None) -> Path:
    paths = get_paths()
    src = paths["json_path"] if paths["db_type"] == "json" else paths["sqlite_path"]
    if not src.exists():
        raise FileNotFoundError("No data file exists yet to back up")
    dest = Path(dest_file) if dest_file else paths["backup_dir"] / f"tasks_backup{src.suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def restore(src_file: str) -> Path:
    src = Path(src_file)
    if not src.exists():
        raise FileNotFoundError(f"Backup file not found: {src_file}")
    paths = get_paths()
    dest = paths["json_path"] if paths["db_type"] == "json" else paths["sqlite_path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    reset_storage_cache()
    return dest


def import_larastan_tasks(file: str = "larastan.json") -> int:
    path = Path(file)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file}")

    data = json.loads(path.read_text(encoding="utf-8"))
    store = get_storage()
    existing = {(t.title, t.tag) for t in store.list()}
    imported = 0

    for file_path, details in data.get("files", {}).items():
        for message in details.get("messages", []):
            title = f"Larastan: {file_path} - {message}"
            key = (title, "larastan")
            if key in existing:
                continue
            task = Task(
                id=next_task_id(),
                title=title,
                status="not_started",
                impact=4,
                frequency=3,
                risk=4,
                effort=2,
                priority=calc_priority(4, 3, 4, 2),
                tag="larastan",
                due_date=None,
                created_at=utc_now_iso(),
                completed_at=None,
                notes=[],
            )
            store.add(task)
            existing.add(key)
            imported += 1
    return imported


def import_coverage_tasks(file: str = "coverage.xml") -> int:
    path = Path(file)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file}")

    tree = ET.parse(path)
    root = tree.getroot()
    uncovered = defaultdict(list)

    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename", "unknown")
        for line in cls.findall("lines/line"):
            if int(line.attrib.get("count", 0)) == 0:
                uncovered[filename].append(int(line.attrib.get("num", 0)))

    store = get_storage()
    existing = {(t.title, t.tag) for t in store.list()}
    imported = 0

    for filename, lines in uncovered.items():
        title = f"Add test coverage: {filename} ({len(lines)} uncovered lines)"
        key = (title, "testing")
        if key in existing:
            continue
            task = Task(
            id=next_task_id(),
            title=title,
            status="not_started",
            impact=3,
            frequency=2,
            risk=3,
            effort=3,
            priority=calc_priority(3, 2, 3, 3),
                tag="testing",
                due_date=None,
                created_at=utc_now_iso(),
                completed_at=None,
                notes=[],
            )
        store.add(task)
        existing.add(key)
        imported += 1
    return imported
