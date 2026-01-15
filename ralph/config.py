"""Configuration management for Ralph CLI."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RalphConfig:
    """Configuration for Ralph autonomous agent."""

    # Iteration settings
    max_iterations: int = 10
    idle_timeout: int = 30  # seconds to wait before considering response complete
    sleep_between: int = 2  # seconds to sleep between iterations

    # Paths
    plans_dir: str = ".ide/tasks/plans"
    completion_flag: str = "/tmp/ralph_complete.flag"
    log_dir: str = ".ide/logs/ralph"

    # Claude settings
    skip_permissions: bool = True
    model: Optional[str] = None

    # Prompt template
    prompt_template: str = """You are Ralph, an autonomous Software Engineering coding agent.

1. Read the phased plans in {plans_dir}/*.md
2. Carefully check their implementation status so far.
3. Pick the **highest priority** phase from the phased plans which is not yet completed.
4. Implement that single phase step by step very carefully end to end.
   Read all relevant code paths and modules to understand the task/story fully.
5. Run quality checks (e.g., typecheck, lint, test - use whatever your project requires)
6. Update CLAUDE.md files if you discover reusable patterns
7. If checks pass, commit ALL changes with message: feat: [Story ID] - [Story Title]
8. Mark the implementation status in the phased plan for future iterations.

## End Condition

After completing your phase, just end your response (next iteration will continue).
If ALL phases are completed, create a file at {completion_flag} with content "done"
"""

    def get_prompt(self, working_dir: str) -> str:
        """Generate the prompt with resolved paths."""
        plans_path = Path(working_dir) / self.plans_dir
        return self.prompt_template.format(
            plans_dir=str(plans_path.resolve()),
            completion_flag=self.completion_flag
        )

    def save(self, path: Path) -> None:
        """Save configuration to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "RalphConfig":
        """Load configuration from JSON file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".config" / "ralph" / "config.json"


def get_project_config_path(working_dir: str = ".") -> Path:
    """Get the project-specific configuration file path."""
    return Path(working_dir) / ".ide" / "ralph.json"
