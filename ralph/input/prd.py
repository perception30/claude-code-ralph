"""PRD file input handler."""

from dataclasses import dataclass
from pathlib import Path

from ..parser.markdown import MarkdownParser
from .base import InputResult, InputSource


@dataclass
class PRDInput(InputSource):
    """Handles PRD (Product Requirements Document) file or directory input."""

    prd_path: str

    def parse(self) -> InputResult:
        """Parse the PRD file or directory."""
        result = InputResult()
        path = Path(self.prd_path)

        if not path.exists():
            result.errors.append(f"PRD path not found: {self.prd_path}")
            return result

        try:
            parser = MarkdownParser()

            if path.is_file():
                # Single PRD file (legacy/manual format)
                result.source_files = [str(path)]
                project = parser.parse_file(str(path))
                result.project = project

            elif path.is_dir():
                # PRD directory (generated format)
                md_files = sorted(path.glob("*.md"))
                if not md_files:
                    result.errors.append(f"No markdown files found in: {self.prd_path}")
                    return result

                result.source_files = [str(f) for f in md_files]
                project = parser.parse_directory(str(path))
                result.project = project

            else:
                result.errors.append(f"Path is neither file nor directory: {self.prd_path}")
                return result

        except Exception as e:
            result.errors.append(f"Failed to parse PRD: {str(e)}")

        return result

    def validate(self) -> list[str]:
        """Validate the PRD path."""
        errors = []
        path = Path(self.prd_path)

        if not path.exists():
            errors.append(f"PRD path not found: {self.prd_path}")
        elif path.is_file():
            # Single file validation
            if path.suffix.lower() not in ['.md', '.markdown']:
                errors.append(f"PRD file should be markdown: {self.prd_path}")
        elif path.is_dir():
            # Directory validation
            md_files = list(path.glob("*.md"))
            if not md_files:
                errors.append(f"No markdown files found in directory: {self.prd_path}")
        else:
            errors.append(f"Path is neither file nor directory: {self.prd_path}")

        return errors

    @property
    def description(self) -> str:
        """Description of this input source."""
        path = Path(self.prd_path)
        if path.is_dir():
            return f"PRD directory: {self.prd_path}"
        else:
            return f"PRD file: {self.prd_path}"
