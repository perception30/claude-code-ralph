# Ralph

**Autonomous Claude Code Agent Runner** - A production-ready Python CLI for running Claude as an autonomous software engineering agent.

[![PyPI version](https://badge.fury.io/py/ralph-agent.svg)](https://badge.fury.io/py/ralph-agent)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Flexible Input** - Run from prompts, PRD files, plan directories, or JSON configs
- **Persistent State** - Track progress across sessions in `.ralph/state.json`
- **Smart Parsing** - Parse markdown plans and PRDs to extract phases and tasks
- **Completion Detection** - Structured output markers for reliable task tracking
- **Auto Checkboxes** - Automatically update `[ ]` to `[x]` in source files
- **Retry Logic** - Exponential backoff with configurable retry attempts
- **Rich Terminal UI** - Beautiful progress bars, status panels, and task tables
- **Resume Capability** - Continue interrupted sessions from where you left off

## Installation

### From PyPI

```bash
pip install ralph-agent
```

### From Source

```bash
git clone https://github.com/yourusername/ralph-agent.git
cd ralph-agent
pip install -e .
```

## Quick Start

### Option 1: Direct Prompt (Fastest)

Run a single task immediately:

```bash
ralph run --prompt "Add a logout button to the navbar"
```

### Option 2: Initialize a Project (Recommended)

**Step 1:** Initialize Ralph in your project:

```bash
cd your-project
ralph init
```

This creates:
```
.ide/tasks/plans/       # Your plan files go here
.ralph/                 # State directory
.ide/ralph.json         # Configuration
```

**Step 2:** Edit the example plan file `.ide/tasks/plans/00-overview.md`:

```markdown
# Project: My Feature

## Phase 1: Setup
- [ ] Task 1: Initialize the component structure
- [ ] Task 2: Add basic styling

## Phase 2: Implementation
- [ ] Task 3: Implement core functionality
- [ ] Task 4: Add error handling

## Phase 3: Polish
- [ ] Task 5: Add tests
- [ ] Task 6: Update documentation
```

**Step 3:** Run Ralph:

```bash
ralph run
```

Ralph will:
1. Parse your plan files
2. Pick the first pending task
3. Run Claude to implement it
4. Mark the checkbox `[x]` when done
5. Repeat until all tasks complete

**Step 4:** Monitor progress:

```bash
# Check current status
ralph status

# See detailed task list
ralph tasks

# View iteration history
ralph history
```

### Option 3: Use a PRD File

```bash
ralph run --prd ./docs/my-feature-prd.md -m 30
```

### Option 4: Use a Config File

```bash
ralph run --config ./ralph.json
```

### Resuming Work

If interrupted (Ctrl+C or timeout), resume anytime:

```bash
ralph resume
```

### Dry Run (Preview Only)

See what tasks would be executed without running:

```bash
ralph run --plans ./phases/ --dry-run
```

## Commands

| Command | Description |
|---------|-------------|
| `ralph run` | Run autonomous agent with various input sources |
| `ralph init` | Initialize Ralph in a project |
| `ralph status` | Show current progress and phase status |
| `ralph resume` | Continue an interrupted session |
| `ralph history` | Show iteration history |
| `ralph tasks` | List all tasks with their status |
| `ralph validate` | Validate a plan or PRD file |
| `ralph reset` | Reset state and start fresh |

## Usage

### `ralph run` - Main Command

```bash
ralph run [OPTIONS]

Input Sources (choose one):
  --prompt, -p TEXT        Direct prompt to execute
  --prd FILE               PRD markdown file to parse
  --plans DIR              Directory containing plan files
  --files FILE...          Specific plan files to parse
  --config, -c FILE        JSON configuration file

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

Behavior Options:
  --dry-run                Parse and plan but don't execute
  --no-commit              Don't auto-commit changes
  --no-state               Don't persist state
  --yes, -y                Auto-confirm prompts
```

### Examples

```bash
# Quick task with prompt
ralph run -p "Add user authentication with JWT"

# PRD implementation with 30 max iterations
ralph run --prd ./docs/user-auth-prd.md -m 30

# Phased development with verbose output
ralph run --plans ./.ide/tasks/plans/ --verbose

# Dry run to preview tasks
ralph run --plans ./phases/ --dry-run

# Resume after interruption
ralph resume

# Check detailed progress
ralph status --detailed

# View iteration history
ralph history -n 20

# List pending tasks only
ralph tasks --status pending
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                       RALPH EXECUTION LOOP                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│   │  Parse   │────▶│  Select  │────▶│ Execute  │                │
│   │  Input   │     │   Task   │     │  Claude  │                │
│   └──────────┘     └──────────┘     └──────────┘                │
│        │                                   │                     │
│        │           ┌──────────┐           │                     │
│        │           │  Parse   │◀──────────┘                     │
│        │           │  Output  │                                  │
│        │           └──────────┘                                  │
│        │                │                                        │
│        ▼                ▼                                        │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│   │  State   │◀───▶│  Update  │────▶│  Next    │                │
│   │  Store   │     │  Status  │     │ Iteration│                │
│   └──────────┘     └──────────┘     └──────────┘                │
│                                           │                      │
│                          ┌────────────────┘                      │
│                          ▼                                       │
│                    ✓ PROJECT_COMPLETE                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Plan File Format

Ralph parses markdown files with this structure:

```markdown
# Project: My Feature

## Phase 1: Setup
Status: IN_PROGRESS

- [x] US-001: Initialize project structure
  - Priority: 1
  - Description: Set up Next.js with TypeScript

- [ ] US-002: Configure database
  - Priority: 1
  - Dependencies: US-001

## Phase 2: Implementation

- [ ] US-003: Create user model
  - Priority: 2
  - Dependencies: US-002
```

## PRD Format Support

```markdown
# Product Requirements Document: User Authentication

## Overview
Implement secure user authentication.

## User Stories

### US-001: As a user, I want to sign up
**Priority:** High
**Status:** Pending

#### Acceptance Criteria
- [ ] User can enter email and password
- [ ] Validation for email format
- [ ] Password strength requirements
```

## Configuration

### Project Config (`ralph.json`)

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

## State Management

Ralph persists state in `.ralph/state.json`:

```json
{
  "version": "1.0",
  "name": "my-project",
  "status": "in_progress",
  "phases": [...],
  "iterations": [...],
  "total_tasks": 25,
  "completed_tasks": 12
}
```

## Architecture

```
ralph/
├── cli.py           # CLI commands (run, status, resume, etc.)
├── input/           # Input handlers (prompt, prd, plans, config)
├── parser/          # Markdown & checkbox parsing
├── state/           # State management (models, store, tracker)
├── executor/        # Claude execution (prompt, output, retry)
└── utils/           # File and git utilities
```

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

## Requirements

- Python 3.9+
- Claude CLI installed and authenticated
- macOS or Linux (uses pexpect)

## License

MIT License - see [LICENSE](LICENSE) for details.
