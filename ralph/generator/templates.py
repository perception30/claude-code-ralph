"""AI prompt templates for PRD and plans generation."""

from typing import Optional

# PRD Generation Template
PRD_GENERATION_TEMPLATE = '''You are a technical product manager \
creating a Product Requirements Document (PRD).

## USER REQUEST
{user_prompt}

## ADDITIONAL CONTEXT
{additional_context}

## OUTPUT REQUIREMENTS

Generate a PRD in this EXACT markdown format:

```markdown
# PRD: {{Project Name}}

## Overview
{{2-3 sentence project description}}

## Objectives
- {{Clear, measurable objective 1}}
- {{Clear, measurable objective 2}}

## User Stories

### US-001: {{First User Story Title}}
**Status:** Pending
**Priority:** High
**Dependencies:** None

**Description:**
As a {{user type}}, I want {{capability}} so that {{benefit}}.

#### Acceptance Criteria
- [ ] {{Specific, testable criterion 1}}
- [ ] {{Specific, testable criterion 2}}
- [ ] {{Specific, testable criterion 3}}

### US-002: {{Second User Story Title}}
**Status:** Pending
**Priority:** Medium
**Dependencies:** US-001

...continue for all user stories...

## Non-Functional Requirements
- [ ] NFR-001: {{Performance/security/scalability requirement}}

## Success Criteria
- [ ] All user stories completed
- [ ] All tests passing
```

## CRITICAL FORMAT RULES
1. User story IDs MUST follow pattern: US-XXX (e.g., US-001, US-002)
2. Status MUST be exactly: **Status:** Pending
3. Priority MUST be exactly: **Priority:** High|Medium|Low
4. Dependencies MUST be exactly: **Dependencies:** US-XXX, US-YYY or None
5. Acceptance criteria MUST use: - [ ] format (checkbox)
6. Each user story MUST have Description and Acceptance Criteria sections

## TASK SIZING GUIDELINES
- Break large features into 3-7 user stories
- Each user story should be completable in 1-3 iterations
- Acceptance criteria should be specific and testable
- Order user stories by dependency (independent first)

Now generate the PRD (output ONLY the markdown, no explanations):
'''

# Plans Generation Template
PLANS_GENERATION_TEMPLATE = '''You are a technical architect creating phased implementation plans.

## USER REQUEST
{user_prompt}

## ADDITIONAL CONTEXT
{additional_context}

## OUTPUT REQUIREMENTS

Generate a set of implementation plan files. Output each file as:

===FILE: {{filename}}===
{{file content}}
===END FILE===

## FILE STRUCTURE

### File 1: 00-overview.md
```markdown
# {{Project Name}} - Master Plan

## Objective
{{Clear project goal in 1-2 sentences}}

## Scope
- **Target**: {{What will be built}}
- **Codebase**: {{Affected directories/modules}}

## Phased Approach

| Phase | Name | Description | Plan File |
|-------|------|-------------|-----------|
| 1 | {{Phase 1}} | {{Brief desc}} | `01-{{slug}}.md` |
| 2 | {{Phase 2}} | {{Brief desc}} | `02-{{slug}}.md` |

## Success Criteria
- [ ] {{Measurable criterion 1}}
- [ ] {{Measurable criterion 2}}

## Execution Order
Execute phases sequentially.
```

### File 2+: NN-phase-name.md
```markdown
# Phase {{N}}: {{Phase Name}}

## Objective
{{What this phase accomplishes}}

## Tasks

### {{N}}.1 {{Task Group Name}}
- [ ] TASK-{{N}}01: {{Task description}}
  - Priority: High
  - Description: {{Detailed description}}

- [ ] TASK-{{N}}02: {{Task description}}
  - Priority: Medium
  - Dependencies: TASK-{{N}}01

### {{N}}.2 {{Another Task Group}}
- [ ] TASK-{{N}}03: {{Task description}}

## Verification
- [ ] {{How to verify phase is complete}}

## Next Phase
Proceed to Phase {{N+1}} after completing all tasks.
```

## CRITICAL FORMAT RULES
1. Task IDs: TASK-{{PHASE}}{{SEQ}} (e.g., TASK-101, TASK-201)
2. Checkboxes: - [ ] for pending, - [x] for completed
3. Priority: - Priority: High|Medium|Low
4. Dependencies: - Dependencies: TASK-XXX, TASK-YYY
5. Description: - Description: {{text}}
6. Each phase file MUST have: Objective, Tasks, Verification sections

## TASK SIZING GUIDELINES
- {num_phases} phases for this project (or auto-determine if not specified)
- 5-10 tasks per phase
- Tasks should be atomic (completable in one iteration)
- Clear dependencies between tasks

Now generate the plan files (output ONLY the file markers and content, no explanations):
'''

# PRD to Plans Conversion Template
PRD_TO_PLANS_TEMPLATE = '''You are a technical architect converting a PRD \
into phased implementation plans.

## INPUT PRD
{prd_content}

## OUTPUT REQUIREMENTS

Convert the PRD user stories into phased implementation plans.

Generate plan files using this format:

===FILE: {{filename}}===
{{file content}}
===END FILE===

## CONVERSION RULES
1. Group related user stories into phases
2. Convert each user story into specific implementation tasks
3. Preserve priority ordering
4. Maintain dependencies between tasks
5. Each acceptance criterion may become a sub-task

## PHASE STRUCTURE
- Phase 1: Foundation/Setup tasks
- Phase 2-N: Feature implementation (grouped by user stories)
- Final Phase: Testing and verification

## TASK ID MAPPING
- US-001 tasks -> TASK-101, TASK-102, etc.
- US-002 tasks -> TASK-201, TASK-202, etc.

{additional_context}

Now generate the plan files:
'''

# Context injection helpers
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
    """
    Format a generation template with user input.

    Args:
        template: Template string
        user_prompt: User's prompt/request
        additional_context: Additional context to inject
        num_phases: Optional number of phases
        **kwargs: Additional format arguments

    Returns:
        Formatted prompt string
    """
    phases_str = str(num_phases) if num_phases else "3-5"

    return template.format(
        user_prompt=user_prompt,
        additional_context=additional_context or "None specified",
        num_phases=phases_str,
        **kwargs
    )
