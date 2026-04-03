from __future__ import annotations

import typer
from rich import print
from rich.panel import Panel
from rich.table import Table

from tasks.config import TasksConfigError, TasksNotInitializedError, get_paths
from tasks.services import (
    add_task,
    add_note,
    backup,
    delete_task,
    delete_note,
    edit_task,
    edit_note,
    export_tasks_file,
    get_task,
    git_repo_root,
    import_tasks_file,
    import_git_branch_task,
    import_git_changed_file_tasks,
    import_git_commit_tasks,
    import_git_todo_tasks,
    import_coverage_tasks,
    import_larastan_tasks,
    init_tasks_project,
    list_tasks,
    next_task,
    overdue_tasks,
    restore,
    stats,
    upcoming_tasks,
    update_many_status,
    update_status,
)
from tasks.utils.heatmap import render_heatmap

app = typer.Typer(help="Task priority CLI app")

HELP_TEXT = """
[bold cyan]Task Pulse[/bold cyan] - Local task CLI

[bold]Commands[/bold]

[green]task init[/green]
  Initialize a .tasks directory in the current project
  Options:
    --db-type [sqlite|json]

[green]task where[/green]
  Show the resolved .tasks project directory

[green]task add TITLE[/green]
  Add a task
  Options:
    --impact INTEGER      1..5
    --frequency INTEGER   1..5
    --risk INTEGER        1..5
    --effort INTEGER      1..5
    --tag TEXT
    --due-date YYYY-MM-DD

[green]task list[/green]
  List tasks
  Options:
    --status TEXT
    --tag TEXT
    --query, -q TEXT      Search by title or tag

[green]task start TASK_ID[/green]
  Mark task as started

[green]task show TASK_ID[/green]
  Show full task details

[green]task open TASK_ID[/green]
  Open a task in the console detail view

[green]task note TASK_ID "TEXT"[/green]
  Add a note to a task

[green]task note-edit TASK_ID NOTE_INDEX "TEXT"[/green]
  Edit a task note

[green]task note-delete TASK_ID NOTE_INDEX[/green]
  Delete a task note

[green]task done TASK_ID [TASK_ID ...][/green]
  Mark one or more tasks as done

[green]task close TASK_ID[/green]
  Mark task as done

[green]task reopen TASK_ID[/green]
  Reopen a completed task

[green]task next[/green]
  Show the next highest-priority unfinished task

[green]task overdue[/green]
  Show unfinished tasks with due dates before today
  Options:
    --tag TEXT
    --query, -q TEXT      Search by title, tag, or notes

[green]task upcoming[/green]
  Show unfinished tasks due soon
  Options:
    --days INTEGER
    --tag TEXT
    --query, -q TEXT      Search by title, tag, or notes

[green]task heatmap[/green]
  Render a GitHub-style calendar heatmap
  Options:
    --status TEXT
    --tag TEXT
    --query, -q TEXT      Search by title or tag
    --mode [completed|due]

[green]task edit TASK_ID[/green]
  Edit a task
  Options:
    --title TEXT
    --impact INTEGER      1..5
    --frequency INTEGER   1..5
    --risk INTEGER        1..5
    --effort INTEGER      1..5
    --tag TEXT
    --status TEXT
    --due-date YYYY-MM-DD
    --clear-due-date

[green]task delete TASK_ID[/green]
  Delete a task

[green]task stats[/green]
  Show task statistics

[green]task backup [DEST][/green]
  Back up the current project task database or JSON file

[green]task restore SRC[/green]
  Restore from a backup file into the current project

[green]task export DEST[/green]
  Export tasks to a portable JSON or CSV file
  Options:
    --format [json|csv]

[green]task import SRC[/green]
  Import tasks from a portable JSON or CSV file
  Options:
    --format [json|csv]

[green]task import-larastan [FILE][/green]
  Import tasks from Larastan/PHPStan JSON
  Default file:
    larastan.json

[green]task import-coverage [FILE][/green]
  Import tasks from PHPUnit coverage XML
  Default file:
    coverage.xml

[green]task import-git-todos[/green]
  Import tasks from TODO/FIXME comments tracked by Git
  Options:
    --pattern TEXT

[green]task import-git-commits[/green]
  Import tasks from recent Git commits
  Options:
    --count INTEGER

[green]task import-git-changes[/green]
  Import tasks from changed files in git status

[green]task import-git-branch[/green]
  Import a task from the current branch name

[bold]Notes[/bold]
  - Commands search upward for .tasks, similar to Git.
  - Use [green]task --help[/green] for Typer's generated help.
  - Use [green]task help[/green] for this condensed command reference.
""".strip()

COMMAND_HELP = {
    "init": """
[green]task init[/green]
Initialize a .tasks directory in the current project

Options:
  --db-type [sqlite|json]
""".strip(),
    "where": """
[green]task where[/green]
Show the resolved .tasks project directory
""".strip(),
    "add": """
[green]task add TITLE[/green]
Add a task

Options:
  --impact INTEGER      1..5
  --frequency INTEGER   1..5
  --risk INTEGER        1..5
  --effort INTEGER      1..5
  --tag TEXT
  --due-date YYYY-MM-DD
""".strip(),
    "list": """
[green]task list[/green]
List tasks

Options:
  --status TEXT
  --tag TEXT
  --query, -q TEXT      Search by title or tag
""".strip(),
    "start": """
[green]task start TASK_ID[/green]
Mark task as started
""".strip(),
    "show": """
[green]task show TASK_ID[/green]
Show full task details
""".strip(),
    "open": """
[green]task open TASK_ID[/green]
Open a task in the console detail view
""".strip(),
    "note": """
[green]task note TASK_ID "TEXT"[/green]
Add a note to a task
""".strip(),
    "note-edit": """
[green]task note-edit TASK_ID NOTE_INDEX "TEXT"[/green]
Edit a task note
""".strip(),
    "note-delete": """
[green]task note-delete TASK_ID NOTE_INDEX[/green]
Delete a task note
""".strip(),
    "done": """
[green]task done TASK_ID [TASK_ID ...][/green]
Mark one or more tasks as done
""".strip(),
    "close": """
[green]task close TASK_ID[/green]
Mark task as done
""".strip(),
    "reopen": """
[green]task reopen TASK_ID[/green]
Reopen a completed task
""".strip(),
    "next": """
[green]task next[/green]
Show the next highest-priority unfinished task
""".strip(),
    "overdue": """
[green]task overdue[/green]
Show unfinished tasks with due dates before today

Options:
  --tag TEXT
  --query, -q TEXT      Search by title, tag, or notes
""".strip(),
    "upcoming": """
[green]task upcoming[/green]
Show unfinished tasks due soon

Options:
  --days INTEGER
  --tag TEXT
  --query, -q TEXT      Search by title, tag, or notes
""".strip(),
    "heatmap": """
[green]task heatmap[/green]
Render a GitHub-style calendar heatmap

Options:
  --status TEXT
  --tag TEXT
  --query, -q TEXT
  --mode [completed|due]
""".strip(),
    "edit": """
[green]task edit TASK_ID[/green]
Edit a task

Options:
  --title TEXT
  --impact INTEGER      1..5
  --frequency INTEGER   1..5
  --risk INTEGER        1..5
  --effort INTEGER      1..5
  --tag TEXT
  --status TEXT
  --due-date YYYY-MM-DD
  --clear-due-date
""".strip(),
    "delete": """
[green]task delete TASK_ID[/green]
Delete a task
""".strip(),
    "stats": """
[green]task stats[/green]
Show task statistics
""".strip(),
    "backup": """
[green]task backup [DEST][/green]
Back up the current project task database or JSON file
""".strip(),
    "restore": """
[green]task restore SRC[/green]
Restore from a backup file into the current project
""".strip(),
    "export": """
[green]task export DEST[/green]
Export tasks to a portable JSON or CSV file

Options:
  --format [json|csv]
""".strip(),
    "import": """
[green]task import SRC[/green]
Import tasks from a portable JSON or CSV file

Options:
  --format [json|csv]
""".strip(),
    "import-larastan": """
[green]task import-larastan [FILE][/green]
Import tasks from Larastan/PHPStan JSON

Default file:
  larastan.json
""".strip(),
    "import-coverage": """
[green]task import-coverage [FILE][/green]
Import tasks from PHPUnit coverage XML

Default file:
  coverage.xml
""".strip(),
    "import-git-todos": """
[green]task import-git-todos[/green]
Import tasks from TODO/FIXME comments tracked by Git

Options:
  --pattern TEXT
""".strip(),
    "import-git-commits": """
[green]task import-git-commits[/green]
Import tasks from recent Git commits

Options:
  --count INTEGER
""".strip(),
    "import-git-changes": """
[green]task import-git-changes[/green]
Import tasks from changed files in git status
""".strip(),
    "import-git-branch": """
[green]task import-git-branch[/green]
Import a task from the current branch name
""".strip(),
}


def run_guarded(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except TasksNotInitializedError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except (TasksConfigError, ValueError, FileNotFoundError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@app.command()
def init(db_type: str = typer.Option(None, help="sqlite or json")):
    """Initialize a .tasks directory in the current project."""
    paths = run_guarded(init_tasks_project, db_type)
    print(f"[green]Initialized[/green] {paths['tasks_dir']}")
    print(f"Storage: {paths['db_type']} -> {paths['sqlite_path'] if paths['db_type'] == 'sqlite' else paths['json_path']}")


@app.command()
def where():
    """Show the resolved .tasks project directory."""
    paths = run_guarded(get_paths)
    print(f"[bold].tasks[/bold]: {paths['tasks_dir']}")
    print(f"[bold]Config[/bold]: {paths['config_path']}")
    print(f"[bold]Storage[/bold]: {paths['sqlite_path'] if paths['db_type'] == 'sqlite' else paths['json_path']}")
    try:
        print(f"[bold]Git Root[/bold]: {run_guarded(git_repo_root)}")
    except typer.Exit:
        pass


@app.command("help")
def help_cmd(command: str = typer.Argument(None)):
    """Show command help."""
    if command:
        text = COMMAND_HELP.get(command)
        if not text:
            print(f"[red]Unknown command:[/red] {command}")
            print("Run [green]task help[/green] to see all available commands.")
            raise typer.Exit(code=1)
        print(Panel.fit(text, title=f"Task Help: {command}", border_style="cyan"))
        return

    print(Panel.fit(HELP_TEXT, title="Task Help", border_style="cyan"))


@app.command()
def add(
    title: str,
    impact: int = typer.Option(3, min=1, max=5),
    frequency: int = typer.Option(3, min=1, max=5),
    risk: int = typer.Option(3, min=1, max=5),
    effort: int = typer.Option(3, min=1, max=5),
    tag: str = typer.Option("general"),
    due_date: str = typer.Option(None, "--due-date", help="ISO date: YYYY-MM-DD"),
):
    """Add a task."""
    task = run_guarded(add_task, title, impact, frequency, risk, effort, tag, due_date)
    print(f"[green]Added task {task.id}[/green] - {task.title}")


@app.command(name="list")
def list_cmd(
    status: str = typer.Option(None),
    tag: str = typer.Option(None),
    query: str = typer.Option(None, "--query", "-q", help="Search title or tag"),
):
    """List tasks."""
    tasks = run_guarded(list_tasks, status, tag, query)
    if not tasks:
        print("[yellow]No tasks found[/yellow]")
        return

    table = Table(title="Tasks")
    table.add_column("ID", justify="right")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Priority", justify="right")
    table.add_column("Tag")
    table.add_column("Due")

    for task in tasks:
        table.add_row(
            str(task.id),
            task.title,
            task.status,
            f"{task.priority:.2f}",
            task.tag,
            task.due_date or "-",
        )
    print(table)


def _render_task_detail(task):
    lines = [
        f"[bold]ID:[/bold] {task.id}",
        f"[bold]Title:[/bold] {task.title}",
        f"[bold]Status:[/bold] {task.status}",
        f"[bold]Priority:[/bold] {task.priority:.2f}",
        f"[bold]Tag:[/bold] {task.tag}",
        f"[bold]Due:[/bold] {task.due_date or '-'}",
        f"[bold]Created:[/bold] {task.created_at or '-'}",
        f"[bold]Completed:[/bold] {task.completed_at or '-'}",
        "[bold]Notes:[/bold]",
    ]
    notes = task.notes or []
    if notes:
        for index, note in enumerate(notes, start=1):
            lines.append(f"  {index}. {note}")
    else:
        lines.append("  -")
    print(Panel.fit("\n".join(lines), title=f"Task #{task.id}", border_style="cyan"))


def _render_task_table(tasks, title: str):
    if not tasks:
        print("[yellow]No tasks found[/yellow]")
        return

    table = Table(title=title)
    table.add_column("ID", justify="right")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Priority", justify="right")
    table.add_column("Tag")
    table.add_column("Due")

    for task in tasks:
        table.add_row(
            str(task.id),
            task.title,
            task.status,
            f"{task.priority:.2f}",
            task.tag,
            task.due_date or "-",
        )
    print(table)


@app.command()
def show(task_id: int):
    """Show full task details."""
    task = run_guarded(get_task, task_id)
    if not task:
        print(f"[red]Task {task_id} not found[/red]")
        raise typer.Exit(code=1)
    _render_task_detail(task)


@app.command()
def open(task_id: int):
    """Open a task in the console detail view."""
    show(task_id)


@app.command()
def note(task_id: int, text: str):
    """Add a note to a task."""
    task = run_guarded(add_note, task_id, text)
    if not task:
        print(f"[red]Task {task_id} not found[/red]")
        raise typer.Exit(code=1)
    print(f"[green]Added note to task {task_id}[/green]")


@app.command("note-edit")
def note_edit(task_id: int, note_index: int, text: str):
    """Edit a task note."""
    task = run_guarded(edit_note, task_id, note_index, text)
    if not task:
        print(f"[red]Task {task_id} not found[/red]")
        raise typer.Exit(code=1)
    print(f"[yellow]Updated note {note_index} on task {task_id}[/yellow]")


@app.command("note-delete")
def note_delete(task_id: int, note_index: int):
    """Delete a task note."""
    task = run_guarded(delete_note, task_id, note_index)
    if not task:
        print(f"[red]Task {task_id} not found[/red]")
        raise typer.Exit(code=1)
    print(f"[red]Deleted note {note_index} from task {task_id}[/red]")


@app.command()
def start(task_id: int):
    """Mark task as started."""
    task = run_guarded(update_status, task_id, "started")
    if task:
        print(f"[yellow]Started task {task_id}[/yellow]")
    else:
        print(f"[red]Task {task_id} not found[/red]")


@app.command()
def done(task_ids: list[int] = typer.Argument(..., help="One or more task IDs")):
    """Mark one or more tasks as done."""
    updated, missing = run_guarded(update_many_status, task_ids, "done")
    for task in updated:
        print(f"[green]Completed task {task.id}[/green]")
    for task_id in missing:
        print(f"[red]Task {task_id} not found[/red]")
    if missing:
        raise typer.Exit(code=1)


@app.command()
def close(task_id: int):
    """Mark task as done."""
    task = run_guarded(update_status, task_id, "done")
    if task:
        print(f"[green]Closed task {task_id}[/green]")
    else:
        print(f"[red]Task {task_id} not found[/red]")


@app.command()
def reopen(task_id: int):
    """Reopen a completed task."""
    task = run_guarded(update_status, task_id, "not_started")
    if task:
        print(f"[yellow]Reopened task {task_id}[/yellow]")
    else:
        print(f"[red]Task {task_id} not found[/red]")


@app.command()
def next():
    """Show the next highest-priority unfinished task."""
    task = run_guarded(next_task)
    if not task:
        print("[yellow]No unfinished tasks found[/yellow]")
        return
    print(f"[bold cyan]Next:[/bold cyan] #{task.id} {task.title} ({task.priority:.2f})")


@app.command()
def overdue(
    tag: str = typer.Option(None),
    query: str = typer.Option(None, "--query", "-q", help="Search title, tag, or notes"),
):
    """Show unfinished tasks with due dates before today."""
    _render_task_table(run_guarded(overdue_tasks, tag, query), "Overdue Tasks")


@app.command()
def upcoming(
    days: int = typer.Option(7, min=1, help="Days ahead to include"),
    tag: str = typer.Option(None),
    query: str = typer.Option(None, "--query", "-q", help="Search title, tag, or notes"),
):
    """Show unfinished tasks due soon."""
    _render_task_table(run_guarded(upcoming_tasks, days, tag, query), f"Upcoming Tasks ({days} days)")


@app.command()
def heatmap(
    tag: str = typer.Option(None),
    query: str = typer.Option(None, "--query", "-q", help="Search title or tag"),
    status: str = typer.Option(None),
    mode: str = typer.Option("completed", help="completed or due"),
):
    """Render a GitHub-style calendar heatmap for the last 3 months."""
    tasks = run_guarded(list_tasks, status, tag, query)
    print(render_heatmap(tasks, mode=mode))


@app.command()
def delete(task_id: int):
    """Delete a task."""
    if run_guarded(delete_task, task_id):
        print(f"[red]Deleted task {task_id}[/red]")
    else:
        print(f"[red]Task {task_id} not found[/red]")


@app.command()
def edit(
    task_id: int,
    title: str = typer.Option(None),
    impact: int = typer.Option(None, min=1, max=5),
    frequency: int = typer.Option(None, min=1, max=5),
    risk: int = typer.Option(None, min=1, max=5),
    effort: int = typer.Option(None, min=1, max=5),
    tag: str = typer.Option(None),
    status: str = typer.Option(None),
    due_date: str = typer.Option(None, "--due-date", help="ISO date: YYYY-MM-DD"),
    clear_due_date: bool = typer.Option(False, "--clear-due-date", help="Remove the due date"),
):
    """Edit a task."""
    if due_date is not None and clear_due_date:
        raise typer.BadParameter("Use either --due-date or --clear-due-date, not both.")

    due_date_update = "" if clear_due_date else due_date

    task = run_guarded(
        edit_task,
        task_id,
        title,
        impact,
        frequency,
        risk,
        effort,
        tag,
        status,
        due_date_update,
    )
    if task:
        print(f"[yellow]Updated task {task_id}[/yellow]")
    else:
        print("[red]Task not found[/red]")


@app.command()
def backup_data(dest: str = typer.Argument(None)):
    """Back up the current project task database or JSON file."""
    path = run_guarded(backup, dest)
    print(f"[green]Backup created:[/green] {path}")


@app.command()
def restore_data(src: str):
    """Restore from a backup file into the current project."""
    path = run_guarded(restore, src)
    print(f"[green]Restored data to:[/green] {path}")


@app.command("export")
def export_cmd(
    dest: str = typer.Argument(..., help="Destination .json or .csv file"),
    format: str = typer.Option(None, "--format", help="json or csv"),
):
    """Export tasks to a portable JSON or CSV file."""
    path = run_guarded(export_tasks_file, dest, format)
    print(f"[green]Exported tasks to:[/green] {path}")


@app.command("import")
def import_cmd(
    src: str = typer.Argument(..., help="Source .json or .csv file"),
    format: str = typer.Option(None, "--format", help="json or csv"),
):
    """Import tasks from a portable JSON or CSV file."""
    count = run_guarded(import_tasks_file, src, format)
    print(f"[green]Imported {count} tasks[/green]")


@app.command()
def stats_cmd():
    """Show task statistics."""
    data = run_guarded(stats)
    print(f"[bold]Total tasks:[/bold] {data['total']}")
    print(f"[bold]Average priority:[/bold] {data['avg_priority']}")
    print("[bold]By status:[/bold]")
    for key, value in data["by_status"].items():
        print(f"  - {key}: {value}")
    print("[bold]By tag:[/bold]")
    for key, value in data["by_tag"].items():
        print(f"  - {key}: {value}")


@app.command("import-larastan")
def import_larastan_cmd(
    file: str = typer.Argument("larastan.json", help="Path to Larastan/PHPStan JSON file"),
):
    """Import tasks from Larastan/PHPStan JSON."""
    count = run_guarded(import_larastan_tasks, file)
    print(f"[green]Imported {count} Larastan issues[/green]")


@app.command("import-coverage")
def import_coverage_cmd(
    file: str = typer.Argument("coverage.xml", help="Path to PHPUnit coverage XML file"),
):
    """Import tasks from PHPUnit coverage XML."""
    count = run_guarded(import_coverage_tasks, file)
    print(f"[green]Imported {count} coverage tasks[/green]")


@app.command("import-git-todos")
def import_git_todos_cmd(pattern: str = typer.Option(r"TODO|FIXME", help="Regex for comments to import")):
    """Import tasks from TODO/FIXME comments tracked by Git."""
    count = run_guarded(import_git_todo_tasks, pattern)
    print(f"[green]Imported {count} Git TODO tasks[/green]")


@app.command("import-git-commits")
def import_git_commits_cmd(count: int = typer.Option(10, min=1, help="Number of recent commits to inspect")):
    """Import tasks from recent Git commits."""
    imported = run_guarded(import_git_commit_tasks, count)
    print(f"[green]Imported {imported} Git commit tasks[/green]")


@app.command("import-git-changes")
def import_git_changes_cmd():
    """Import tasks from changed files in git status."""
    count = run_guarded(import_git_changed_file_tasks)
    print(f"[green]Imported {count} Git changed-file tasks[/green]")


@app.command("import-git-branch")
def import_git_branch_cmd():
    """Import a task from the current branch name."""
    count = run_guarded(import_git_branch_task)
    print(f"[green]Imported {count} Git branch task[/green]")


@app.command("backup")
def backup_alias(dest: str = typer.Argument(None)):
    backup_data(dest)


@app.command("restore")
def restore_alias(src: str):
    restore_data(src)


@app.command("stats")
def stats_alias():
    stats_cmd()


if __name__ == "__main__":
    app()
