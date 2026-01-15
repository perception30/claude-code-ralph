"""AI prompt templates for PRD and plans generation."""

# PRD Generation Template - Claude writes directly to file
# Uses plan-style format for consistency and direct executability
PRD_GENERATION_TEMPLATE = '''You are a technical product manager creating a PRD.

## USER REQUEST
{user_prompt}

## OUTPUT DIRECTORY
Write plan files to: {output_path}

## INSTRUCTIONS
Create a PRD using the phased plan format for direct executability:

1. Create a directory structure with:
   - 00-overview.md - Project overview with phase summary table
   - 01-phase-name.md, 02-phase-name.md, etc. - Individual phase files

2. The 00-overview.md should include:
   - # Project title
   - ## Overview (project description, goals, scope)
   - ## User Stories (brief user story context for each phase)
   - ## Phase Summary (table with phase names and status)

3. Each phase file (01-xxx.md, 02-xxx.md) should have:
   - ## Objective (what this phase achieves)
   - ## User Story Context (the user story this phase addresses)
   - ## Tasks with checkboxes:
     - [ ] TASK-N01: Description
       - Priority: High/Medium/Low
       - Dependencies: none or TASK-XXX
       - Description: Detailed implementation notes
   - ## Verification (how to verify phase completion)

4. CRITICAL - Task IDs must be GLOBALLY UNIQUE across all files:
   - Phase 1: TASK-101, TASK-102, TASK-103, etc.
   - Phase 2: TASK-201, TASK-202, TASK-203, etc.
   - Phase 3: TASK-301, TASK-302, TASK-303, etc.

5. Write all files directly to the output directory

6. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-prd"}}

## CRITICAL: TASK GRANULARITY
Tasks MUST be LARGE and COARSE-GRAINED. Each task should represent a substantial unit of work:
- **Minimum scope**: Each task should take 2-8 hours of focused work
- **Maximum tasks per phase**: 3-5 tasks (NOT 8-10)
- **Maximum total tasks**: 10-20 for the entire PRD (NOT 50-60)
- **Group related work**: Combine related sub-tasks into single larger tasks
- **One iteration per task**: Each task will be one Claude iteration, so make them comprehensive

BAD (too granular):
- TASK-101: Install Inter font
- TASK-102: Configure font weights
- TASK-103: Set up CSS variable
- TASK-104: Add fallback fonts

GOOD (properly sized):
- TASK-101: Set up complete typography foundation (font installation, weights, CSS variables, fallbacks)

Before creating the PRD, review all the relevant code paths/modules and deep analyze to gather context and understand the scope of the request. Ask users for clarifications if there are any gaps in understanding, or ambiguous requirements.

Then, create the PRD files.
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

3. CRITICAL - Task IDs must be GLOBALLY UNIQUE across all files:
   - Phase 1: TASK-101, TASK-102, TASK-103, etc.
   - Phase 2: TASK-201, TASK-202, TASK-203, etc.
   - Phase 3: TASK-301, TASK-302, TASK-303, etc.
   - Never reuse task IDs across different phases or files

4. Write all files directly to the output directory

5. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-plans"}}

## CRITICAL: TASK GRANULARITY
Tasks MUST be LARGE and COARSE-GRAINED. Each task should represent a substantial unit of work:
- **Minimum scope**: Each task should take 2-8 hours of focused work
- **Maximum tasks per phase**: 3-5 tasks (NOT 8-10)
- **Maximum total tasks**: 10-20 for the entire plan (NOT 50-60)
- **Group related work**: Combine related sub-tasks into single larger tasks
- **One iteration per task**: Each task will be one Claude iteration, so make them comprehensive

BAD (too granular):
- TASK-101: Create Button component
- TASK-102: Add Button variants
- TASK-103: Add Button sizes
- TASK-104: Add Button tests

GOOD (properly sized):
- TASK-101: Implement complete Button component with all variants, sizes, states, and tests

Before creating the phased plan files, review all the relevant code paths/modules and deep analyze to gather context and understand the scope of the request. Ask users for clarifications if there are any gaps in understanding, or ambiguous requirements.

Then, proceed to create the phased plan files.
'''

# PRD to Plans Conversion Template
# Used when PRD exists in legacy format or needs restructuring
PRD_TO_PLANS_TEMPLATE = '''You are a technical architect refining a PRD into execution-ready plans.

## INPUT PRD
{prd_content}

## OUTPUT DIRECTORY
Write plan files to: {output_path}

## INSTRUCTIONS
Analyze the PRD and create/refine phased execution plans:

1. If PRD already uses phased format, refine and enhance:
   - Ensure task granularity is appropriate (1-4 hours each)
   - Add missing dependencies between tasks
   - Ensure verification steps are concrete and testable

2. If PRD uses legacy user-story format, convert to phased plans:
   - Group user stories into logical implementation phases
   - Break down acceptance criteria into discrete tasks
   - Add technical implementation details

3. Create/update plan files:
   - 00-overview.md - Master overview with phase table
   - 01-phase-name.md, 02-phase-name.md, etc. - Phase files

4. Each phase file must have:
   - ## Objective
   - ## Tasks with checkboxes:
     - [ ] TASK-N01: Description
       - Priority: High/Medium/Low
       - Dependencies: none or TASK-XXX
       - Description: Implementation details
   - ## Verification

5. CRITICAL - Task IDs must be GLOBALLY UNIQUE across all files:
   - Phase 1: TASK-101, TASK-102, TASK-103, etc.
   - Phase 2: TASK-201, TASK-202, TASK-203, etc.
   - Phase 3: TASK-301, TASK-302, TASK-303, etc.
   - Never reuse task IDs across different phases or files

6. When done, write status to `.ralph/status.json`:
   {{"status": "COMPLETED", "task_id": "generate-plans"}}

## CRITICAL: TASK GRANULARITY
Tasks MUST be LARGE and COARSE-GRAINED. Each task should represent a substantial unit of work:
- **Minimum scope**: Each task should take 2-8 hours of focused work
- **Maximum tasks per phase**: 3-5 tasks (NOT 8-10)
- **Maximum total tasks**: 10-20 for the entire plan (NOT 50-60)
- **Group related work**: Combine related sub-tasks into single larger tasks
- **One iteration per task**: Each task will be one Claude iteration, so make them comprehensive

When refining, CONSOLIDATE granular tasks into larger ones rather than keeping them separate.

Now create the plan files.
'''
