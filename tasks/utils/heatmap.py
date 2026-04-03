from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Iterable

from tasks.models import Task


LEVELS = ["  ", "░░", "▒▒", "▓▓", "██"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CELL_WIDTH = 3
ROW_PREFIX = "    "


def render_heatmap(tasks: Iterable[Task], mode: str = "completed") -> str:
    if mode not in {"completed", "due"}:
        raise ValueError("mode must be 'completed' or 'due'")

    today = date.today()
    start_month = _month_start(today, months_back=2)
    start = start_month - timedelta(days=start_month.weekday())
    this_monday = today - timedelta(days=today.weekday())
    week_starts = []
    current = start
    while current <= this_monday:
        week_starts.append(current)
        current += timedelta(weeks=1)

    counts = Counter()
    for task in tasks:
        day = _task_day(task, mode)
        if day is None or day < start or day > today:
            continue
        counts[day] += 1

    max_count = max(counts.values(), default=0)

    lines = [f"{'Completed' if mode == 'completed' else 'Due'} Activity Heatmap", ""]
    lines.append(_render_month_row(week_starts, today))

    for weekday in range(7):
        row = f"{DAYS[weekday]:<3} "
        for week_start in week_starts:
            current_day = week_start + timedelta(days=weekday)
            if current_day < start_month or current_day > today:
                cell = "  "
            else:
                cell = LEVELS[_level(counts.get(current_day, 0), max_count)]
            row += f"{cell} "
        lines.append(row.rstrip())

    lines.append("")
    lines.append("Less " + " ".join(LEVELS) + " More")
    return "\n".join(lines)


def _render_month_row(week_starts: list[date], today: date) -> str:
    width = len(ROW_PREFIX) + (len(week_starts) * CELL_WIDTH)
    chars = [" "] * width
    chars[:len(ROW_PREFIX)] = list(ROW_PREFIX)

    last_label_end = -1
    prev_month = None

    for index, week_start in enumerate(week_starts):
        month_counts = Counter()
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            if day <= today:
                month_counts[day.month] += 1
        if not month_counts:
            continue

        label_month = month_counts.most_common(1)[0][0]
        if label_month == prev_month:
            continue

        month_name = date(today.year, label_month, 1).strftime("%b")
        pos = len(ROW_PREFIX) + (index * CELL_WIDTH)

        # Skip this label if it would run into the previous one.
        if pos <= last_label_end + 1:
            continue

        for i, ch in enumerate(month_name):
            if pos + i < len(chars):
                chars[pos + i] = ch

        last_label_end = pos + len(month_name) - 1
        prev_month = label_month

    return "".join(chars).rstrip()


def _month_start(day: date, months_back: int) -> date:
    year = day.year
    month = day.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _task_day(task: Task, mode: str) -> date | None:
    raw = task.completed_at if mode == "completed" else task.due_date
    if not raw:
        return None
    if mode == "completed":
        return datetime.fromisoformat(raw).date()
    return date.fromisoformat(raw)


def _level(count: int, max_count: int) -> int:
    if count <= 0 or max_count <= 0:
        return 0
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4