"""Checkbox parsing and updating for markdown files."""

import re
from pathlib import Path
from typing import Optional

from ..state.models import Task, TaskStatus


class CheckboxParser:
    """Parses checkbox status from markdown content."""

    CHECKBOX_PATTERN = re.compile(
        r'^(\s*-\s+\[)([ xX])(\]\s+(?:[A-Z]+-\d+[:\s]+)?(.+?))$',
        re.MULTILINE
    )

    @classmethod
    def count_checkboxes(cls, content: str) -> tuple[int, int]:
        """
        Count completed and total checkboxes in content.

        Returns:
            Tuple of (completed_count, total_count)
        """
        matches = cls.CHECKBOX_PATTERN.findall(content)
        total = len(matches)
        completed = sum(1 for m in matches if m[1].lower() == 'x')
        return completed, total

    @classmethod
    def get_completion_percentage(cls, content: str) -> float:
        """Get completion percentage from 0.0 to 1.0."""
        completed, total = cls.count_checkboxes(content)
        return completed / total if total > 0 else 0.0

    @classmethod
    def is_complete(cls, content: str) -> bool:
        """Check if all checkboxes are completed."""
        completed, total = cls.count_checkboxes(content)
        return completed == total and total > 0

    @classmethod
    def extract_tasks(
        cls,
        content: str,
        source_file: Optional[str] = None
    ) -> list[Task]:
        """Extract tasks from checkbox content."""
        tasks: list[Task] = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            match = re.match(
                r'^(\s*)-\s+\[([ xX])\]\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$',
                line
            )
            if match:
                is_completed = match.group(2).lower() == 'x'
                task_id = match.group(3) or f"task-{len(tasks) + 1}"
                task_name = match.group(4).strip()

                task = Task(
                    id=task_id,
                    name=task_name,
                    status=TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING,
                    source_file=source_file,
                    source_line=line_num,
                )
                tasks.append(task)

        return tasks


class CheckboxUpdater:
    """Updates checkbox status in markdown files."""

    @classmethod
    def update_task_status(
        cls,
        content: str,
        task_id: str,
        completed: bool
    ) -> str:
        """
        Update the checkbox status for a specific task.

        Args:
            content: Markdown content
            task_id: Task ID to update (e.g., "US-001")
            completed: True to check, False to uncheck

        Returns:
            Updated content
        """
        new_status = 'x' if completed else ' '

        # Pattern to match the specific task
        pattern = re.compile(
            rf'^(\s*-\s+\[)([ xX])(\]\s+{re.escape(task_id)}[:\s]+.+?)$',
            re.MULTILINE
        )

        def replace_checkbox(match):
            return f"{match.group(1)}{new_status}{match.group(3)}"

        return pattern.sub(replace_checkbox, content)

    @classmethod
    def update_task_by_name(
        cls,
        content: str,
        task_name: str,
        completed: bool
    ) -> str:
        """
        Update the checkbox status for a task by its name.

        Args:
            content: Markdown content
            task_name: Task name to find and update
            completed: True to check, False to uncheck

        Returns:
            Updated content
        """
        new_status = 'x' if completed else ' '
        escaped_name = re.escape(task_name)

        # Pattern to match by task name
        pattern = re.compile(
            rf'^(\s*-\s+\[)([ xX])(\]\s+(?:[A-Z]+-\d+[:\s]+)?{escaped_name})$',
            re.MULTILINE
        )

        def replace_checkbox(match):
            return f"{match.group(1)}{new_status}{match.group(3)}"

        return pattern.sub(replace_checkbox, content)

    @classmethod
    def update_task_by_line(
        cls,
        content: str,
        line_number: int,
        completed: bool
    ) -> str:
        """
        Update the checkbox status at a specific line.

        Args:
            content: Markdown content
            line_number: 1-based line number
            completed: True to check, False to uncheck

        Returns:
            Updated content
        """
        lines = content.split('\n')
        if line_number < 1 or line_number > len(lines):
            return content

        line = lines[line_number - 1]
        new_status = 'x' if completed else ' '

        # Replace checkbox on this line
        updated_line = re.sub(
            r'^(\s*-\s+\[)([ xX])(\].+)$',
            rf'\g<1>{new_status}\g<3>',
            line
        )

        lines[line_number - 1] = updated_line
        return '\n'.join(lines)

    @classmethod
    def update_file(
        cls,
        file_path: str,
        task_id: str,
        completed: bool
    ) -> bool:
        """
        Update a task's checkbox status in a file.

        Args:
            file_path: Path to markdown file
            task_id: Task ID to update
            completed: New status

        Returns:
            True if file was modified, False otherwise
        """
        path = Path(file_path)
        if not path.exists():
            return False

        original_content = path.read_text(encoding='utf-8')
        updated_content = cls.update_task_status(original_content, task_id, completed)

        if updated_content != original_content:
            path.write_text(updated_content, encoding='utf-8')
            return True

        return False

    @classmethod
    def update_file_by_line(
        cls,
        file_path: str,
        line_number: int,
        completed: bool
    ) -> bool:
        """
        Update a checkbox at a specific line in a file.

        Args:
            file_path: Path to markdown file
            line_number: Line number to update
            completed: New status

        Returns:
            True if file was modified, False otherwise
        """
        path = Path(file_path)
        if not path.exists():
            return False

        original_content = path.read_text(encoding='utf-8')
        updated_content = cls.update_task_by_line(original_content, line_number, completed)

        if updated_content != original_content:
            path.write_text(updated_content, encoding='utf-8')
            return True

        return False

    @classmethod
    def add_status_marker(
        cls,
        content: str,
        phase_name: str,
        status: str
    ) -> str:
        """
        Add or update a status marker for a phase.

        Args:
            content: Markdown content
            phase_name: Name of the phase
            status: Status string (e.g., "COMPLETED", "IN_PROGRESS")

        Returns:
            Updated content
        """
        escaped_name = re.escape(phase_name)

        # Check if status marker already exists
        status_pattern = re.compile(
            rf'(^##\s+(?:Phase\s+\d+[:\s]*)?{escaped_name}\s*\n)(?:Status:\s*\w+\s*\n)?',
            re.MULTILINE
        )

        if status_pattern.search(content):
            # Update existing status
            return status_pattern.sub(
                rf'\g<1>Status: {status}\n',
                content
            )
        else:
            # Find phase header and add status after it
            header_pattern = re.compile(
                rf'(^##\s+(?:Phase\s+\d+[:\s]*)?{escaped_name}\s*\n)',
                re.MULTILINE
            )
            return header_pattern.sub(
                rf'\g<1>Status: {status}\n',
                content
            )
