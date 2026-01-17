# Ralph

**Run Claude as an autonomous coding agent.** Give it a task, and watch it work through your entire codebase.

[![PyPI version](https://img.shields.io/pypi/v/ralph-agent.svg)](https://pypi.org/project/ralph-agent/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Quick Start (30 seconds)

```bash
# Install
pipx install ralph-agent  # or: pip install ralph-agent

# Run with a simple prompt
ralph run --prompt "Add a dark mode toggle to the settings page"
```

That's it. Ralph will autonomously implement the feature, make commits, and report when done.

---

## Table of Contents

- [Installation](#installation)
- [Usage Patterns](#usage-patterns)
  - [Single Task](#1-single-task-simplest)
  - [Multi-Phase Project](#2-multi-phase-project-recommended)
  - [Generate from Idea](#3-generate-from-idea-full-workflow)
- [Commands Reference](#commands-reference)
- [Plan File Format](#plan-file-format)
- [Configuration](#configuration)
- [How It Works](#how-it-works)

---

## Installation

### From PyPI (Recommended)

```bash
# Using pipx (recommended for CLI tools)
pipx install ralph-agent

# Or using pip
pip install ralph-agent
```

### From Source

```bash
git clone https://github.com/anthropics/ralph-agent.git
cd ralph-agent
pip install -e .
```

### Requirements

- Python 3.9+
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- macOS or Linux

---

## Usage Patterns

### 1. Single Task (Simplest)

Run a one-off task immediately:

```bash
ralph run --prompt "Add input validation to the login form"
```

### 2. Multi-Phase Project (Recommended)

For larger features, break work into phases and tasks:

**Step 1:** Initialize Ralph in your project

```bash
cd your-project
ralph init
```

**Step 2:** Edit `.ide/tasks/plans/00-overview.md`

```markdown
# Project: User Authentication

## Phase 1: Setup
- [ ] TASK-101: Create user database schema
- [ ] TASK-102: Set up authentication middleware

## Phase 2: Implementation
- [ ] TASK-201: Build login endpoint
- [ ] TASK-202: Build registration endpoint
- [ ] TASK-203: Add password reset flow

## Phase 3: Testing
- [ ] TASK-301: Write unit tests
- [ ] TASK-302: Add integration tests
```

**Step 3:** Run Ralph

```bash
ralph run
```

Ralph will work through each task, checking off boxes as it completes them.

**Step 4:** Monitor progress

```bash
ralph status          # Quick summary
ralph tasks           # See all tasks
ralph history         # View iteration log
```

### 3. Generate from Idea (Full Workflow)

Let Claude help you plan before executing:

```bash
# Step 1: Generate a PRD from your idea
ralph generate prd --prompt "Build a REST API for task management with teams"

# Step 2: Review PRDs/, edit if needed

# Step 3: Run directly on PRD directory
ralph run --prd ./PRDs/

# OR: Convert PRD to executable plans first
ralph generate plans --from-prd ./PRDs/
ralph run --plans ./plans/
```

---

## Commands Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ralph run` | Execute tasks | `ralph run --prompt "Fix the bug"` |
| `ralph status` | Show progress | `ralph status --detailed` |
| `ralph resume` | Continue interrupted work | `ralph resume` |

### Generation Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ralph generate prd` | Create PRD from prompt | `ralph generate prd -p "Auth system"` |
| `ralph generate plans` | Create phased plans | `ralph generate plans --from-prd ./PRD.md` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ralph init` | Initialize project | `ralph init` |
| `ralph tasks` | List all tasks | `ralph tasks --status pending` |
| `ralph history` | Show iteration log | `ralph history -n 20` |
| `ralph projects` | List all projects | `ralph projects` |
| `ralph validate` | Check plan file | `ralph validate ./plan.md` |
| `ralph reset` | Clear state | `ralph reset --yes` |

---

### `ralph run`

The main command. Runs Claude autonomously on your tasks.

```bash
ralph run [OPTIONS]
```

**Input Options** (pick one):

| Option | Description |
|--------|-------------|
| `--prompt, -p` | Direct task description |
| `--plans` | Directory of plan files |
| `--prd` | PRD markdown file or directory |
| `--files` | Specific plan files |
| `--config, -c` | JSON config file |
| `--id` | Resume project by ID (full or partial) |
| `--name` | Resume project by name |

**Execution Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--max, -m` | 50 | Max iterations |
| `--timeout, -t` | 60 | Seconds to wait for Claude |
| `--model` | - | Claude model to use |
| `--dry-run` | - | Preview without executing |
| `--no-commit` | - | Skip auto-commits |
| `--yes, -y` | - | Auto-confirm prompts |

**Examples:**

```bash
# Simple prompt
ralph run -p "Add logout button"

# From PRD file (single file)
ralph run --prd ./docs/PRD.md

# From PRD directory (generated format)
ralph run --prd ./PRDs/

# From plans directory
ralph run --plans ./my-feature/

# With custom settings
ralph run --plans ./plans/ --max 100 --timeout 120

# Preview only (no execution)
ralph run --plans ./plans/ --dry-run

# Auto-confirm all prompts
ralph run --plans ./plans/ --yes

# Resume by project ID (from ralph projects)
ralph run --id abc123de

# Resume by project name
ralph run --name "auth service"
```

**Resume Workflow:**

```bash
# List all projects with their IDs
$ ralph projects
ID       Name      Status       Progress
abc123.. auth      in_progress  5/10
def456.. payments  pending      0/8

# Resume by ID (partial match works)
$ ralph run --id abc123

# Or resume by name
$ ralph run --name auth
```

---

### `ralph generate prd`

Generate a Product Requirements Document from a natural language description.

```bash
ralph generate prd [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--prompt, -p` | Feature description |
| `--from-file, -f` | Read prompt from file |
| `--output, -o` | Output directory (default: `./PRDs`) |
| `--name, -n` | Project name |
| `--dry-run` | Preview prompt only |

**Examples:**

```bash
# From prompt
ralph generate prd -p "User authentication with OAuth and JWT"

# From file
ralph generate prd -f ./requirements.txt -o ./docs/PRD.md

# Preview what will be sent to Claude
ralph generate prd -p "New feature" --dry-run
```

---

### `ralph generate plans`

Generate phased implementation plans from a prompt or PRD.

```bash
ralph generate plans [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--prompt, -p` | Feature description |
| `--from-file, -f` | Read prompt from file |
| `--from-prd` | Convert existing PRD to plans |
| `--output, -o` | Output directory (default: `./plans`) |
| `--phases` | Number of phases (default: auto) |
| `--max-tasks` | Max tasks per phase (default: 10) |
| `--dry-run` | Preview prompt only |

**Examples:**

```bash
# From prompt
ralph generate plans -p "Refactor authentication system"

# From PRD file
ralph generate plans --from-prd ./PRD.md -o ./.ide/tasks/plans/

# Specify number of phases
ralph generate plans -p "Build REST API" --phases 4
```

---

### `ralph status`

Show current project progress.

```bash
ralph status [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--detailed` | Show all tasks |
| `--json` | Output as JSON |
| `--dir, -d` | Working directory |

---

### `ralph tasks`

List all tasks with their status.

```bash
ralph tasks [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--status` | Filter: `pending`, `completed`, `failed`, `blocked` |
| `--dir, -d` | Working directory |

**Examples:**

```bash
ralph tasks                    # All tasks
ralph tasks --status pending   # Only pending
ralph tasks --status completed # Only completed
```

---

### `ralph resume`

Continue an interrupted session.

```bash
ralph resume [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--max, -m` | 50 | Additional iterations |
| `--dir, -d` | `.` | Working directory |

> **Tip:** You can also just re-run the original command. Ralph auto-detects and resumes.

---

## Plan File Format

Ralph parses markdown files with phases and tasks:

```markdown
# Project: My Feature

## Phase 1: Setup
- [ ] TASK-101: Initialize project structure
- [ ] TASK-102: Configure dependencies

## Phase 2: Core Implementation
- [ ] TASK-201: Build the main component
- [ ] TASK-202: Add state management
- [ ] TASK-203: Connect to API

## Phase 3: Polish
- [ ] TASK-301: Add error handling
- [ ] TASK-302: Write tests
- [ ] TASK-303: Update documentation
```

### Task ID Convention

Use globally unique IDs across all files:

- Phase 1: `TASK-101`, `TASK-102`, `TASK-103`
- Phase 2: `TASK-201`, `TASK-202`, `TASK-203`
- Phase 3: `TASK-301`, `TASK-302`, `TASK-303`

### Task Metadata (Optional)

Add details under each task:

```markdown
- [ ] TASK-101: Create user authentication
  - Priority: High
  - Description: Implement JWT-based auth with refresh tokens
  - Dependencies: TASK-100
```

---

## Configuration

### Config File (`ralph.json`)

Create a config file for repeated use:

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
    "retry_attempts": 3
  },
  "claude": {
    "model": "opus",
    "skip_permissions": true
  },
  "completion": {
    "update_source": true,
    "commit_changes": true,
    "commit_prefix": "feat:"
  }
}
```

Then run:

```bash
ralph run --config ./ralph.json
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH EXECUTION LOOP                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. PARSE          2. SELECT          3. EXECUTE           │
│   ┌─────────┐       ┌─────────┐       ┌─────────┐          │
│   │  Plans  │──────▶│  Next   │──────▶│ Claude  │          │
│   │  /PRD   │       │  Task   │       │   CLI   │          │
│   └─────────┘       └─────────┘       └─────────┘          │
│                                             │               │
│   6. REPEAT         5. UPDATE          4. PARSE            │
│   ┌─────────┐       ┌─────────┐       ┌─────────┐          │
│   │  Next   │◀──────│  Mark   │◀──────│ Output  │          │
│   │  Task   │       │  Done   │       │ Stream  │          │
│   └─────────┘       └─────────┘       └─────────┘          │
│                                                              │
│                     ✓ All tasks complete                     │
└─────────────────────────────────────────────────────────────┘
```

1. **Parse** - Read plans, PRD, or prompt
2. **Select** - Pick the next pending task
3. **Execute** - Run Claude with task context
4. **Parse** - Monitor output for completion
5. **Update** - Mark task done, update checkboxes
6. **Repeat** - Continue until all tasks complete

---

## Multi-Project Support

Ralph tracks multiple projects independently:

```bash
# Work on feature A
ralph run --plans ./feature-a/

# Work on feature B (separate state)
ralph run --plans ./feature-b/

# See all projects
ralph projects
```

Each input source gets isolated state in `.ralph/projects/`.

---

## Tips & Best Practices

### Writing Good Tasks

```markdown
# Good - Specific and actionable
- [ ] TASK-101: Add email validation to signup form with error messages

# Bad - Too vague
- [ ] TASK-101: Fix signup
```

### Handling Interruptions

If Ralph is interrupted (Ctrl+C, timeout, etc.):

```bash
# Option 1: Run the same command again (re-parses files)
ralph run --plans ./my-feature/

# Option 2: Resume by ID (uses saved state)
ralph projects                    # Find your project ID
ralph run --id abc123de           # Resume from saved state

# Option 3: Resume by name
ralph run --name "my feature"

# Or use resume
ralph resume
```

Ralph automatically continues from where it stopped.

### Dry Run First

Preview what will happen before executing:

```bash
ralph run --plans ./plans/ --dry-run
```

### Monitor Long Runs

In another terminal:

```bash
watch ralph status --detailed
```

---

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Lint & format
make lint
make format

# Build package
make build
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
