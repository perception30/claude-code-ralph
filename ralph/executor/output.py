"""Output parser for Claude responses."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedOutput:
    """Parsed result from Claude's output."""

    # Task completion
    task_completed: bool = False
    task_id: Optional[str] = None
    task_status: Optional[str] = None  # COMPLETED, BLOCKED, FAILED
    reason: Optional[str] = None

    # Project completion
    project_complete: bool = False

    # Extracted info
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    blocked_tasks: list[str] = field(default_factory=list)

    # Commits detected
    commits: list[str] = field(default_factory=list)

    # Errors detected
    errors: list[str] = field(default_factory=list)

    # Raw output
    raw_output: str = ""

    @property
    def is_success(self) -> bool:
        """Check if the output indicates success."""
        return self.task_completed or self.project_complete

    @property
    def has_errors(self) -> bool:
        """Check if errors were detected."""
        return len(self.errors) > 0


class OutputParser:
    """Parses Claude's output to extract completion markers and status."""

    # Status marker patterns
    TASK_STATUS_PATTERN = re.compile(
        r'TASK_STATUS:\s*(COMPLETED|BLOCKED|FAILED)',
        re.IGNORECASE
    )
    TASK_ID_PATTERN = re.compile(
        r'TASK_ID:\s*([A-Za-z0-9_-]+)',
        re.IGNORECASE
    )
    REASON_PATTERN = re.compile(
        r'REASON:\s*(.+?)(?:\n|$)',
        re.IGNORECASE
    )
    PROJECT_COMPLETE_PATTERN = re.compile(
        r'PROJECT_COMPLETE',
        re.IGNORECASE
    )

    # Alternative completion pattern (fallback)
    ALT_COMPLETED_PATTERN = re.compile(
        r'(?:task|phase).*(?:completed?|done|finished)',
        re.IGNORECASE
    )

    # Commit detection
    COMMIT_PATTERN = re.compile(
        r'(?:git commit|committed).*?(?:"([^"]+)"|\'([^\']+)\')',
        re.IGNORECASE
    )

    # Error patterns
    ERROR_PATTERNS = [
        re.compile(r'error:\s*(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'failed:\s*(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'exception:\s*(.+?)(?:\n|$)', re.IGNORECASE),
    ]

    @classmethod
    def parse(cls, output: str) -> ParsedOutput:
        """Parse Claude's output and extract status markers."""
        result = ParsedOutput(raw_output=output)

        # Check for project completion
        if cls.PROJECT_COMPLETE_PATTERN.search(output):
            result.project_complete = True
            return result

        # Parse task status
        status_match = cls.TASK_STATUS_PATTERN.search(output)
        if status_match:
            result.task_status = status_match.group(1).upper()
            result.task_completed = result.task_status == "COMPLETED"

            # Extract task ID
            id_match = cls.TASK_ID_PATTERN.search(output)
            if id_match:
                result.task_id = id_match.group(1)

            # Extract reason if blocked/failed
            if result.task_status in ("BLOCKED", "FAILED"):
                reason_match = cls.REASON_PATTERN.search(output)
                if reason_match:
                    result.reason = reason_match.group(1).strip()

                if result.task_status == "BLOCKED":
                    result.blocked_tasks.append(result.task_id or "unknown")
                else:
                    result.failed_tasks.append(result.task_id or "unknown")
            else:
                result.completed_tasks.append(result.task_id or "unknown")

        # Fallback: check for alternative completion markers
        elif cls.ALT_COMPLETED_PATTERN.search(output):
            result.task_completed = True
            result.task_status = "COMPLETED"

        # Detect commits
        for commit_match in cls.COMMIT_PATTERN.finditer(output):
            message = commit_match.group(1) or commit_match.group(2)
            if message:
                result.commits.append(message)

        # Detect errors
        for pattern in cls.ERROR_PATTERNS:
            for error_match in pattern.finditer(output):
                result.errors.append(error_match.group(1).strip())

        return result
