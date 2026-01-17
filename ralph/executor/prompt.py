"""Optimized prompt builder for Claude execution."""

from dataclasses import dataclass
from typing import Optional

from ..state.models import Project, Task, TaskStatus


@dataclass
class ExecutionContext:
    """Context for prompt generation."""
    project: Project
    iteration: int
    working_dir: str
    source_files: list[str]
    progress_file: str = ".ralph/progress.txt"
    custom_instructions: str = ""
    commit_prefix: str = "feat:"
    update_source: bool = True


class PromptBuilder:
    """Builds optimized prompts for Claude execution."""

    # The core autonomous agent prompt - optimized for efficiency and clarity
    AUTONOMOUS_PROMPT_TEMPLATE = (
        '''You are Ralph, an autonomous software engineering agent '''
        '''executing iteration {iteration}.

## PROJECT STATUS
{progress_summary}

## PREVIOUS PROGRESS
Previous iterations logged in `{progress_file}`. Read if you need context about past decisions/learnings.

## CURRENT TASK
{current_task}

## SOURCE FILES
{source_files}

## INSTRUCTIONS
1. **Analyze** - Read relevant code paths/modules, deep analyse to understand context before making any changes
2. **Implement** - Complete the current task fully, following existing patterns and best practices step by step
3. **Verify** - Run quality/static checks (test, lint, typecheck) appropriate for the project
4. **Document** - Update source file checkbox: `- [x]` when task is done
5. **Commit** - If checks pass: `git commit -m "{commit_prefix} {task_id} - {task_name}"`

## COMPLETION
When done, document progress BEFORE writing status:

**Step 1: Append to `{progress_file}`** (compact, 5-10 lines total):
```markdown
---
# Iteration {iteration} - {task_id}: {task_name}
## Done: [key actions, 2-3 bullets]
## Decisions: [critical choices with brief why, 1-2 bullets]
## Learnings: [important discoveries, 1-2 bullets]
## Challenges: [major blockers + solutions, 1-2 bullets or omit]
```

**Step 2: Write status to `.ralph/status.json`**:
```json
{{"status": "COMPLETED", "task_id": "{task_id}"}}
```

If blocked or failed:
```json
{{"status": "BLOCKED", "task_id": "{task_id}", "reason": "explanation"}}
```

If ALL project tasks are done:
```json
{{"status": "PROJECT_COMPLETE", "task_id": "{task_id}"}}
```
{custom_section}
Now implement the task carefully. Be thorough but efficient.'''
    )

    def __init__(self, context: Optional[ExecutionContext] = None):
        self.context = context

    def build(self, context: Optional[ExecutionContext] = None) -> str:
        """Build the full prompt for Claude execution."""
        ctx = context or self.context
        if not ctx:
            raise ValueError("ExecutionContext is required")

        # Get next task
        next_task = ctx.project.get_next_task()
        if not next_task:
            # All tasks complete
            return self._build_completion_check_prompt(ctx)

        # Build progress summary
        progress_summary = self._format_progress(ctx.project)

        # Build current task section
        current_task = self._format_task(next_task, ctx.project)

        # Build source files section
        source_files = self._format_source_files(ctx.source_files)

        # Custom instructions section
        custom_section = ""
        if ctx.custom_instructions:
            custom_section = f"\n## ADDITIONAL CONTEXT\n{ctx.custom_instructions}\n"

        return self.AUTONOMOUS_PROMPT_TEMPLATE.format(
            iteration=ctx.iteration,
            progress_summary=progress_summary,
            progress_file=ctx.progress_file,
            current_task=current_task,
            source_files=source_files,
            commit_prefix=ctx.commit_prefix,
            task_id=next_task.id,
            task_name=next_task.name,
            custom_section=custom_section,
        )

    def _format_progress(self, project: Project) -> str:
        """Format project progress summary."""
        lines = [
            f"Project: {project.name}",
            f"Progress: {project.completed_tasks}/{project.total_tasks} tasks "
            f"({round(project.progress * 100, 1)}%)",
            "",
            "Phases:",
        ]

        current_found = False
        for phase in project.phases:
            status_icon = self._get_status_icon(phase.status)
            task_count = f"{phase.completed_count}/{len(phase.tasks)}"

            # Only mark the FIRST incomplete phase as current
            is_current = (
                not current_found
                and not phase.is_complete
                and phase.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
            )
            if is_current:
                current_found = True
                lines.append(f"  {status_icon} {phase.name}: {task_count} ← current")
            else:
                lines.append(f"  {status_icon} {phase.name}: {task_count}")

        return "\n".join(lines)

    def _format_task(self, task: Task, project: Project) -> str:
        """Format current task details."""
        phase = project.get_phase_by_id(task.phase_id) if task.phase_id else None

        lines = [
            f"ID: {task.id}",
            f"Name: {task.name}",
        ]

        if phase:
            lines.append(f"Phase: {phase.name}")

        if task.description:
            lines.append(f"Description: {task.description}")

        if task.dependencies:
            lines.append(f"Dependencies: {', '.join(task.dependencies)}")

        if task.source_file:
            lines.append(f"Source: {task.source_file}:{task.source_line}")

        return "\n".join(lines)

    def _format_source_files(self, source_files: list[str]) -> str:
        """Format source files list."""
        if not source_files:
            return "No source files specified"

        lines = ["Read these files for task details:"]
        for f in source_files:
            lines.append(f"  - {f}")

        return "\n".join(lines)

    def _build_completion_check_prompt(self, ctx: ExecutionContext) -> str:
        """Build prompt for when all tasks appear complete."""
        return f'''You are Ralph, an autonomous software engineering agent.

## PROJECT STATUS
All {ctx.project.total_tasks} tasks appear to be completed!

## VERIFICATION TASK
1. Review the source files to confirm all checkboxes are marked `[x]`
2. Run final quality checks (test, lint, build)
3. If everything passes, output: `PROJECT_COMPLETE`
4. If issues found, output the incomplete task status

## SOURCE FILES
{self._format_source_files(ctx.source_files)}

Verify completion and report status.'''

    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get icon for task status."""
        icons = {
            TaskStatus.PENDING: "○",
            TaskStatus.IN_PROGRESS: "→",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.BLOCKED: "⊘",
            TaskStatus.FAILED: "✗",
            TaskStatus.SKIPPED: "⊖",
        }
        return icons.get(status, "?")
