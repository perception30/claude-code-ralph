"""Checkbox updating for markdown files."""

import re
from pathlib import Path


class CheckboxUpdater:
    """Updates checkbox status in markdown files."""

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
