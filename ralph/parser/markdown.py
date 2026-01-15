"""Markdown parser for Ralph plan files.

Uses unified plan format with `- [ ] TASK-XXX:` checkboxes for tasks.
Multi-file structure: 00-overview.md, 01-phase.md, etc.
"""

import re
from pathlib import Path
from typing import Optional

from ..state.models import Phase, Project, Task, TaskStatus


class MarkdownParser:
    """Parses markdown plan files to extract phases and tasks."""

    # Regex patterns
    PHASE_PATTERN = re.compile(
        r'^##\s+(?:Phase\s+\d+[:\s]*)?(.+?)$',
        re.MULTILINE
    )
    TASK_CHECKBOX_PATTERN = re.compile(
        r'^(\s*)-\s+\[([ xX])\]\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$',
        re.MULTILINE
    )
    DEPENDENCY_PATTERN = re.compile(
        r'^-?\s*Dependenc(?:y|ies):\s*(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )
    DESCRIPTION_PATTERN = re.compile(
        r'^-?\s*Description:\s*(.+?)$',
        re.MULTILINE
    )

    def __init__(self, source_file: Optional[str] = None):
        self.source_file = source_file

    def parse_file(self, file_path: str) -> Project:
        """Parse a markdown file and return a Project."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding='utf-8')
        return self.parse_content(content, str(path))

    def parse_content(self, content: str, source_file: Optional[str] = None) -> Project:
        """Parse markdown content and return a Project."""
        self.source_file = source_file

        # Extract project name from first H1 header
        name_match = re.search(r'^#\s+(?:Project:\s*)?(.+?)$', content, re.MULTILINE)
        project_name = name_match.group(1).strip() if name_match else "Unnamed Project"

        project = Project(name=project_name)
        if source_file:
            project.source_files.append(source_file)

        # Parse using plan format
        phases, _, _ = self._parse_plan_format(content, source_file, 0, 0)

        project.phases = phases
        project.update_status()
        return project

    def parse_directory(self, dir_path: str) -> Project:
        """Parse all markdown files in a directory and return a combined Project.

        Each file becomes ONE phase (using H1 title or filename as phase name).
        All tasks within the file belong to that single phase.
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        md_files = sorted(path.glob("*.md"))
        if not md_files:
            raise ValueError(f"No markdown files found in: {dir_path}")

        # Create project from directory name
        project = Project(name=path.name)

        # Global task counter for unique IDs across all files
        global_task_counter = 0

        for phase_num, md_file in enumerate(md_files):
            content = md_file.read_text(encoding='utf-8')
            source = str(md_file)
            project.source_files.append(source)

            # Parse file as a single phase
            phase, global_task_counter = self._parse_file_as_phase(
                content, source, phase_num, global_task_counter
            )

            # Only add phases that have tasks
            if phase and phase.tasks:
                project.phases.append(phase)

        project.update_status()
        return project

    def _parse_file_as_phase(
        self,
        content: str,
        source_file: str,
        phase_num: int,
        global_task_counter: int
    ) -> tuple[Optional[Phase], int]:
        """Parse a single file as one phase.

        The H1 header becomes the phase name. All checkbox tasks in the file
        belong to this single phase.

        Args:
            content: File content
            source_file: Source file path
            phase_num: Phase number for ID generation
            global_task_counter: Running task counter

        Returns:
            Tuple of (Phase or None, updated task counter)
        """
        # Extract phase name from H1 header or filename
        name_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if name_match:
            phase_name = name_match.group(1).strip()
            # Clean up phase name (remove "Phase N:" prefix)
            phase_name = re.sub(r'^Phase\s+\d+[:\s]*', '', phase_name).strip()
        else:
            # Use filename without extension
            phase_name = Path(source_file).stem

        phase = Phase(
            id=f"phase-{phase_num + 1}",
            name=phase_name,
            source_file=source_file,
            source_line=1,
            priority=phase_num,
        )

        # Find all checkbox tasks in the file (only with explicit TASK-XXX IDs)
        lines = content.split('\n')
        current_task: Optional[Task] = None

        for line_num, line in enumerate(lines, 1):
            # Check for task checkbox - MUST have explicit TASK-XXX ID
            task_match = re.match(
                r'^(\s*)-\s+\[([ xX])\]\s+([A-Z]+-\d+)[:\s]+(.+?)$',
                line
            )
            if task_match:
                indent = len(task_match.group(1))
                is_completed = task_match.group(2).lower() == 'x'
                task_id = task_match.group(3)
                task_name = task_match.group(4).strip()

                task = Task(
                    id=task_id,
                    name=task_name,
                    status=TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING,
                    phase_id=phase.id,
                    source_file=source_file,
                    source_line=line_num,
                    priority=len(phase.tasks),
                )

                # Sub-task detection (indented)
                if indent > 2 and current_task:
                    task.dependencies.append(current_task.id)

                phase.tasks.append(task)
                current_task = task
                continue

            # Check for task metadata (under current task)
            if current_task:
                # Priority
                priority_match = re.match(
                    r'^\s*-?\s*\*?\*?Priority\*?\*?:\s*(\d+|high|medium|low)',
                    line, re.IGNORECASE
                )
                if priority_match:
                    priority_val = priority_match.group(1).lower()
                    if priority_val == 'high':
                        current_task.priority = 1
                    elif priority_val == 'medium':
                        current_task.priority = 2
                    elif priority_val == 'low':
                        current_task.priority = 3
                    else:
                        current_task.priority = int(priority_val)
                    continue

                # Dependencies
                dep_match = re.match(
                    r'^\s*-?\s*\*?\*?Dependenc(?:y|ies)\*?\*?:\s*(.+?)$',
                    line, re.IGNORECASE
                )
                if dep_match:
                    deps = [
                        d.strip() for d in dep_match.group(1).split(',')
                        if d.strip().lower() not in ('none', 'n/a', '-')
                    ]
                    current_task.dependencies.extend(deps)
                    continue

                # Description
                desc_match = re.match(
                    r'^\s*-?\s*\*?\*?Description\*?\*?:\s*(.+?)$',
                    line
                )
                if desc_match:
                    current_task.description = desc_match.group(1).strip()
                    continue

        return phase, global_task_counter

    def _parse_plan_format(
        self,
        content: str,
        source_file: Optional[str] = None,
        global_phase_counter: int = 0,
        global_task_counter: int = 0
    ) -> tuple[list[Phase], int, int]:
        """Parse plan format markdown.

        Args:
            content: Markdown content to parse
            source_file: Source file path for tracking
            global_phase_counter: Starting phase counter for globally unique IDs
            global_task_counter: Starting task counter for globally unique IDs

        Returns:
            Tuple of (phases list, updated phase counter, updated task counter)
        """
        phases = []
        lines = content.split('\n')
        current_phase: Optional[Phase] = None
        current_task: Optional[Task] = None

        for line_num, line in enumerate(lines, 1):
            # Check for phase header (## Phase X: Name or ## Name)
            phase_match = re.match(r'^##\s+(.+?)$', line)
            if phase_match:
                # Save previous phase if exists
                if current_phase:
                    phases.append(current_phase)

                phase_name = phase_match.group(1).strip()
                # Always use global counter for unique phase ID
                global_phase_counter += 1
                phase_id = f"phase-{global_phase_counter}"

                # Clean up phase name if it has "Phase N:" prefix
                phase_num_match = re.match(r'Phase\s+\d+[:\s]*(.+)?', phase_name)
                if phase_num_match:
                    phase_name = phase_num_match.group(1) or phase_name

                current_phase = Phase(
                    id=phase_id,
                    name=phase_name.strip(),
                    source_file=source_file,
                    source_line=line_num,
                    priority=global_phase_counter - 1,  # 0-indexed priority
                )
                current_task = None
                continue

            # Check for task checkbox
            task_match = re.match(r'^(\s*)-\s+\[([ xX])\]\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$', line)
            if task_match and current_phase:
                indent = len(task_match.group(1))
                is_completed = task_match.group(2).lower() == 'x'
                explicit_task_id = task_match.group(3)
                task_name = task_match.group(4).strip()

                # Use explicit ID if provided (like TASK-101), otherwise generate unique one
                if explicit_task_id:
                    task_id = explicit_task_id
                else:
                    global_task_counter += 1
                    task_id = f"task-{global_task_counter}"

                task = Task(
                    id=task_id,
                    name=task_name,
                    status=TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING,
                    phase_id=current_phase.id,
                    source_file=source_file,
                    source_line=line_num,
                    priority=len(current_phase.tasks),
                )

                # Check if this is a sub-task (indented)
                if indent > 2 and current_task:
                    # Add as dependency
                    task.dependencies.append(current_task.id)

                current_phase.tasks.append(task)
                current_task = task
                continue

            # Check for task metadata (under current task)
            if current_task:
                # Priority
                priority_pattern = r'^\s*-?\s*Priority:\s*(\d+|high|medium|low)$'
                priority_match = re.match(priority_pattern, line, re.IGNORECASE)
                if priority_match:
                    priority_val = priority_match.group(1).lower()
                    if priority_val == 'high':
                        current_task.priority = 1
                    elif priority_val == 'medium':
                        current_task.priority = 2
                    elif priority_val == 'low':
                        current_task.priority = 3
                    else:
                        current_task.priority = int(priority_val)
                    continue

                # Dependencies
                dep_match = re.match(r'^\s*-?\s*Dependenc(?:y|ies):\s*(.+?)$', line, re.IGNORECASE)
                if dep_match:
                    deps = [
                        d.strip() for d in dep_match.group(1).split(',')
                        if d.strip().lower() not in ('none', 'n/a', '-')
                    ]
                    current_task.dependencies.extend(deps)
                    continue

                # Description
                desc_match = re.match(r'^\s*-?\s*Description:\s*(.+?)$', line)
                if desc_match:
                    current_task.description = desc_match.group(1).strip()
                    continue

        # Add final phase
        if current_phase:
            phases.append(current_phase)

        return phases, global_phase_counter, global_task_counter

    def merge_projects(self, projects: list[Project]) -> Project:
        """Merge multiple projects into one."""
        if not projects:
            return Project(name="Empty Project")

        merged = Project(name=projects[0].name)
        phase_priority = 0

        for project in projects:
            merged.source_files.extend(project.source_files)
            for phase in project.phases:
                phase.priority = phase_priority
                merged.phases.append(phase)
                phase_priority += 1

        merged.update_status()
        return merged

    def validate_format(self, content: str) -> list[str]:
        """
        Validate markdown content format and return errors.

        Args:
            content: Markdown content to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check for project title
        if not re.search(r'^#\s+.+$', content, re.MULTILINE):
            errors.append("Missing project title (# heading)")

        # Check for at least one phase
        if not self.PHASE_PATTERN.search(content):
            errors.append("No phase headers found (## headings)")

        # Check for tasks
        if not self.TASK_CHECKBOX_PATTERN.search(content):
            errors.append("No tasks found (- [ ] TASK-XXX: format)")

        # Validate task IDs - check for duplicates
        task_ids: list[str] = []
        for match in self.TASK_CHECKBOX_PATTERN.finditer(content):
            task_id = match.group(3)
            if task_id:
                if task_id in task_ids:
                    errors.append(f"Duplicate task ID: {task_id}")
                task_ids.append(task_id)

        return errors

    def detect_format(self, content: str) -> str:
        """
        Detect the format of markdown content.

        Args:
            content: Markdown content

        Returns:
            Format string: 'plans' or 'unknown'
        """
        if self.TASK_CHECKBOX_PATTERN.search(content):
            return 'plans'
        return 'unknown'
