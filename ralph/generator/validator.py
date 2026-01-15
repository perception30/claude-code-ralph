"""Validation for generated documents."""

import re
from dataclasses import dataclass, field

from ..parser.markdown import MarkdownParser


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    task_count: int = 0
    phase_count: int = 0
    task_ids: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed with no errors."""
        return self.valid and len(self.errors) == 0


class GeneratorValidator:
    """Validates generated PRD and plans documents."""

    # Patterns for validation
    PRD_USER_STORY_PATTERN = re.compile(
        r'^###\s+([A-Z]+-\d+)[:\s]+.+$',
        re.MULTILINE
    )
    PRD_STATUS_PATTERN = re.compile(
        r'^\*\*Status:\*\*\s*(Pending|In Progress|Completed|Blocked|Failed)',
        re.MULTILINE | re.IGNORECASE
    )
    PRD_PRIORITY_PATTERN = re.compile(
        r'^\*\*Priority:\*\*\s*(High|Medium|Low|\d+)',
        re.MULTILINE | re.IGNORECASE
    )
    CHECKBOX_PATTERN = re.compile(
        r'^-\s+\[([ xX])\]\s+.+$',
        re.MULTILINE
    )
    TASK_PATTERN = re.compile(
        r'^-\s+\[([ xX])\]\s+([A-Z]+-\d+)[:\s]+.+$',
        re.MULTILINE
    )
    PHASE_PATTERN = re.compile(
        r'^##\s+(?:Phase\s+\d+[:\s]*)?(.+?)$',
        re.MULTILINE
    )

    def __init__(self):
        self.parser = MarkdownParser()

    def validate_prd(self, content: str) -> ValidationResult:
        """
        Validate PRD format.

        Args:
            content: PRD markdown content

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult(valid=True)

        # Check for project title
        if not re.search(r'^#\s+PRD:', content, re.MULTILINE):
            result.warnings.append("Missing 'PRD:' prefix in title")

        # Check for required sections
        required_sections = ["Overview", "User Stories"]
        for section in required_sections:
            if not re.search(rf'^##\s+{section}', content, re.MULTILINE):
                result.errors.append(f"Missing required section: {section}")
                result.valid = False

        # Validate user stories
        user_stories = self.PRD_USER_STORY_PATTERN.findall(content)
        if not user_stories:
            result.errors.append("No user stories found (expected ### US-XXX: pattern)")
            result.valid = False
        else:
            result.task_ids = user_stories
            result.task_count = len(user_stories)

            # Check for unique IDs
            if len(user_stories) != len(set(user_stories)):
                result.errors.append("Duplicate user story IDs found")
                result.valid = False

        # Validate each user story has required fields
        story_blocks = re.split(r'(?=^###\s+[A-Z]+-\d+)', content, flags=re.MULTILINE)
        for block in story_blocks:
            if not block.strip() or not re.match(r'^###\s+[A-Z]+-\d+', block):
                continue

            story_id_match = re.match(r'^###\s+([A-Z]+-\d+)', block)
            story_id = story_id_match.group(1) if story_id_match else "Unknown"

            if not self.PRD_STATUS_PATTERN.search(block):
                result.warnings.append(f"{story_id}: Missing **Status:** field")

            if not self.PRD_PRIORITY_PATTERN.search(block):
                result.warnings.append(f"{story_id}: Missing **Priority:** field")

            if not self.CHECKBOX_PATTERN.search(block):
                result.warnings.append(f"{story_id}: No acceptance criteria checkboxes found")

        # Check parseability
        parseability_errors = self._check_parseability(content)
        if parseability_errors:
            result.errors.extend(parseability_errors)
            result.valid = False

        return result

    def validate_plans(self, files: dict[str, str]) -> ValidationResult:
        """
        Validate phased plans format.

        Args:
            files: Dictionary of filename -> content

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult(valid=True)

        if not files:
            result.errors.append("No plan files provided")
            result.valid = False
            return result

        # Check for overview file
        overview_file = None
        for name in files:
            if "overview" in name.lower() or name.startswith("00"):
                overview_file = name
                break

        if not overview_file:
            result.warnings.append("No overview file found (expected 00-overview.md)")

        # Validate each file
        all_task_ids: list[str] = []
        phase_count = 0

        for filename, content in files.items():
            if overview_file and filename == overview_file:
                # Validate overview
                overview_errors = self._validate_overview(content)
                result.errors.extend(overview_errors)
            else:
                # Validate phase file
                phase_result = self._validate_phase_file(content, filename)
                result.errors.extend(phase_result.errors)
                result.warnings.extend(phase_result.warnings)
                all_task_ids.extend(phase_result.task_ids)
                phase_count += 1

        result.task_ids = all_task_ids
        result.task_count = len(all_task_ids)
        result.phase_count = phase_count

        # Check for unique task IDs
        if len(all_task_ids) != len(set(all_task_ids)):
            duplicates = [
                tid for tid in all_task_ids
                if all_task_ids.count(tid) > 1
            ]
            result.errors.append(f"Duplicate task IDs: {', '.join(set(duplicates))}")
            result.valid = False

        # Validate dependencies exist
        dep_errors = self._validate_dependencies(files, all_task_ids)
        result.errors.extend(dep_errors)

        if result.errors:
            result.valid = False

        return result

    def _validate_overview(self, content: str) -> list[str]:
        """Validate overview file content."""
        errors: list[str] = []

        # Check for required sections
        if not re.search(r'^##\s+Objective', content, re.MULTILINE | re.IGNORECASE):
            errors.append("Overview: Missing Objective section")

        if not re.search(r'^##\s+Phased\s+Approach', content, re.MULTILINE | re.IGNORECASE):
            errors.append("Overview: Missing Phased Approach section")

        # Check for phase table
        if "|" not in content:
            errors.append("Overview: Missing phase table")

        return errors

    def _validate_phase_file(self, content: str, filename: str) -> ValidationResult:
        """Validate individual phase file."""
        result = ValidationResult(valid=True)

        # Check for phase header
        if not re.search(r'^#\s+Phase\s+\d+', content, re.MULTILINE):
            result.warnings.append(f"{filename}: Missing 'Phase N:' header")

        # Check for required sections
        if not re.search(r'^##\s+Objective', content, re.MULTILINE | re.IGNORECASE):
            result.warnings.append(f"{filename}: Missing Objective section")

        if not re.search(r'^##\s+Tasks', content, re.MULTILINE | re.IGNORECASE):
            result.errors.append(f"{filename}: Missing Tasks section")

        # Extract task IDs
        task_matches = self.TASK_PATTERN.findall(content)
        result.task_ids = [match[1] for match in task_matches]

        if not result.task_ids:
            result.errors.append(f"{filename}: No tasks found (expected - [ ] TASK-XXX: pattern)")

        # Validate task format
        for task_id in result.task_ids:
            # Check task has description
            task_block_match = re.search(
                rf'-\s+\[[ xX]\]\s+{task_id}[:\s]+.+?\n((?:\s+-.+?\n)*)',
                content,
                re.MULTILINE
            )
            if task_block_match:
                task_block = task_block_match.group(1)
                if "Priority:" not in task_block:
                    result.warnings.append(f"{task_id}: Missing Priority")

        result.task_count = len(result.task_ids)
        return result

    def _validate_dependencies(
        self,
        files: dict[str, str],
        all_task_ids: list[str]
    ) -> list[str]:
        """Validate all dependencies reference existing tasks."""
        errors: list[str] = []
        dep_pattern = re.compile(
            r'^\s*-?\s*Dependenc(?:y|ies):\s*(.+?)$',
            re.MULTILINE | re.IGNORECASE
        )

        for filename, content in files.items():
            for match in dep_pattern.finditer(content):
                deps_str = match.group(1).strip()
                if deps_str.lower() == "none":
                    continue

                deps = [d.strip() for d in deps_str.split(",")]
                for dep in deps:
                    if dep and dep not in all_task_ids:
                        errors.append(
                            f"{filename}: Dependency '{dep}' not found in task list"
                        )

        return errors

    def _check_parseability(self, content: str) -> list[str]:
        """Check if content can be parsed by MarkdownParser."""
        errors: list[str] = []

        try:
            project = self.parser.parse_content(content)
            if not project.phases:
                errors.append("Parser extracted no phases from content")
            elif project.total_tasks == 0:
                errors.append("Parser extracted no tasks from content")
        except Exception as e:
            errors.append(f"Parser failed: {e}")

        return errors
