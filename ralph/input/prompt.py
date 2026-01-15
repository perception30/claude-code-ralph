"""Prompt input handler for direct prompts."""

from dataclasses import dataclass

from ..state.models import Phase, Project, Task
from .base import InputResult, InputSource


@dataclass
class PromptInput(InputSource):
    """Handles direct prompt input."""

    prompt: str
    task_name: str = "Execute prompt"

    def parse(self) -> InputResult:
        """Parse the prompt into a minimal project structure."""
        result = InputResult(prompt=self.prompt)

        # Create a simple project with a single task
        project = Project(name="Prompt Task")
        phase = Phase(
            id="phase-prompt",
            name="Execute Prompt",
            priority=0,
        )
        task = Task(
            id="task-prompt",
            name=self.task_name,
            description=self.prompt,
            priority=0,
            phase_id="phase-prompt",
        )
        phase.tasks.append(task)
        project.phases.append(phase)
        project.update_status()

        result.project = project
        return result

    def validate(self) -> list[str]:
        """Validate the prompt input."""
        errors = []
        if not self.prompt or not self.prompt.strip():
            errors.append("Prompt cannot be empty")
        return errors

    @property
    def description(self) -> str:
        """Description of this input source."""
        prompt_preview = self.prompt[:50] + "..." if len(self.prompt) > 50 else self.prompt
        return f"Prompt: {prompt_preview}"
