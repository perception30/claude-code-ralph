# Ralph CLI - Robust Autonomous Agent Platform

## Vision

Ralph is a production-grade CLI for running Claude as an autonomous software engineering agent. It takes a PRD, plan files, or custom prompts and iteratively implements them until completion, tracking progress and updating status along the way.

---

## Core Requirements

### 1. Flexible Input Sources

Users should be able to provide work in multiple formats:

```bash
# Custom prompt
ralph run --prompt "Implement user authentication with JWT"

# Single PRD file
ralph run --prd ./docs/PRD.md

# Plan files directory
ralph run --plans ./plans/

# Specific plan files
ralph run --files plan1.md plan2.md plan3.md

# JSON task definition
ralph run --config ./ralph.json

# Interactive mode (prompts for input)
ralph run -i
```

### 2. State Management & Progress Tracking

Ralph must track implementation status persistently:

- **Task States**: `pending` → `in_progress` → `completed` | `blocked` | `failed`
- **Progress File**: `.ralph/state.json` - tracks all task states
- **Plan Updates**: Automatically update checkboxes/status in source files
- **Resume Capability**: Continue from where it left off after interruption

### 3. Completion Detection

Multiple strategies for detecting completion:

- **Checkbox Parsing**: Count `[x]` vs `[ ]` in plan files
- **Status Markers**: Look for `## Status: COMPLETED` in files
- **AI Self-Report**: Claude reports completion via structured output
- **File Flag**: Create completion flag file (current approach)
- **All Tasks Done**: All parsed tasks marked complete in state

### 4. Robust Error Handling

- Retry failed iterations with exponential backoff
- Graceful degradation on partial failures
- Detailed error logging with context
- Recovery suggestions for common issues

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RALPH CLI                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Inputs     │    │   Parser     │    │   Planner    │               │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤               │
│  │ • PRD.md     │───▶│ • Markdown   │───▶│ • Prioritize │               │
│  │ • Plans/*.md │    │ • JSON       │    │ • Sequence   │               │
│  │ • --prompt   │    │ • YAML       │    │ • Deps       │               │
│  │ • --config   │    │ • Checkboxes │    │              │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                 │                        │
│                                                 ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Reporter   │    │   Executor   │    │    State     │               │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤               │
│  │ • Rich UI    │◀───│ • Claude     │◀──▶│ • Tasks      │               │
│  │ • Progress   │    │ • Streaming  │    │ • Progress   │               │
│  │ • Logs       │    │ • Retry      │    │ • History    │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Module Design

### 1. `ralph/input/` - Input Handlers

```
ralph/input/
├── __init__.py
├── base.py          # Abstract InputSource class
├── prompt.py        # --prompt "string" handler
├── prd.py           # --prd file.md handler (parses PRD format)
├── plans.py         # --plans dir/ handler (multiple plan files)
├── config.py        # --config file.json handler
└── interactive.py   # -i interactive mode
```

**Responsibilities:**
- Parse different input formats into unified Task structure
- Extract phases, tasks, dependencies, priorities
- Validate input completeness

### 2. `ralph/parser/` - Document Parsers

```
ralph/parser/
├── __init__.py
├── markdown.py      # Parse markdown plans/PRDs
├── json_parser.py   # Parse JSON task definitions
├── yaml_parser.py   # Parse YAML configs
└── checkbox.py      # Parse/update checkbox status
```

**Markdown Parser Features:**
- Extract headers as phases (`# Phase 1`, `## Task 1.1`)
- Parse checkboxes (`- [ ]`, `- [x]`)
- Extract metadata (priority, dependencies, estimates)
- Parse status markers (`Status: IN_PROGRESS`)

### 3. `ralph/state/` - State Management

```
ralph/state/
├── __init__.py
├── models.py        # Task, Phase, Project dataclasses
├── store.py         # StateStore - persistence layer
├── tracker.py       # ProgressTracker - status updates
└── history.py       # IterationHistory - audit log
```

**State File (`.ralph/state.json`):**
```json
{
  "version": "1.0",
  "project": "my-project",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T12:30:00Z",
  "status": "in_progress",
  "phases": [
    {
      "id": "phase-1",
      "name": "Setup",
      "status": "completed",
      "tasks": [
        {
          "id": "task-1.1",
          "name": "Initialize project",
          "status": "completed",
          "completed_at": "2025-01-15T10:15:00Z",
          "iteration": 1
        }
      ]
    }
  ],
  "iterations": [
    {
      "number": 1,
      "started_at": "2025-01-15T10:00:00Z",
      "ended_at": "2025-01-15T10:20:00Z",
      "tasks_completed": ["task-1.1", "task-1.2"],
      "status": "success"
    }
  ],
  "current_iteration": 3,
  "total_tasks": 25,
  "completed_tasks": 12
}
```

### 4. `ralph/executor/` - Claude Execution

```
ralph/executor/
├── __init__.py
├── runner.py        # ClaudeRunner - pexpect wrapper
├── prompt.py        # PromptBuilder - dynamic prompt generation
├── output.py        # OutputParser - parse Claude's responses
└── retry.py         # RetryStrategy - exponential backoff
```

**Dynamic Prompt Generation:**
```python
class PromptBuilder:
    def build(self, context: ExecutionContext) -> str:
        """Build prompt with current state context."""
        return f"""
You are Ralph, an autonomous coding agent.

## Current Project State
{self._format_progress(context.state)}

## Your Current Task
{self._format_current_task(context.next_task)}

## Instructions
1. Implement the current task completely
2. Run quality checks (test, lint, typecheck)
3. Commit changes with message: feat: {context.next_task.id} - {context.next_task.name}
4. Report completion status

## Output Format
When done, output:
TASK_COMPLETED: {context.next_task.id}

If all tasks are done:
ALL_PHASES_COMPLETED
"""
```

### 5. `ralph/ui/` - User Interface

```
ralph/ui/
├── __init__.py
├── console.py       # Rich console wrapper
├── banner.py        # ASCII art banner
├── progress.py      # Progress bars and spinners
├── panels.py        # Info panels (config, status)
├── tables.py        # Task tables
└── live.py          # Live updating display
```

**Rich UI Features:**
- ASCII banner with version
- Configuration panel
- Live progress bar (tasks completed / total)
- Current task highlight
- Streaming Claude output
- Iteration summary panels
- Error panels with suggestions

### 6. `ralph/cli/` - CLI Commands

```
ralph/cli/
├── __init__.py
├── main.py          # Typer app entry
├── run.py           # ralph run command
├── init.py          # ralph init command
├── status.py        # ralph status command
├── resume.py        # ralph resume command
├── history.py       # ralph history command
└── validate.py      # ralph validate command
```

**Commands:**
```bash
ralph run [OPTIONS]        # Run autonomous agent
ralph init                 # Initialize project
ralph status               # Show current progress
ralph resume               # Resume interrupted session
ralph history              # Show iteration history
ralph validate FILE        # Validate plan/PRD file
ralph tasks                # List all tasks with status
ralph reset                # Reset state (start fresh)
```

---

## CLI Interface Design

### `ralph run` - Main Command

```bash
ralph run [OPTIONS]

Input Sources (mutually exclusive):
  --prompt, -p TEXT        Custom prompt to execute
  --prd FILE               PRD markdown file
  --plans DIR              Directory containing plan files
  --files FILE...          Specific plan files
  --config FILE            JSON/YAML config file

Execution Options:
  --max, -m INT            Max iterations [default: 50]
  --timeout, -t INT        Idle timeout seconds [default: 60]
  --sleep, -s INT          Sleep between iterations [default: 2]
  --retry INT              Max retries on failure [default: 3]
  --model TEXT             Claude model to use

Output Options:
  --quiet, -q              Minimal output
  --verbose, -v            Verbose output
  --log-file FILE          Write logs to file
  --no-stream              Don't stream Claude output

Behavior Options:
  --dry-run                Parse and plan but don't execute
  --no-commit              Don't auto-commit changes
  --no-state               Don't persist state
  --yes, -y                Auto-confirm prompts

Examples:
  ralph run --prd ./PRD.md
  ralph run --plans ./phases/ -m 20
  ralph run -p "Add dark mode to the app"
  ralph run --config ./ralph.json --verbose
```

### `ralph status` - Progress Status

```bash
ralph status [OPTIONS]

Options:
  --json                   Output as JSON
  --detailed               Show all tasks

Output:
┌─────────────────────────────────────────────────────────────┐
│                    Ralph Status                              │
├─────────────────────────────────────────────────────────────┤
│  Project: math-app-claude                                    │
│  Status:  IN PROGRESS                                        │
│                                                              │
│  Progress: ████████████░░░░░░░░ 60% (15/25 tasks)           │
│                                                              │
│  Phases:                                                     │
│    ✓ Phase 1: Setup (5/5)                                   │
│    ✓ Phase 2: Core Features (5/5)                           │
│    → Phase 3: UI Polish (3/8) ← current                     │
│    ○ Phase 4: Testing (0/4)                                 │
│    ○ Phase 5: Deployment (0/3)                              │
│                                                              │
│  Current Task: Implement dark mode toggle                    │
│  Iterations: 12 completed                                    │
│  Runtime: 2h 34m                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Task/Phase Data Models

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Task:
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    phase_id: Optional[str] = None

    # Tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    iteration: Optional[int] = None
    attempts: int = 0
    error: Optional[str] = None

    # Source location for updating
    source_file: Optional[str] = None
    source_line: Optional[int] = None

@dataclass
class Phase:
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    tasks: list[Task] = field(default_factory=list)
    priority: int = 0

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

@dataclass
class Project:
    name: str
    phases: list[Phase] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def total_tasks(self) -> int:
        return sum(len(p.tasks) for p in self.phases)

    @property
    def completed_tasks(self) -> int:
        return sum(
            1 for p in self.phases
            for t in p.tasks
            if t.status == TaskStatus.COMPLETED
        )

    @property
    def progress(self) -> float:
        total = self.total_tasks
        return self.completed_tasks / total if total > 0 else 0.0

    def get_next_task(self) -> Optional[Task]:
        """Get the next task to work on based on priority and dependencies."""
        for phase in sorted(self.phases, key=lambda p: p.priority):
            for task in sorted(phase.tasks, key=lambda t: t.priority):
                if task.status == TaskStatus.PENDING:
                    # Check dependencies
                    if self._dependencies_met(task):
                        return task
        return None

    def _dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies are completed."""
        for dep_id in task.dependencies:
            dep_task = self.get_task_by_id(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
```

---

## Markdown Plan Format

Ralph should parse this format:

```markdown
# Project: E-commerce Platform

## Phase 1: Foundation
Priority: 1
Status: IN_PROGRESS

### Tasks

- [x] US-001: Set up project structure
  - Priority: 1
  - Description: Initialize Next.js project with TypeScript

- [x] US-002: Configure database
  - Priority: 1
  - Dependencies: US-001

- [ ] US-003: Create user model
  - Priority: 2
  - Dependencies: US-002
  - Description: |
      Create User model with fields:
      - id, email, password, name, role, createdAt

## Phase 2: Authentication
Priority: 2
Status: PENDING

### Tasks

- [ ] US-004: Implement signup
  - Dependencies: US-003

- [ ] US-005: Implement login
  - Dependencies: US-003

- [ ] US-006: Add password reset
  - Dependencies: US-004, US-005
```

---

## PRD Format Support

Ralph should also parse PRD format:

```markdown
# Product Requirements Document: Feature Name

## Overview
Brief description of the feature.

## User Stories

### US-001: As a user, I want to sign up
**Priority:** High
**Status:** Pending

#### Acceptance Criteria
- [ ] User can enter email and password
- [ ] Validation for email format
- [ ] Password strength requirements
- [ ] Confirmation email sent

#### Technical Notes
Use NextAuth.js for authentication.

### US-002: As a user, I want to log in
**Priority:** High
**Status:** Pending
**Dependencies:** US-001

#### Acceptance Criteria
- [ ] User can log in with email/password
- [ ] Remember me option
- [ ] Redirect to dashboard after login
```

---

## Configuration File Format

`ralph.json` or `.ralph/config.json`:

```json
{
  "version": "1.0",
  "project": {
    "name": "my-project",
    "description": "Project description"
  },
  "input": {
    "type": "plans",
    "path": ".ide/tasks/plans",
    "pattern": "*.md"
  },
  "execution": {
    "max_iterations": 50,
    "idle_timeout": 60,
    "sleep_between": 2,
    "retry_attempts": 3,
    "retry_delay": 5
  },
  "claude": {
    "model": "opus",
    "skip_permissions": true,
    "custom_instructions": "Additional context for Claude..."
  },
  "output": {
    "log_dir": ".ralph/logs",
    "state_file": ".ralph/state.json",
    "verbose": false
  },
  "hooks": {
    "before_iteration": "npm run lint",
    "after_iteration": "npm run test",
    "on_complete": "npm run build"
  },
  "completion": {
    "flag_file": "/tmp/ralph_complete.flag",
    "update_source": true,
    "commit_changes": true,
    "commit_prefix": "feat:"
  }
}
```

---

## Implementation Phases

### Phase 1: Core Refactor (Foundation)
- [ ] Restructure into modular architecture
- [ ] Implement Task/Phase/Project data models
- [ ] Create StateStore for persistence
- [ ] Add markdown parser for plans
- [ ] Update CLI with new input options

### Phase 2: Input Flexibility
- [ ] Implement --prompt handler
- [ ] Implement --prd parser
- [ ] Implement --plans directory scanner
- [ ] Implement --config JSON/YAML loader
- [ ] Add input validation

### Phase 3: State Management
- [ ] Implement persistent state in `.ralph/state.json`
- [ ] Add progress tracking per task
- [ ] Implement resume capability
- [ ] Add iteration history
- [ ] Source file status updates (checkboxes)

### Phase 4: Enhanced UI
- [ ] Add progress bar (completed/total tasks)
- [ ] Show current phase and task
- [ ] Add task table view
- [ ] Implement status command
- [ ] Add history command

### Phase 5: Robustness
- [ ] Add retry logic with exponential backoff
- [ ] Implement proper error handling
- [ ] Add validation command
- [ ] Add dry-run mode
- [ ] Comprehensive logging

### Phase 6: Advanced Features
- [ ] Dependency resolution
- [ ] Priority-based task selection
- [ ] Hooks (before/after iteration)
- [ ] Custom completion detection
- [ ] Parallel task execution (future)

---

## File Structure

```
ralph/
├── __init__.py
├── __main__.py
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer app
│   ├── run.py               # run command
│   ├── status.py            # status command
│   ├── init.py              # init command
│   ├── resume.py            # resume command
│   ├── history.py           # history command
│   ├── tasks.py             # tasks command
│   ├── validate.py          # validate command
│   └── reset.py             # reset command
├── input/
│   ├── __init__.py
│   ├── base.py              # InputSource ABC
│   ├── prompt.py            # Prompt input
│   ├── prd.py               # PRD parser
│   ├── plans.py             # Plans directory
│   └── config.py            # Config file
├── parser/
│   ├── __init__.py
│   ├── markdown.py          # Markdown parser
│   ├── checkbox.py          # Checkbox parser/updater
│   └── json_parser.py       # JSON parser
├── state/
│   ├── __init__.py
│   ├── models.py            # Task, Phase, Project
│   ├── store.py             # StateStore
│   ├── tracker.py           # ProgressTracker
│   └── history.py           # IterationHistory
├── executor/
│   ├── __init__.py
│   ├── runner.py            # ClaudeRunner
│   ├── prompt.py            # PromptBuilder
│   ├── output.py            # OutputParser
│   └── retry.py             # RetryStrategy
├── ui/
│   ├── __init__.py
│   ├── console.py           # Rich console
│   ├── banner.py            # ASCII banner
│   ├── progress.py          # Progress bars
│   ├── panels.py            # Info panels
│   ├── tables.py            # Task tables
│   └── live.py              # Live display
└── utils/
    ├── __init__.py
    ├── files.py             # File utilities
    ├── git.py               # Git operations
    └── logging.py           # Logging setup
```

---

## Success Criteria

1. **Flexible Input**: Accept prompts, PRDs, plans, configs
2. **Persistent State**: Track progress across sessions
3. **Visual Progress**: Show completion percentage and current task
4. **Resumable**: Continue from interruption point
5. **Reliable**: Retry on failure, graceful error handling
6. **Updatable**: Update source files with completion status
7. **Configurable**: All behavior customizable via config/CLI
8. **Observable**: Rich UI, detailed logs, status commands

---

## Example Usage Scenarios

### Scenario 1: Quick Task
```bash
ralph run -p "Add a logout button to the navbar that clears the session"
```

### Scenario 2: PRD Implementation
```bash
ralph run --prd ./docs/user-auth-prd.md -m 30
```

### Scenario 3: Phased Development
```bash
ralph run --plans ./.ide/tasks/plans/ --verbose
```

### Scenario 4: Resume After Break
```bash
ralph resume  # Continues from last state
```

### Scenario 5: Check Progress
```bash
ralph status --detailed
```

---

## Next Steps

1. Review and approve this plan
2. Start Phase 1 implementation
3. Iterate based on testing feedback
