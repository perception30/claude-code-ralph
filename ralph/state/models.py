"""Data models for Ralph task management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    """Status of a task or phase."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Represents a single task to be implemented."""
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    phase_id: Optional[str] = None

    # Tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    iteration: Optional[int] = None
    attempts: int = 0
    error: Optional[str] = None

    # Source location for updating
    source_file: Optional[str] = None
    source_line: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "phase_id": self.phase_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "iteration": self.iteration,
            "attempts": self.attempts,
            "error": self.error,
            "source_file": self.source_file,
            "source_line": self.source_line,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create Task from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            dependencies=data.get("dependencies", []),
            phase_id=data.get("phase_id"),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at") else None
            ),
            iteration=data.get("iteration"),
            attempts=data.get("attempts", 0),
            error=data.get("error"),
            source_file=data.get("source_file"),
            source_line=data.get("source_line"),
        )

    def mark_started(self, iteration: int) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.iteration = iteration
        self.attempts += 1

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.error = error

    def mark_blocked(self, reason: str) -> None:
        """Mark task as blocked."""
        self.status = TaskStatus.BLOCKED
        self.error = reason


@dataclass
class Phase:
    """Represents a phase containing multiple tasks."""
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    tasks: list[Task] = field(default_factory=list)
    priority: int = 0

    # Source location
    source_file: Optional[str] = None
    source_line: Optional[int] = None

    @property
    def progress(self) -> float:
        """Calculate completion percentage."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

    @property
    def completed_count(self) -> int:
        """Count of completed tasks."""
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

    @property
    def pending_count(self) -> int:
        """Count of pending tasks."""
        return sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)

    @property
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks) if self.tasks else False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "priority": self.priority,
            "source_file": self.source_file,
            "source_line": self.source_line,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Phase":
        """Create Phase from dictionary."""
        phase = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            source_file=data.get("source_file"),
            source_line=data.get("source_line"),
        )
        phase.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return phase

    def get_next_task(self) -> Optional[Task]:
        """Get next pending task in this phase."""
        for task in sorted(self.tasks, key=lambda t: t.priority):
            if task.status == TaskStatus.PENDING:
                return task
        return None

    def update_status(self) -> None:
        """Update phase status based on task states."""
        if not self.tasks:
            return

        if all(t.status == TaskStatus.COMPLETED for t in self.tasks):
            self.status = TaskStatus.COMPLETED
        elif any(t.status == TaskStatus.IN_PROGRESS for t in self.tasks):
            self.status = TaskStatus.IN_PROGRESS
        elif any(t.status == TaskStatus.FAILED for t in self.tasks):
            self.status = TaskStatus.FAILED
        elif any(t.status == TaskStatus.BLOCKED for t in self.tasks):
            self.status = TaskStatus.BLOCKED


@dataclass
class Iteration:
    """Record of a single iteration run."""
    number: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    tasks_started: list[str] = field(default_factory=list)
    tasks_completed: list[str] = field(default_factory=list)
    status: str = "running"  # running, success, failed, interrupted
    error: Optional[str] = None
    output_log: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "number": self.number,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "tasks_started": self.tasks_started,
            "tasks_completed": self.tasks_completed,
            "status": self.status,
            "error": self.error,
            "output_log": self.output_log,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Iteration":
        """Create Iteration from dictionary."""
        return cls(
            number=data["number"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            tasks_started=data.get("tasks_started", []),
            tasks_completed=data.get("tasks_completed", []),
            status=data.get("status", "running"),
            error=data.get("error"),
            output_log=data.get("output_log"),
        )


@dataclass
class Project:
    """Represents the entire project with all phases and tasks."""
    name: str
    phases: list[Phase] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    iterations: list[Iteration] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING

    # Metadata
    version: str = "1.0"
    description: str = ""
    source_files: list[str] = field(default_factory=list)

    @property
    def total_tasks(self) -> int:
        """Total number of tasks across all phases."""
        return sum(len(p.tasks) for p in self.phases)

    @property
    def completed_tasks(self) -> int:
        """Number of completed tasks."""
        return sum(
            1 for p in self.phases
            for t in p.tasks
            if t.status == TaskStatus.COMPLETED
        )

    @property
    def progress(self) -> float:
        """Overall completion percentage."""
        total = self.total_tasks
        return self.completed_tasks / total if total > 0 else 0.0

    @property
    def current_iteration(self) -> int:
        """Current iteration number."""
        return len(self.iterations)

    @property
    def is_complete(self) -> bool:
        """Check if all phases are complete."""
        return all(p.is_complete for p in self.phases) if self.phases else False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "phases": [p.to_dict() for p in self.phases],
            "iterations": [i.to_dict() for i in self.iterations],
            "source_files": self.source_files,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create Project from dictionary."""
        project = cls(
            name=data["name"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at") else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at") else datetime.now()
            ),
            source_files=data.get("source_files", []),
        )
        project.phases = [Phase.from_dict(p) for p in data.get("phases", [])]
        project.iterations = [Iteration.from_dict(i) for i in data.get("iterations", [])]
        return project

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Find a task by its ID."""
        for phase in self.phases:
            for task in phase.tasks:
                if task.id == task_id:
                    return task
        return None

    def get_phase_by_id(self, phase_id: str) -> Optional[Phase]:
        """Find a phase by its ID."""
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None

    def get_next_task(self) -> Optional[Task]:
        """Get the next task to work on based on priority and dependencies."""
        for phase in sorted(self.phases, key=lambda p: p.priority):
            if phase.status == TaskStatus.COMPLETED:
                continue
            for task in sorted(phase.tasks, key=lambda t: t.priority):
                if task.status == TaskStatus.PENDING:
                    if self._dependencies_met(task):
                        return task
        return None

    def get_current_phase(self) -> Optional[Phase]:
        """Get the currently active phase."""
        for phase in sorted(self.phases, key=lambda p: p.priority):
            if phase.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return phase
            if not phase.is_complete:
                return phase
        return None

    def _dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies of a task are completed."""
        for dep_id in task.dependencies:
            dep_task = self.get_task_by_id(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def update_status(self) -> None:
        """Update project status based on phase states."""
        self.updated_at = datetime.now()

        # Update all phase statuses first
        for phase in self.phases:
            phase.update_status()

        if not self.phases:
            return

        if all(p.status == TaskStatus.COMPLETED for p in self.phases):
            self.status = TaskStatus.COMPLETED
        elif any(p.status == TaskStatus.IN_PROGRESS for p in self.phases):
            self.status = TaskStatus.IN_PROGRESS
        elif any(p.status == TaskStatus.FAILED for p in self.phases):
            self.status = TaskStatus.FAILED
        else:
            self.status = TaskStatus.PENDING

    def add_iteration(self, iteration: Iteration) -> None:
        """Add an iteration to the project."""
        self.iterations.append(iteration)
        self.updated_at = datetime.now()

    def get_summary(self) -> dict:
        """Get a summary of project status."""
        return {
            "name": self.name,
            "status": self.status.value,
            "total_phases": len(self.phases),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "progress_percent": round(self.progress * 100, 1),
            "iterations_run": len(self.iterations),
            "current_phase": (phase.name if (phase := self.get_current_phase()) else None),
            "next_task": (task.name if (task := self.get_next_task()) else None),
        }
