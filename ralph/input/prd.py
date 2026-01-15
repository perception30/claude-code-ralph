"""PRD file input handler."""

from dataclasses import dataclass
from pathlib import Path

from ..parser.markdown import MarkdownParser
from .base import InputResult, InputSource


@dataclass
class PRDInput(InputSource):
    """Handles PRD (Product Requirements Document) file input."""

    prd_file: str

    def parse(self) -> InputResult:
        """Parse the PRD file."""
        result = InputResult()
        path = Path(self.prd_file)

        if not path.exists():
            result.errors.append(f"PRD file not found: {self.prd_file}")
            return result

        if not path.is_file():
            result.errors.append(f"Not a file: {self.prd_file}")
            return result

        result.source_files = [str(path)]

        try:
            parser = MarkdownParser(str(path))
            project = parser.parse_file(self.prd_file)
            result.project = project

        except Exception as e:
            result.errors.append(f"Failed to parse PRD: {str(e)}")

        return result

    def validate(self) -> list[str]:
        """Validate the PRD file."""
        errors = []
        path = Path(self.prd_file)

        if not path.exists():
            errors.append(f"PRD file not found: {self.prd_file}")
        elif not path.is_file():
            errors.append(f"Not a file: {self.prd_file}")
        elif path.suffix.lower() not in ['.md', '.markdown']:
            errors.append(f"PRD file should be markdown: {self.prd_file}")

        return errors

    @property
    def description(self) -> str:
        """Description of this input source."""
        return f"PRD file: {self.prd_file}"
