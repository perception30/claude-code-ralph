"""AI prompt templates for PRD and plans generation."""

from typing import Optional

# PRD Generation Template - Claude writes directly to file
PRD_GENERATION_TEMPLATE = '''You are a technical product manager creating a PRD.

## USER REQUEST
{user_prompt}

## OUTPUT PATH
Write the PRD to: {output_path}

## INSTRUCTIONS
1. Create a PRD document following standard format with:
   - Overview section
   - User Stories (US-001, US-002, etc.) with acceptance criteria
   - Each user story should have **Status:** Pending, **Priority:** High/Medium/Low
   - Use - [ ] checkboxes for acceptance criteria

2. Write the PRD file directly to the output path specified above

3. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-prd"}}

Now create the PRD file.
'''

# Plans Generation Template - Claude writes files directly
PLANS_GENERATION_TEMPLATE = '''You are a technical architect creating phased plans.

## USER REQUEST
{user_prompt}

## OUTPUT DIRECTORY
Write plan files to: {output_path}

## INSTRUCTIONS
1. Create a directory structure with:
   - 00-overview.md - Master plan with phase table
   - 01-phase-name.md, 02-phase-name.md, etc. - Individual phase files

2. Each phase file should have:
   - ## Objective
   - ## Tasks with checkboxes: - [ ] TASK-N01: Description
   - Task metadata: Priority, Dependencies, Description
   - ## Verification section

3. Task IDs: TASK-101, TASK-102 for phase 1; TASK-201, TASK-202 for phase 2, etc.

4. Write all files directly to the output directory

5. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-plans"}}

Now create the plan files.
'''

# PRD to Plans Conversion Template
PRD_TO_PLANS_TEMPLATE = '''You are a technical architect converting a PRD to plans.

## INPUT PRD
{prd_content}

## OUTPUT DIRECTORY
Write plan files to: {output_path}

## INSTRUCTIONS
1. Convert user stories to implementation tasks
2. Group related tasks into phases
3. Create plan files:
   - 00-overview.md
   - 01-phase-name.md, 02-phase-name.md, etc.

4. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-plans"}}

Now convert the PRD to plan files.
'''


def build_tech_stack_context(tech_stack: list[str]) -> str:
    """Build tech stack context for prompts."""
    if not tech_stack:
        return ""
    return f"\n**Tech Stack:** {', '.join(tech_stack)}\n"


def build_codebase_context(patterns: str) -> str:
    """Build codebase patterns context for prompts."""
    if not patterns:
        return ""
    return f"\n**Codebase Patterns:**\n{patterns}\n"


def format_prompt(
    template: str,
    user_prompt: str,
    additional_context: str = "",
    num_phases: Optional[int] = None,
    **kwargs: str,
) -> str:
    """Format a generation template with user input."""
    phases_str = str(num_phases) if num_phases else "3-5"

    return template.format(
        user_prompt=user_prompt,
        additional_context=additional_context or "None specified",
        num_phases=phases_str,
        **kwargs
    )
