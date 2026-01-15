"""Base classes for generators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class GeneratorContext:
    """Context for generation."""
    prompt: str
    output_path: str
    project_name: Optional[str] = None
    num_phases: Optional[int] = None
    max_tasks_per_phase: int = 10
    additional_context: str = ""
    tech_stack: list[str] = field(default_factory=list)
    codebase_patterns: str = ""


@dataclass
class GeneratorResult:
    """Result of generation."""
    success: bool
    content: str = ""
    files: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_path: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if generation was successful with no errors."""
        return self.success and len(self.errors) == 0


class Generator(ABC):
    """Abstract base class for document generators."""

    @abstractmethod
    def generate(self, context: GeneratorContext) -> GeneratorResult:
        """
        Generate document(s) from the given context.

        Args:
            context: GeneratorContext with prompt and settings

        Returns:
            GeneratorResult with generated content/files
        """

    @abstractmethod
    def validate_output(self, content: str) -> list[str]:
        """
        Validate generated output matches expected format.

        Args:
            content: Generated content to validate

        Returns:
            List of validation error messages (empty if valid)
        """

    def write_output(self, result: GeneratorResult, output_path: str) -> None:
        """
        Write generated content to file(s).

        Args:
            result: GeneratorResult with content to write
            output_path: Path to write output
        """
        path = Path(output_path)

        if result.files:
            # Multiple files - output_path is a directory
            path.mkdir(parents=True, exist_ok=True)
            for filename, content in result.files.items():
                file_path = path / filename
                file_path.write_text(content, encoding='utf-8')
        elif result.content:
            # Single file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result.content, encoding='utf-8')

        result.output_path = str(path)
