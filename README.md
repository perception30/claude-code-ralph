# Ralph

**Autonomous Claude Code Agent Runner** - A production-ready Python CLI for running Claude as an autonomous software engineering agent.

[![PyPI version](https://badge.fury.io/py/ralph-agent.svg)](https://badge.fury.io/py/ralph-agent)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Flexible Input** - Run from prompts, PRD files, plan directories, or JSON configs
- **PRD & Plans Generation** - Generate PRDs and phased plans from natural language prompts
- **Multi-Project Support** - Work on multiple projects simultaneously without interference
- **Persistent State** - Track progress across sessions with automatic resume
- **Smart Parsing** - Parse markdown plans and PRDs to extract phases and tasks
- **Globally Unique Task IDs** - Reliable task tracking across all phases and files
- **Completion Detection** - Structured output markers for reliable task tracking
- **Auto Checkboxes** - Automatically update `[ ]` to `[x]` in source files
- **Retry Logic** - Exponential backoff with configurable retry attempts
- **Rich Terminal UI** - Beautiful progress bars, status panels, and task tables
- **Resume Capability** - Continue interrupted sessions from exactly where you left off

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

If interrupted (Ctrl+C or timeout), simply re-run the same command:

```bash
# Original run
ralph run --plans ./my-feature/

# ... interrupted ...

# Resume - just run the same command again
ralph run --plans ./my-feature/
```

Ralph automatically:
1. Recognizes this is the same project (by input source)
2. Loads existing state from `.ralph/projects/<id>/`
3. Continues from the last incomplete task
4. Preserves iteration history

You can also use the legacy resume command:

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
| `ralph generate prd` | Generate a PRD from a natural language prompt |
| `ralph generate plans` | Generate phased implementation plans |
| `ralph init` | Initialize Ralph in a project |
| `ralph status` | Show current progress and phase status |
| `ralph projects` | List all projects and their progress |
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

# Resume after interruption (re-run same command)
ralph run --plans ./my-feature/

# List all projects
ralph projects

# Check detailed progress
ralph status --detailed

# View iteration history
ralph history -n 20

# List pending tasks only
ralph tasks --status pending
```

### `ralph generate` - Generate PRDs and Plans

Generate PRDs and phased implementation plans from natural language prompts. Claude runs interactively to create structured documents.

#### Generate PRD

```bash
ralph generate prd [OPTIONS]

Options:
  --prompt, -p TEXT      Prompt describing the feature/project
  --from-file, -f TEXT   Path to prompt file (.txt, .md)
  --output, -o TEXT      Output file path [default: ./PRD.md]
  --name, -n TEXT        Project name
  --model TEXT           Claude model to use
  --timeout, -t INT      Seconds to wait for Claude [default: 60]
  --dry-run              Show prompt without generating
  --dir, -d TEXT         Working directory [default: .]
```

#### Generate Plans

```bash
ralph generate plans [OPTIONS]

Options:
  --prompt, -p TEXT      Prompt describing the feature/project
  --from-file, -f TEXT   Path to prompt file (.txt, .md)
  --from-prd TEXT        Convert PRD file to plans
  --output, -o TEXT      Output directory path [default: ./plans]
  --name, -n TEXT        Project name
  --phases INT           Number of phases to generate (default: auto)
  --max-tasks INT        Maximum tasks per phase [default: 10]
  --model TEXT           Claude model to use
  --timeout, -t INT      Seconds to wait for Claude [default: 60]
  --dry-run              Show prompt without generating
  --dir, -d TEXT         Working directory [default: .]
```

#### Generation Examples

```bash
# Generate PRD from a prompt
ralph generate prd --prompt "User authentication system with OAuth support"

# Generate PRD from a requirements file
ralph generate prd --from-file ./requirements.txt --output ./docs/PRD.md

# Generate phased plans from a prompt
ralph generate plans --prompt "Refactor the authentication system"

# Convert existing PRD to phased plans
ralph generate plans --from-prd ./docs/PRD.md --output ./plans/

# Generate plans with specific number of phases
ralph generate plans --prompt "Build a REST API" --phases 4

# Preview the prompt without generating (dry run)
ralph generate prd --prompt "New feature" --dry-run
```

#### Typical Workflow

```bash
# Step 1: Generate PRD from your idea
ralph generate prd --prompt "Build a task management system with teams"

# Step 2: Review and edit PRD.md as needed

# Step 3: Generate phased plans from PRD
ralph generate plans --from-prd ./PRD.md --output ./.ide/tasks/plans/

# Step 4: Run Ralph to execute the plans
ralph run --plans ./.ide/tasks/plans/
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

- [x] TASK-101: Initialize project structure
  - Priority: High
  - Description: Set up Next.js with TypeScript

- [ ] TASK-102: Configure database
  - Priority: High
  - Dependencies: TASK-101

## Phase 2: Implementation

- [ ] TASK-201: Create user model
  - Priority: Medium
  - Dependencies: TASK-102
```

### Task ID Convention

**IMPORTANT:** Task IDs must be globally unique across all files:

- Phase 1: `TASK-101`, `TASK-102`, `TASK-103`, etc.
- Phase 2: `TASK-201`, `TASK-202`, `TASK-203`, etc.
- Phase 3: `TASK-301`, `TASK-302`, `TASK-303`, etc.

If task IDs are omitted, Ralph auto-generates unique IDs, but explicit IDs are recommended for clarity and reliable dependency tracking.

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

### Multi-Project Isolation

Ralph supports multiple concurrent projects without interference. Each input source gets its own isolated state directory:

```
.ralph/
└── projects/
    ├── a92f5b03.../       # Project from ./plans/feature-a/
    │   ├── state.json
    │   └── status.json
    ├── 7c8d9e01.../       # Project from ./plans/feature-b/
    │   ├── state.json
    │   └── status.json
    └── 37ae55ff.../       # Project from --prompt "Fix bug"
        ├── state.json
        └── status.json
```

### Project Identity

Projects are identified by their input source:

| Input Type | Identity Based On | Same Input = Same Project? |
|------------|-------------------|---------------------------|
| `--plans ./dir/` | Directory path | ✓ Yes |
| `--prd ./file.md` | File path | ✓ Yes |
| `--prompt "text"` | Prompt text hash | ✓ Yes |
| `--config ./file.json` | Config file path | ✓ Yes |

This means:
- Running `ralph run --plans ./my-feature/` twice **continues** from where you left off
- Running `ralph run --plans ./different-feature/` is a **separate project**
- Both can run without interfering with each other

### List All Projects

```bash
$ ralph projects

Ralph Projects (2 total)

ID         Name              Status       Progress    Source
a92f5b03   feature-a         in_progress  5/12        ...plans/feature-a
7c8d9e01   feature-b         pending      0/8         ...plans/feature-b
```

### State File Structure

Each project's `state.json`:

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
├── cli.py           # CLI commands (run, status, resume, projects, generate)
├── input/           # Input handlers (prompt, prd, plans, config)
├── parser/          # Markdown & checkbox parsing
├── state/           # State management
│   ├── models.py    # Data models (Project, Phase, Task)
│   ├── store.py     # Persistent storage with multi-project support
│   ├── tracker.py   # Progress tracking
│   └── identity.py  # Project identity generation
├── executor/        # Claude execution (prompt, output, retry)
├── generator/       # PRD & plans generation (prd, plans, templates)
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
