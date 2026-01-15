"""Plans directory input handler."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..parser.markdown import MarkdownParser
from .base import InputResult, InputSource


@dataclass
class PlansInput(InputSource):
    """Handles plan files from a directory."""

    plans_dir: str
    pattern: str = "*.md"
    project_name: Optional[str] = None

    def parse(self) -> InputResult:
        """Parse all plan files in the directory."""
        result = InputResult()
        path = Path(self.plans_dir)

        if not path.exists():
            result.errors.append(f"Plans directory not found: {self.plans_dir}")
            return result

        if not path.is_dir():
            result.errors.append(f"Not a directory: {self.plans_dir}")
            return result

        md_files = sorted(path.glob(self.pattern))
        if not md_files:
            msg = f"No plan files matching '{self.pattern}' found in: {self.plans_dir}"
            result.errors.append(msg)
            return result

        result.source_files = [str(f) for f in md_files]

        try:
            parser = MarkdownParser()
            project = parser.parse_directory(self.plans_dir)

            # Override project name if specified
            if self.project_name:
                project.name = self.project_name

            result.project = project

        except Exception as e:
            result.errors.append(f"Failed to parse plans: {str(e)}")

        return result

    def validate(self) -> list[str]:
        """Validate the plans directory."""
        errors = []
        path = Path(self.plans_dir)

        if not path.exists():
            errors.append(f"Plans directory not found: {self.plans_dir}")
        elif not path.is_dir():
            errors.append(f"Not a directory: {self.plans_dir}")
        else:
            md_files = list(path.glob(self.pattern))
            if not md_files:
                errors.append(f"No plan files matching '{self.pattern}' found")

        return errors

    @property
    def description(self) -> str:
        """Description of this input source."""
        return f"Plans directory: {self.plans_dir}"
