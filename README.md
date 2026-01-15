# Ralph

**Autonomous Claude Code Agent Runner** - A production-ready Python CLI for running Claude as an autonomous software engineering agent.

[![PyPI version](https://badge.fury.io/py/ralph-agent.svg)](https://badge.fury.io/py/ralph-agent)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🎨 **Rich Terminal UI** - Beautiful colored output, progress indicators, and status displays
- 📺 **Streaming Output** - See Claude's responses in real-time as they're generated
- 🔄 **Auto Exit Detection** - Detects when Claude finishes and automatically proceeds
- 🔁 **Iteration Management** - Run multiple iterations with configurable limits
- ✅ **Completion Detection** - Automatically detects when all phases are complete
- 📝 **Session Logging** - Saves each iteration's output to log files
- 🛑 **Graceful Shutdown** - Ctrl+C handling with proper cleanup
- ⚙️ **Configurable** - Customize timeouts, paths, and behavior via CLI options

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

```bash
# Run with defaults (10 iterations, 30s timeout)
ralph

# Run with custom settings
ralph -m 20 -t 60

# Initialize a new project
ralph init

# Check status
ralph status
```

## Usage

```
Usage: ralph [OPTIONS] COMMAND [ARGS]...

Commands:
  run      Run Ralph autonomous agent (default)
  init     Initialize Ralph in a project
  status   Show session status and progress

Options:
  -m, --max INTEGER      Maximum iterations [default: 10]
  -t, --timeout INTEGER  Idle timeout in seconds [default: 30]
  -s, --sleep INTEGER    Sleep between iterations [default: 2]
  -p, --plans TEXT       Plans directory [default: .ide/tasks/plans]
  -d, --dir TEXT         Working directory [default: .]
  --model TEXT           Claude model (e.g., 'sonnet', 'opus')
  --no-skip-permissions  Don't bypass permission checks
  -q, --quiet            Minimal output
  -v, --version          Show version
  --help                 Show help
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        RALPH LOOP                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. Read Plans  ──►  2. Pick Phase  ──►  3. Implement     │
│         ▲                                       │           │
│         │                                       ▼           │
│   6. Repeat     ◄──  5. Commit      ◄──  4. Quality Check  │
│         │                                                   │
│         ▼                                                   │
│   ✓ All Done (creates completion flag)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Building & Distribution

### Development Setup

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Lint & format
make lint
make format
```

### Build Package

```bash
# Build wheel and sdist
make build
# Output: dist/ralph_agent-1.0.0-py3-none-any.whl
#         dist/ralph_agent-1.0.0.tar.gz
```

### Publish to PyPI

```bash
# Test on TestPyPI first
make publish-test

# Publish to PyPI
make publish
```

### Build Standalone Executable

```bash
# Single binary with PyInstaller
make standalone
# Output: dist/ralph

# Python zipapp with shiv
make zipapp
# Output: ralph.pyz
```

## Configuration

Create `.ide/ralph.json` for project-specific settings:

```json
{
  "max_iterations": 20,
  "idle_timeout": 60,
  "sleep_between": 5,
  "plans_dir": ".ide/tasks/plans",
  "completion_flag": "/tmp/ralph_complete.flag"
}
```

## Requirements

- Python 3.9+
- Claude CLI installed and authenticated
- macOS or Linux (uses pexpect)

## License

MIT License - see [LICENSE](LICENSE) for details.
