"""Configuration file input handler."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import InputResult, InputSource
from .plans import PlansInput
from .prd import PRDInput


@dataclass
class RalphProjectConfig:
    """Configuration structure for Ralph projects."""

    # Project info
    name: str = "Ralph Project"
    description: str = ""

    # Input configuration
    input_type: str = "plans"  # plans, prd, prompt
    input_path: str = ".ide/tasks/plans"
    input_pattern: str = "*.md"

    # Execution settings
    max_iterations: int = 50
    idle_timeout: int = 10
    sleep_between: int = 2
    retry_attempts: int = 3
    retry_delay: int = 5

    # Claude settings
    model: Optional[str] = None
    skip_permissions: bool = True
    custom_instructions: str = ""

    # Output settings
    log_dir: str = ".ralph/logs"
    state_file: str = ".ralph/state.json"
    verbose: bool = False

    # Hooks
    before_iteration: Optional[str] = None
    after_iteration: Optional[str] = None
    on_complete: Optional[str] = None

    # Completion settings
    completion_flag: str = "/tmp/ralph_complete.flag"
    update_source: bool = True
    commit_changes: bool = True
    commit_prefix: str = "feat:"

    @classmethod
    def from_dict(cls, data: dict) -> "RalphProjectConfig":
        """Create config from dictionary."""
        config = cls()

        # Project info
        project = data.get("project", {})
        config.name = project.get("name", config.name)
        config.description = project.get("description", config.description)

        # Input config
        input_cfg = data.get("input", {})
        config.input_type = input_cfg.get("type", config.input_type)
        config.input_path = input_cfg.get("path", config.input_path)
        config.input_pattern = input_cfg.get("pattern", config.input_pattern)

        # Execution settings
        exec_cfg = data.get("execution", {})
        config.max_iterations = exec_cfg.get("max_iterations", config.max_iterations)
        config.idle_timeout = exec_cfg.get("idle_timeout", config.idle_timeout)
        config.sleep_between = exec_cfg.get("sleep_between", config.sleep_between)
        config.retry_attempts = exec_cfg.get("retry_attempts", config.retry_attempts)
        config.retry_delay = exec_cfg.get("retry_delay", config.retry_delay)

        # Claude settings
        claude_cfg = data.get("claude", {})
        config.model = claude_cfg.get("model", config.model)
        config.skip_permissions = claude_cfg.get("skip_permissions", config.skip_permissions)
        config.custom_instructions = claude_cfg.get(
            "custom_instructions", config.custom_instructions
        )

        # Output settings
        output_cfg = data.get("output", {})
        config.log_dir = output_cfg.get("log_dir", config.log_dir)
        config.state_file = output_cfg.get("state_file", config.state_file)
        config.verbose = output_cfg.get("verbose", config.verbose)

        # Hooks
        hooks_cfg = data.get("hooks", {})
        config.before_iteration = hooks_cfg.get("before_iteration")
        config.after_iteration = hooks_cfg.get("after_iteration")
        config.on_complete = hooks_cfg.get("on_complete")

        # Completion settings
        completion_cfg = data.get("completion", {})
        config.completion_flag = completion_cfg.get("flag_file", config.completion_flag)
        config.update_source = completion_cfg.get("update_source", config.update_source)
        config.commit_changes = completion_cfg.get("commit_changes", config.commit_changes)
        config.commit_prefix = completion_cfg.get("commit_prefix", config.commit_prefix)

        return config

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": "1.0",
            "project": {
                "name": self.name,
                "description": self.description,
            },
            "input": {
                "type": self.input_type,
                "path": self.input_path,
                "pattern": self.input_pattern,
            },
            "execution": {
                "max_iterations": self.max_iterations,
                "idle_timeout": self.idle_timeout,
                "sleep_between": self.sleep_between,
                "retry_attempts": self.retry_attempts,
                "retry_delay": self.retry_delay,
            },
            "claude": {
                "model": self.model,
                "skip_permissions": self.skip_permissions,
                "custom_instructions": self.custom_instructions,
            },
            "output": {
                "log_dir": self.log_dir,
                "state_file": self.state_file,
                "verbose": self.verbose,
            },
            "hooks": {
                "before_iteration": self.before_iteration,
                "after_iteration": self.after_iteration,
                "on_complete": self.on_complete,
            },
            "completion": {
                "flag_file": self.completion_flag,
                "update_source": self.update_source,
                "commit_changes": self.commit_changes,
                "commit_prefix": self.commit_prefix,
            },
        }


@dataclass
class ConfigInput(InputSource):
    """Handles configuration file input."""

    config_file: str
    config: Optional[RalphProjectConfig] = None

    def parse(self) -> InputResult:
        """Parse the configuration file and resolve input source."""
        result = InputResult()
        path = Path(self.config_file)

        if not path.exists():
            result.errors.append(f"Config file not found: {self.config_file}")
            return result

        try:
            with open(path) as f:
                data = json.load(f)

            self.config = RalphProjectConfig.from_dict(data)
            result.source_files = [str(path)]

            # Resolve input based on config
            working_dir = path.parent
            input_path = working_dir / self.config.input_path

            if self.config.input_type == "plans":
                plans_input = PlansInput(
                    plans_dir=str(input_path),
                    pattern=self.config.input_pattern,
                    project_name=self.config.name,
                )
                plans_result = plans_input.parse()

                if plans_result.is_valid:
                    result.project = plans_result.project
                    result.source_files.extend(plans_result.source_files)
                else:
                    result.errors.extend(plans_result.errors)

            elif self.config.input_type == "prd":
                prd_input = PRDInput(prd_path=str(input_path))
                prd_result = prd_input.parse()

                if prd_result.is_valid:
                    result.project = prd_result.project
                    result.source_files.extend(prd_result.source_files)
                else:
                    result.errors.extend(prd_result.errors)

            elif self.config.input_type == "prompt":
                # Prompt is stored in custom_instructions
                result.prompt = self.config.custom_instructions

            else:
                result.errors.append(f"Unknown input type: {self.config.input_type}")

            # Apply custom instructions to project if present
            if result.project and self.config.description:
                result.project.description = self.config.description

        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON in config file: {e}")
        except Exception as e:
            result.errors.append(f"Failed to parse config: {str(e)}")

        return result

    def validate(self) -> list[str]:
        """Validate the configuration file."""
        errors = []
        path = Path(self.config_file)

        if not path.exists():
            errors.append(f"Config file not found: {self.config_file}")
            return errors

        try:
            with open(path) as f:
                data = json.load(f)

            # Validate required fields
            if "input" not in data:
                errors.append("Config missing 'input' section")
            else:
                input_cfg = data["input"]
                if "type" not in input_cfg:
                    errors.append("Config input missing 'type' field")
                if "path" not in input_cfg:
                    errors.append("Config input missing 'path' field")

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")

        return errors

    @property
    def description(self) -> str:
        """Description of this input source."""
        return f"Config file: {self.config_file}"
