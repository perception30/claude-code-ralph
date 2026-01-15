"""State persistence for Ralph CLI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Project, Phase, Task, TaskStatus, Iteration


class StateStore:
    """Manages persistent state storage for Ralph projects."""

    DEFAULT_STATE_DIR = ".ralph"
    DEFAULT_STATE_FILE = "state.json"

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir).resolve()
        self.state_dir = self.working_dir / self.DEFAULT_STATE_DIR
        self.state_file = self.state_dir / self.DEFAULT_STATE_FILE
        self._project: Optional[Project] = None

    @property
    def project(self) -> Optional[Project]:
        """Get the current project, loading from disk if needed."""
        if self._project is None:
            self._project = self.load()
        return self._project

    def ensure_state_dir(self) -> Path:
        """Ensure the state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        return self.state_dir

    def exists(self) -> bool:
        """Check if state file exists."""
        return self.state_file.exists()

    def load(self) -> Optional[Project]:
        """Load project state from disk."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            self._project = Project.from_dict(data)
            return self._project
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log error but don't crash - return None for fresh start
            print(f"Warning: Could not load state file: {e}")
            return None

    def save(self, project: Optional[Project] = None) -> None:
        """Save project state to disk."""
        if project is not None:
            self._project = project

        if self._project is None:
            return

        self.ensure_state_dir()
        self._project.updated_at = datetime.now()

        # Write atomically with temp file
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(self._project.to_dict(), f, indent=2)

        # Atomic rename
        temp_file.replace(self.state_file)

    def create_project(self, name: str, description: str = "") -> Project:
        """Create a new project."""
        self._project = Project(
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return self._project

    def get_or_create_project(self, name: str, description: str = "") -> Project:
        """Get existing project or create new one."""
        if self.exists():
            project = self.load()
            if project:
                return project

        return self.create_project(name, description)

    def reset(self) -> None:
        """Reset state by removing state file."""
        if self.state_file.exists():
            self.state_file.unlink()
        self._project = None

    def add_phase(self, phase: Phase) -> None:
        """Add a phase to the current project."""
        if self._project:
            self._project.phases.append(phase)
            self.save()

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None
    ) -> Optional[Task]:
        """Update the status of a specific task."""
        if not self._project:
            return None

        task = self._project.get_task_by_id(task_id)
        if task:
            task.status = status
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
            if error:
                task.error = error
            self._project.update_status()
            self.save()
        return task

    def start_iteration(self, number: int) -> Iteration:
        """Start a new iteration."""
        iteration = Iteration(
            number=number,
            started_at=datetime.now(),
            status="running"
        )
        if self._project:
            self._project.add_iteration(iteration)
            self.save()
        return iteration

    def end_iteration(
        self,
        number: int,
        status: str = "success",
        error: Optional[str] = None,
        output_log: Optional[str] = None
    ) -> Optional[Iteration]:
        """End an iteration and record its outcome."""
        if not self._project:
            return None

        for iteration in self._project.iterations:
            if iteration.number == number:
                iteration.ended_at = datetime.now()
                iteration.status = status
                iteration.error = error
                iteration.output_log = output_log
                self.save()
                return iteration
        return None

    def record_task_start(self, task_id: str, iteration_number: int) -> Optional[Task]:
        """Record that a task was started in an iteration."""
        if not self._project:
            return None

        task = self._project.get_task_by_id(task_id)
        if task:
            task.mark_started(iteration_number)

            # Also record in the iteration
            for iteration in self._project.iterations:
                if iteration.number == iteration_number:
                    if task_id not in iteration.tasks_started:
                        iteration.tasks_started.append(task_id)
                    break

            self.save()
        return task

    def record_task_complete(self, task_id: str, iteration_number: int) -> Optional[Task]:
        """Record that a task was completed in an iteration."""
        if not self._project:
            return None

        task = self._project.get_task_by_id(task_id)
        if task:
            task.mark_completed()
            task.iteration = iteration_number

            # Also record in the iteration
            for iteration in self._project.iterations:
                if iteration.number == iteration_number:
                    if task_id not in iteration.tasks_completed:
                        iteration.tasks_completed.append(task_id)
                    break

            self._project.update_status()
            self.save()
        return task

    def get_pending_tasks(self) -> list[Task]:
        """Get all pending tasks."""
        if not self._project:
            return []

        tasks = []
        for phase in self._project.phases:
            for task in phase.tasks:
                if task.status == TaskStatus.PENDING:
                    tasks.append(task)
        return tasks

    def get_progress_summary(self) -> dict:
        """Get a summary of current progress."""
        if not self._project:
            return {
                "status": "no_project",
                "total_tasks": 0,
                "completed_tasks": 0,
                "progress_percent": 0,
            }
        return self._project.get_summary()

    def backup(self, suffix: str = "") -> Path:
        """Create a backup of the current state."""
        if not self.state_file.exists():
            raise FileNotFoundError("No state file to backup")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"state_backup_{timestamp}{suffix}.json"
        backup_path = self.state_dir / backup_name

        with open(self.state_file, 'r') as src:
            with open(backup_path, 'w') as dst:
                dst.write(src.read())

        return backup_path

    def list_backups(self) -> list[Path]:
        """List all backup files."""
        if not self.state_dir.exists():
            return []
        return sorted(self.state_dir.glob("state_backup_*.json"), reverse=True)

    def restore_backup(self, backup_path: Path) -> Project:
        """Restore state from a backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with open(backup_path, 'r') as f:
            data = json.load(f)

        self._project = Project.from_dict(data)
        self.save()
        return self._project
