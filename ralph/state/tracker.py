"""Progress tracking for Ralph CLI."""

from datetime import datetime
from typing import Callable, Optional

from .models import Iteration, Phase, Project, Task, TaskStatus
from .store import StateStore


class ProgressTracker:
    """Tracks and reports progress during Ralph execution."""

    def __init__(
        self,
        store: StateStore,
        on_progress: Optional[Callable[[dict], None]] = None
    ):
        self.store = store
        self.on_progress = on_progress
        self._current_iteration: Optional[Iteration] = None
        self._current_task: Optional[Task] = None

    @property
    def project(self) -> Optional[Project]:
        """Get the current project."""
        return self.store.project

    def start_iteration(self, number: int) -> Iteration:
        """Start tracking a new iteration."""
        self._current_iteration = self.store.start_iteration(number)
        self._notify_progress("iteration_started", {
            "iteration": number,
            "timestamp": datetime.now().isoformat(),
        })
        return self._current_iteration

    def end_iteration(
        self,
        status: str = "success",
        error: Optional[str] = None,
        output_log: Optional[str] = None
    ) -> Optional[Iteration]:
        """End the current iteration."""
        if not self._current_iteration:
            return None

        iteration = self.store.end_iteration(
            self._current_iteration.number,
            status=status,
            error=error,
            output_log=output_log
        )

        self._notify_progress("iteration_ended", {
            "iteration": self._current_iteration.number,
            "status": status,
            "duration_seconds": iteration.duration_seconds if iteration else None,
            "tasks_completed": iteration.tasks_completed if iteration else [],
        })

        self._current_iteration = None
        return iteration

    def start_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as started."""
        if not self._current_iteration:
            return None

        task = self.store.record_task_start(task_id, self._current_iteration.number)
        if task:
            self._current_task = task
            self._notify_progress("task_started", {
                "task_id": task_id,
                "task_name": task.name,
                "iteration": self._current_iteration.number,
            })
        return task

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        if not self._current_iteration:
            return None

        task = self.store.record_task_complete(task_id, self._current_iteration.number)
        if task:
            self._current_task = None
            self._notify_progress("task_completed", {
                "task_id": task_id,
                "task_name": task.name,
                "iteration": self._current_iteration.number,
            })
        return task

    def fail_task(self, task_id: str, error: str) -> Optional[Task]:
        """Mark a task as failed."""
        task = self.store.update_task_status(task_id, TaskStatus.FAILED, error)
        if task:
            self._current_task = None
            self._notify_progress("task_failed", {
                "task_id": task_id,
                "task_name": task.name,
                "error": error,
            })
        return task

    def get_next_task(self) -> Optional[Task]:
        """Get the next task to work on."""
        if not self.project:
            return None
        return self.project.get_next_task()

    def get_current_phase(self) -> Optional[Phase]:
        """Get the currently active phase."""
        if not self.project:
            return None
        return self.project.get_current_phase()

    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        return self.project.is_complete if self.project else False

    def get_progress(self) -> dict:
        """Get current progress information."""
        if not self.project:
            return {
                "status": "no_project",
                "total_tasks": 0,
                "completed_tasks": 0,
                "progress_percent": 0,
                "current_iteration": 0,
            }

        current_phase = self.project.get_current_phase()
        next_task = self.project.get_next_task()

        return {
            "status": self.project.status.value,
            "total_tasks": self.project.total_tasks,
            "completed_tasks": self.project.completed_tasks,
            "progress_percent": round(self.project.progress * 100, 1),
            "current_iteration": (
                self._current_iteration.number
                if self._current_iteration else self.project.current_iteration
            ),
            "total_phases": len(self.project.phases),
            "current_phase": {
                "id": current_phase.id,
                "name": current_phase.name,
                "progress": round(current_phase.progress * 100, 1),
                "tasks_total": len(current_phase.tasks),
                "tasks_completed": current_phase.completed_count,
            } if current_phase else None,
            "next_task": {
                "id": next_task.id,
                "name": next_task.name,
                "description": next_task.description,
            } if next_task else None,
            "current_task": {
                "id": self._current_task.id,
                "name": self._current_task.name,
            } if self._current_task else None,
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status.value,
                    "tasks_total": len(p.tasks),
                    "tasks_completed": p.completed_count,
                }
                for p in self.project.phases
            ],
        }

    def get_phases_summary(self) -> list[dict]:
        """Get a summary of all phases."""
        if not self.project:
            return []

        return [
            {
                "id": phase.id,
                "name": phase.name,
                "status": phase.status.value,
                "progress": round(phase.progress * 100, 1),
                "tasks_total": len(phase.tasks),
                "tasks_completed": phase.completed_count,
                "tasks_pending": phase.pending_count,
            }
            for phase in self.project.phases
        ]

    def get_task_list(self, status_filter: Optional[TaskStatus] = None) -> list[dict]:
        """Get a list of all tasks, optionally filtered by status."""
        if not self.project:
            return []

        tasks = []
        for phase in self.project.phases:
            for task in phase.tasks:
                if status_filter is None or task.status == status_filter:
                    tasks.append({
                        "id": task.id,
                        "name": task.name,
                        "status": task.status.value,
                        "phase_id": phase.id,
                        "phase_name": phase.name,
                        "priority": task.priority,
                        "attempts": task.attempts,
                        "iteration": task.iteration,
                    })
        return tasks

    def get_iteration_history(self, limit: int = 10) -> list[dict]:
        """Get history of recent iterations."""
        if not self.project:
            return []

        iterations = self.project.iterations[-limit:]
        return [
            {
                "number": it.number,
                "started_at": it.started_at.isoformat(),
                "ended_at": it.ended_at.isoformat() if it.ended_at else None,
                "duration_seconds": it.duration_seconds,
                "status": it.status,
                "tasks_completed": it.tasks_completed,
                "error": it.error,
            }
            for it in reversed(iterations)
        ]

    def _notify_progress(self, event: str, data: dict) -> None:
        """Notify progress callback with an event."""
        if self.on_progress:
            self.on_progress({
                "event": event,
                "data": data,
                "progress": self.get_progress(),
            })

    def format_progress_bar(self, width: int = 40) -> str:
        """Format a text progress bar."""
        if not self.project:
            return "[" + " " * width + "] 0%"

        filled = int(self.project.progress * width)
        bar = "#" * filled + "-" * (width - filled)
        percent = round(self.project.progress * 100, 1)
        return f"[{bar}] {percent}%"

    def format_status_line(self) -> str:
        """Format a single-line status string."""
        progress = self.get_progress()

        if progress["status"] == "no_project":
            return "No project loaded"

        completed = progress['completed_tasks']
        total = progress['total_tasks']
        pct = progress['progress_percent']
        parts = [f"Progress: {completed}/{total} tasks ({pct}%)"]

        if progress.get("current_phase"):
            parts.append(f"Phase: {progress['current_phase']['name']}")

        if progress.get("next_task"):
            parts.append(f"Next: {progress['next_task']['name']}")

        return " | ".join(parts)
