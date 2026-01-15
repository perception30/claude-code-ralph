"""Base classes for input handling."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..state.models import Project


@dataclass
class InputResult:
    """Result from parsing an input source."""
    project: Optional[Project] = None
    prompt: Optional[str] = None
    source_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the input result is valid."""
        return len(self.errors) == 0 and (self.project is not None or self.prompt is not None)

    @property
    def has_project(self) -> bool:
        """Check if a project was parsed."""
        return self.project is not None

    @property
    def has_prompt(self) -> bool:
        """Check if a direct prompt was provided."""
        return self.prompt is not None and len(self.prompt.strip()) > 0


class InputSource(ABC):
    """Abstract base class for input sources."""

    @abstractmethod
    def parse(self) -> InputResult:
        """Parse the input source and return an InputResult."""
        pass

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate the input source and return a list of errors."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the input source."""
        pass
