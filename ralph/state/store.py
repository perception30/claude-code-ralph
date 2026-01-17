"""State persistence for Ralph CLI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .identity import ProjectIdentity
from .models import Iteration, Phase, Project, Task, TaskStatus


class StateStore:
    """Manages persistent state storage for Ralph projects.

    Supports project-specific directories to allow multiple concurrent
    projects without state interference.

    Directory structure:
        .ralph/
            projects/
                <project-id>/
                    state.json
                    status.json
                    logs/
    """

    DEFAULT_STATE_DIR = ".ralph"
    PROJECTS_SUBDIR = "projects"
    DEFAULT_STATE_FILE = "state.json"
    STATUS_FILE = "status.json"

    def __init__(
        self,
        working_dir: str = ".",
        project_identity: Optional[ProjectIdentity] = None
    ):
        """Initialize state store.

        Args:
            working_dir: Working directory for the project
            project_identity: Optional project identity for isolation.
                If provided, state is stored in a project-specific directory.
                If not provided, uses legacy single-project mode for backwards
                compatibility.
        """
        self.working_dir = Path(working_dir).resolve()
        self.project_identity = project_identity

        # Determine state directory based on project identity
        base_state_dir = self.working_dir / self.DEFAULT_STATE_DIR
        if project_identity:
            self.state_dir = (
                base_state_dir / self.PROJECTS_SUBDIR / project_identity.state_dir_name
            )
        else:
            # Legacy mode - single state directory
            self.state_dir = base_state_dir

        self.state_file = self.state_dir / self.DEFAULT_STATE_FILE
        self.status_file = self.state_dir / self.STATUS_FILE
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
            with open(self.state_file) as f:
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

    def merge_with_existing(self, new_project: Project) -> Project:
        """Merge a newly parsed project with existing state.

        Preserves task completion status, iteration history, and other
        runtime state from the existing project while adopting any new
        tasks or phases from the fresh parse.

        Note: When using project_identity, projects are already matched
        by their unique ID, so we always merge. In legacy mode (no identity),
        we check source files for backwards compatibility.

        Args:
            new_project: Freshly parsed project from plan files

        Returns:
            Merged project with preserved state
        """
        existing = self.load()
        if not existing:
            return new_project

        # In legacy mode (no project identity), check source files match
        if not self.project_identity:
            if set(existing.source_files) != set(new_project.source_files):
                # Different project in legacy mode, use new one
                return new_project

        # Build a map of existing task states by ID
        existing_task_states: dict[str, dict] = {}
        for phase in existing.phases:
            for task in phase.tasks:
                existing_task_states[task.id] = {
                    'status': task.status,
                    'completed_at': task.completed_at,
                    'started_at': task.started_at,
                    'iteration': task.iteration,
                    'attempts': task.attempts,
                    'error': task.error,
                }

        # Apply existing states to new project
        for phase in new_project.phases:
            for task in phase.tasks:
                if task.id in existing_task_states:
                    state = existing_task_states[task.id]
                    task.status = state['status']
                    task.completed_at = state['completed_at']
                    task.started_at = state['started_at']
                    task.iteration = state['iteration']
                    task.attempts = state['attempts']
                    task.error = state['error']

        # Preserve iteration history
        new_project.iterations = existing.iterations
        new_project.created_at = existing.created_at

        # Update project status based on merged task states
        new_project.update_status()

        return new_project

    @classmethod
    def list_projects(cls, working_dir: str = ".") -> list[dict]:
        """List all projects with saved state.

        Returns:
            List of dicts with project info (id, name, progress, etc.)
        """
        base_dir = Path(working_dir).resolve() / cls.DEFAULT_STATE_DIR / cls.PROJECTS_SUBDIR
        projects: list[dict] = []

        if not base_dir.exists():
            return projects

        for project_dir in base_dir.iterdir():
            if not project_dir.is_dir():
                continue

            state_file = project_dir / cls.DEFAULT_STATE_FILE
            if not state_file.exists():
                continue

            try:
                with open(state_file) as f:
                    data = json.load(f)
                projects.append({
                    'project_id': project_dir.name,
                    'name': data.get('name', 'Unknown'),
                    'status': data.get('status', 'unknown'),
                    'total_tasks': data.get('total_tasks', 0),
                    'completed_tasks': data.get('completed_tasks', 0),
                    'source_files': data.get('source_files', []),
                    'updated_at': data.get('updated_at'),
                })
            except (json.JSONDecodeError, OSError):
                continue

        return projects

    @classmethod
    def load_by_project_id(
        cls,
        project_id: str,
        working_dir: str = "."
    ) -> tuple[Optional['Project'], Optional['ProjectIdentity']]:
        """Load project by ID (supports partial match).

        Args:
            project_id: Full or partial project ID
            working_dir: Working directory

        Returns:
            (Project, ProjectIdentity) if found, (None, None) if not found or ambiguous
        """
        from .identity import InputType, ProjectIdentity

        base_dir = Path(working_dir).resolve() / cls.DEFAULT_STATE_DIR / cls.PROJECTS_SUBDIR

        if not base_dir.exists():
            return None, None

        # Find matching directories
        matches = [d for d in base_dir.iterdir()
                  if d.is_dir() and d.name.startswith(project_id)]

        if len(matches) != 1:
            return None, None  # Not found or ambiguous

        # Load project
        project_dir = matches[0]
        state_file = project_dir / cls.DEFAULT_STATE_FILE

        if not state_file.exists():
            return None, None

        try:
            with open(state_file) as f:
                data = json.load(f)

            project = Project.from_dict(data)

            # Create ProjectIdentity for resume
            identity = ProjectIdentity(
                project_id=project_dir.name,
                input_type=InputType.PROMPT,  # Generic for resume
                input_source=f"project:{project_dir.name}",
                display_name=project.name,
            )

            return project, identity

        except (json.JSONDecodeError, OSError):
            return None, None

    @classmethod
    def find_by_name(
        cls,
        name: str,
        working_dir: str = "."
    ) -> list[dict]:
        """Find projects matching a name.

        Returns exact matches first, then partial matches.
        """
        all_projects = cls.list_projects(working_dir)

        # Exact match (case-insensitive)
        exact = [p for p in all_projects if p['name'].lower() == name.lower()]
        if exact:
            return exact

        # Partial match
        partial = [p for p in all_projects if name.lower() in p['name'].lower()]
        return partial

    def backup(self, suffix: str = "") -> Path:
        """Create a backup of the current state."""
        if not self.state_file.exists():
            raise FileNotFoundError("No state file to backup")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"state_backup_{timestamp}{suffix}.json"
        backup_path = self.state_dir / backup_name

        with open(self.state_file) as src:
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

        with open(backup_path) as f:
            data = json.load(f)

        self._project = Project.from_dict(data)
        self.save()
        return self._project
