"""Markdown parser for Ralph plan files and PRDs."""

import re
from pathlib import Path
from typing import Optional

from ..state.models import Phase, Project, Task, TaskStatus


class MarkdownParser:
    """Parses markdown files to extract phases and tasks."""

    # Regex patterns
    PHASE_PATTERN = re.compile(
        r'^##\s+(?:Phase\s+\d+[:\s]*)?(.+?)$',
        re.MULTILINE
    )
    TASK_CHECKBOX_PATTERN = re.compile(
        r'^(\s*)-\s+\[([ xX])\]\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$',
        re.MULTILINE
    )
    STATUS_PATTERN = re.compile(
        r'^Status:\s*(PENDING|IN_PROGRESS|COMPLETED|BLOCKED|FAILED)$',
        re.MULTILINE | re.IGNORECASE
    )
    PRIORITY_PATTERN = re.compile(
        r'^Priority:\s*(\d+|high|medium|low)$',
        re.MULTILINE | re.IGNORECASE
    )
    DEPENDENCY_PATTERN = re.compile(
        r'^-?\s*Dependenc(?:y|ies):\s*(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )
    DESCRIPTION_PATTERN = re.compile(
        r'^-?\s*Description:\s*(.+?)$',
        re.MULTILINE
    )

    # PRD-specific patterns
    USER_STORY_PATTERN = re.compile(
        r'^###\s+(?:([A-Z]+-\d+)[:\s]+)?(?:As a .+?,\s*)?(.+?)$',
        re.MULTILINE
    )
    ACCEPTANCE_CRITERIA_PATTERN = re.compile(
        r'^####\s+Acceptance\s+Criteria',
        re.MULTILINE | re.IGNORECASE
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

        # Check if this is a PRD or a plan file
        if self._is_prd_format(content):
            phases = self._parse_prd_format(content, source_file)
        else:
            phases = self._parse_plan_format(content, source_file)

        project.phases = phases
        project.update_status()
        return project

    def parse_directory(self, dir_path: str) -> Project:
        """Parse all markdown files in a directory and return a combined Project."""
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        md_files = sorted(path.glob("*.md"))
        if not md_files:
            raise ValueError(f"No markdown files found in: {dir_path}")

        # Create project from directory name
        project = Project(name=path.name)

        phase_priority = 0
        for md_file in md_files:
            content = md_file.read_text(encoding='utf-8')
            source = str(md_file)
            project.source_files.append(source)

            # Parse each file for phases
            if self._is_prd_format(content):
                phases = self._parse_prd_format(content, source)
            else:
                phases = self._parse_plan_format(content, source)

            # Add phases with incremented priority
            for phase in phases:
                phase.priority = phase_priority
                phase_priority += 1
                project.phases.append(phase)

        project.update_status()
        return project

    def _is_prd_format(self, content: str) -> bool:
        """Check if content is in PRD format (has user stories)."""
        return bool(self.USER_STORY_PATTERN.search(content))

    def _parse_plan_format(
        self,
        content: str,
        source_file: Optional[str] = None
    ) -> list[Phase]:
        """Parse plan format markdown."""
        phases = []
        lines = content.split('\n')
        current_phase: Optional[Phase] = None
        current_task: Optional[Task] = None
        task_counter = 0

        for line_num, line in enumerate(lines, 1):
            # Check for phase header (## Phase X: Name or ## Name)
            phase_match = re.match(r'^##\s+(.+?)$', line)
            if phase_match:
                # Save previous phase if exists
                if current_phase:
                    phases.append(current_phase)

                phase_name = phase_match.group(1).strip()
                # Extract phase number if present
                phase_num_match = re.match(r'Phase\s+(\d+)[:\s]*(.+)?', phase_name)
                if phase_num_match:
                    phase_id = f"phase-{phase_num_match.group(1)}"
                    phase_name = phase_num_match.group(2) or f"Phase {phase_num_match.group(1)}"
                else:
                    phase_id = f"phase-{len(phases) + 1}"

                current_phase = Phase(
                    id=phase_id,
                    name=phase_name.strip(),
                    source_file=source_file,
                    source_line=line_num,
                    priority=len(phases),
                )
                current_task = None
                continue

            # Check for task checkbox
            task_match = re.match(r'^(\s*)-\s+\[([ xX])\]\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$', line)
            if task_match and current_phase:
                indent = len(task_match.group(1))
                is_completed = task_match.group(2).lower() == 'x'
                task_id = task_match.group(3) or f"task-{len(current_phase.tasks) + 1}"
                task_name = task_match.group(4).strip()

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
                task_counter += 1
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
                    deps = [d.strip() for d in dep_match.group(1).split(',')]
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

        return phases

    def _parse_prd_format(
        self,
        content: str,
        source_file: Optional[str] = None
    ) -> list[Phase]:
        """Parse PRD format markdown."""
        phases = []
        lines = content.split('\n')
        current_phase: Optional[Phase] = None
        current_task: Optional[Task] = None
        in_acceptance_criteria = False

        for line_num, line in enumerate(lines, 1):
            # Check for phase header (## Section)
            phase_match = re.match(r'^##\s+(.+?)$', line)
            if phase_match:
                # Save previous phase if exists
                if current_phase and current_phase.tasks:
                    phases.append(current_phase)

                phase_name = phase_match.group(1).strip()
                phase_id = f"phase-{len(phases) + 1}"

                current_phase = Phase(
                    id=phase_id,
                    name=phase_name,
                    source_file=source_file,
                    source_line=line_num,
                    priority=len(phases),
                )
                current_task = None
                in_acceptance_criteria = False
                continue

            # Check for user story header (### US-XXX: ...)
            story_match = re.match(r'^###\s+(?:([A-Z]+-\d+)[:\s]+)?(.+?)$', line)
            if story_match and current_phase:
                task_id = story_match.group(1) or f"task-{len(current_phase.tasks) + 1}"
                task_name = story_match.group(2).strip()

                task = Task(
                    id=task_id,
                    name=task_name,
                    phase_id=current_phase.id,
                    source_file=source_file,
                    source_line=line_num,
                    priority=len(current_phase.tasks),
                )

                current_phase.tasks.append(task)
                current_task = task
                in_acceptance_criteria = False
                continue

            # Check for Acceptance Criteria header
            if re.match(r'^####\s+Acceptance\s+Criteria', line, re.IGNORECASE):
                in_acceptance_criteria = True
                continue

            # Check for status in PRD format
            status_pattern = (
                r'^\*\*Status:\*\*\s*'
                r'(Pending|In Progress|Completed|Blocked|Failed)'
            )
            status_match = re.match(status_pattern, line, re.IGNORECASE)
            if status_match and current_task:
                status_str = status_match.group(1).lower().replace(' ', '_')
                current_task.status = TaskStatus(status_str)
                continue

            # Check for priority in PRD format
            prd_priority_pattern = r'^\*\*Priority:\*\*\s*(High|Medium|Low|\d+)'
            priority_match = re.match(prd_priority_pattern, line, re.IGNORECASE)
            if priority_match and current_task:
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

            # Check for dependencies in PRD format
            dep_match = re.match(r'^\*\*Dependenc(?:y|ies):\*\*\s*(.+?)$', line, re.IGNORECASE)
            if dep_match and current_task:
                deps = [d.strip() for d in dep_match.group(1).split(',')]
                current_task.dependencies.extend(deps)
                continue

            # Parse acceptance criteria checkboxes as sub-tasks
            if in_acceptance_criteria and current_task:
                ac_match = re.match(r'^-\s+\[([ xX])\]\s+(.+?)$', line)
                if ac_match:
                    is_completed = ac_match.group(1).lower() == 'x'
                    criteria = ac_match.group(2).strip()

                    # Add to task description
                    if current_task.description:
                        current_task.description += f"\n- [{ac_match.group(1)}] {criteria}"
                    else:
                        current_task.description = f"- [{ac_match.group(1)}] {criteria}"

                    # If any criteria incomplete, task is incomplete
                    if not is_completed:
                        current_task.status = TaskStatus.PENDING
                    elif current_task.status == TaskStatus.PENDING:
                        # Only mark complete if all criteria are checked
                        pass

        # Add final phase
        if current_phase and current_phase.tasks:
            phases.append(current_phase)

        return phases

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
            # Also check PRD format
            if not self.USER_STORY_PATTERN.search(content):
                errors.append("No tasks found (checkbox items or user stories)")

        # Validate task IDs if present
        task_ids: list[str] = []
        for match in self.TASK_CHECKBOX_PATTERN.finditer(content):
            task_id = match.group(3)
            if task_id:
                if task_id in task_ids:
                    errors.append(f"Duplicate task ID: {task_id}")
                task_ids.append(task_id)

        # Check for PRD-specific validation
        if self._is_prd_format(content):
            prd_errors = self._validate_prd_format(content)
            errors.extend(prd_errors)

        return errors

    def _validate_prd_format(self, content: str) -> list[str]:
        """Validate PRD-specific format requirements."""
        errors: list[str] = []

        # Check for User Stories section
        if not re.search(r'^##\s+User\s+Stories', content, re.MULTILINE | re.IGNORECASE):
            errors.append("PRD missing 'User Stories' section")

        # Check user story format
        story_ids: list[str] = []
        for match in self.USER_STORY_PATTERN.finditer(content):
            story_id = match.group(1)
            if story_id:
                if story_id in story_ids:
                    errors.append(f"Duplicate user story ID: {story_id}")
                story_ids.append(story_id)

        return errors

    def detect_format(self, content: str) -> str:
        """
        Detect the format of markdown content.

        Args:
            content: Markdown content

        Returns:
            Format string: 'prd', 'plans', or 'unknown'
        """
        if self._is_prd_format(content):
            return 'prd'
        if self.TASK_CHECKBOX_PATTERN.search(content):
            return 'plans'
        return 'unknown'
