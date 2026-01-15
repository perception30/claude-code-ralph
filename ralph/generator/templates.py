"""AI prompt templates for PRD and plans generation."""

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
