  # Task Pulse

  A local-first console task manager for software projects.

  Task Pulse gives each project its own task workspace, supports priorities, due dates, notes, bulk actions, overdue/upcoming views, heatmaps, imports from analysis tools,
  Git-based task creation, and portable JSON/CSV export for team sharing. Note: this is experimental and there may still be bugs that need to be worked out until it is stable.


  ## Features

  - Local per-project task storage
  - Priority scoring with impact, frequency, risk, and effort
  - Due dates
  - Notes on tasks
  - Search and filtering by status, tag, and query text
  - Bulk completion: `task done 4 5 6`
  - Workflow commands: `show`, `open`, `note`, `close`, `reopen`
  - Overdue and upcoming views
  - GitHub-style terminal heatmap
  - Imports from:
    - Larastan / PHPStan JSON
    - PHPUnit coverage XML
    - Git TODO / FIXME comments
    - Recent Git commits
    - Changed files
    - Current branch name
  - Portable export/import:
    - JSON
    - CSV

  ## Install

  ### 1. Clone the repo

  ```bash
  git clone https://github.com/trafficinc/task-pulse.git
  cd task-pulse

  ### 2. Create a virtual environment

  macOS / Linux:

  python3 -m venv .venv
  source .venv/bin/activate

  Windows PowerShell:

  py -3 -m venv .venv
  .venv\Scripts\Activate.ps1

  ### 3. Install the CLI

  Editable install:

  python -m pip install -e .

  Or install dependencies only:

  python -m pip install -r requirements.txt

  ### 4. Verify installation

  task help

  ## Quick Start

  Initialize task storage in the current project:

  task init

  Add some tasks:

  task add "Refactor auth middleware" --impact 5 --risk 4 --tag backend
  task add "Ship billing fix" --due-date 2026-04-15 --tag billing
  task list

  ## Common Commands

  ### Add and list

  task add "Fix login bug" --impact 5 --risk 4 --tag auth
  task list
  task list --status not_started
  task list --tag backend
  task list --query billing

  ### Workflow

  task show 1
  task open 1
  task note 1 "Need to confirm edge cases before merge"
  task note-edit 1 1 "Need to confirm edge cases with QA before merge"
  task note-delete 1 1
  task start 1
  task done 1
  task done 4 5 6
  task close 2
  task reopen 2
  task edit 1 --due-date 2026-04-20
  task edit 1 --clear-due-date

  ### Due dates

  task overdue
  task overdue --tag backend
  task upcoming
  task upcoming --days 14
  task upcoming --query auth

  ### Heatmap

  task heatmap
  task heatmap --mode due
  task heatmap --tag backend
  task heatmap --query billing

  ## Imports

  ### Larastan / PHPStan

  task import-larastan larastan.json

  ### PHPUnit coverage

  task import-coverage coverage.xml

  ### Git-based imports

  Import TODO / FIXME comments from tracked files:

  task import-git-todos
  task import-git-todos --pattern "TODO|FIXME|HACK"

  Import recent commits as review tasks:

  task import-git-commits
  task import-git-commits --count 20

  Import changed files from git status:

  task import-git-changes

  Import a task from the current branch name:

  task import-git-branch

  ## Export and Import Tasks

  Use portable exports to share tasks across machines or commit them to Git.

  ### Export to JSON

  task export shared/tasks.json

  ### Export to CSV

  task export shared/tasks.csv

  ### Import from JSON

  task import shared/tasks.json

  ### Import from CSV

  task import shared/tasks.csv

  JSON is the better format if you want to preserve notes cleanly in Git.

  ## Team Workflow

  Recommended setup:

  - Do not commit the live .tasks/ runtime directory (git ignore it)
  - Commit a shared task export instead, for example:
      - shared/tasks.json

  Typical team flow:

  task init
  task import shared/tasks.json

  After making changes to tasks, refresh the shared export:

  task export shared/tasks.json

  Then commit the updated shared task file.

  ## Notes

  - Task storage is local to each project via a .tasks/ directory.
  - Commands search upward for .tasks/, similar to Git.
  - Portable exports are intended for sharing and versioning.
  - Git import commands require the project to be inside a Git repository.

  ## Help

  General help:

  task help

  Single-command help:

  task help add
  task help heatmap
  task help import-git-todos