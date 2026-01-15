"""Project identity management for Ralph.

Generates unique project identifiers based on input sources to enable
multiple concurrent projects without state interference.
"""

import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InputType(str, Enum):
    """Type of input source."""
    PLANS = "plans"
    PRD = "prd"
    PROMPT = "prompt"
    CONFIG = "config"


@dataclass
class ProjectIdentity:
    """Uniquely identifies a Ralph project."""

    project_id: str
    input_type: InputType
    input_source: str  # Original path or prompt
    display_name: str  # Human-readable name

    @property
    def state_dir_name(self) -> str:
        """Get the directory name for this project's state."""
        return self.project_id

    def __str__(self) -> str:
        return f"{self.display_name} ({self.project_id[:8]})"


class ProjectIdentifier:
    """Generates unique project identifiers from input sources."""

    @staticmethod
    def from_plans_dir(plans_dir: str, working_dir: str = ".") -> ProjectIdentity:
        """Generate project identity from a plans directory.

        Uses the absolute path of the plans directory to ensure
        the same directory always gets the same ID.
        """
        abs_path = os.path.abspath(plans_dir)
        rel_to_working = os.path.relpath(abs_path, os.path.abspath(working_dir))

        # Use relative path for ID (more portable)
        project_id = ProjectIdentifier._hash_string(f"plans:{rel_to_working}")

        # Display name from directory
        display_name = Path(abs_path).name

        return ProjectIdentity(
            project_id=project_id,
            input_type=InputType.PLANS,
            input_source=abs_path,
            display_name=display_name,
        )

    @staticmethod
    def from_prd_file(prd_file: str, working_dir: str = ".") -> ProjectIdentity:
        """Generate project identity from a PRD file.

        Uses the absolute path of the PRD file.
        """
        abs_path = os.path.abspath(prd_file)
        rel_to_working = os.path.relpath(abs_path, os.path.abspath(working_dir))

        project_id = ProjectIdentifier._hash_string(f"prd:{rel_to_working}")

        # Display name from file (without extension)
        display_name = Path(abs_path).stem

        return ProjectIdentity(
            project_id=project_id,
            input_type=InputType.PRD,
            input_source=abs_path,
            display_name=display_name,
        )

    @staticmethod
    def from_prompt(prompt: str) -> ProjectIdentity:
        """Generate project identity from a direct prompt.

        Uses a hash of the prompt text. Same prompt = same project.
        """
        # Normalize prompt (strip whitespace)
        normalized = prompt.strip()
        project_id = ProjectIdentifier._hash_string(f"prompt:{normalized}")

        # Display name from first 30 chars of prompt
        display_name = normalized[:30] + "..." if len(normalized) > 30 else normalized

        return ProjectIdentity(
            project_id=project_id,
            input_type=InputType.PROMPT,
            input_source=normalized,
            display_name=display_name,
        )

    @staticmethod
    def from_config_file(config_file: str, working_dir: str = ".") -> ProjectIdentity:
        """Generate project identity from a config file.

        Uses the absolute path of the config file.
        """
        abs_path = os.path.abspath(config_file)
        rel_to_working = os.path.relpath(abs_path, os.path.abspath(working_dir))

        project_id = ProjectIdentifier._hash_string(f"config:{rel_to_working}")

        # Display name from file (without extension)
        display_name = Path(abs_path).stem

        return ProjectIdentity(
            project_id=project_id,
            input_type=InputType.CONFIG,
            input_source=abs_path,
            display_name=display_name,
        )

    @staticmethod
    def _hash_string(s: str) -> str:
        """Generate a short hash from a string."""
        return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]
