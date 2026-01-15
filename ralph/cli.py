"""Ralph CLI - Autonomous Claude Code Agent Runner."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .config import RalphConfig, get_project_config_path
from .runner import RalphSession
from .ui import ui

app = typer.Typer(
    name="ralph",
    help="Ralph - Autonomous Claude Code Agent Runner",
    add_completion=False,
    no_args_is_help=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        ui.console.print(f"Ralph v{__version__}")
        raise typer.Exit()


@app.command()
def run(
    # Iteration settings
    max_iterations: int = typer.Option(
        10, "--max", "-m",
        help="Maximum number of iterations to run",
    ),
    idle_timeout: int = typer.Option(
        30, "--timeout", "-t",
        help="Seconds to wait for Claude response before considering it complete",
    ),
    sleep_between: int = typer.Option(
        2, "--sleep", "-s",
        help="Seconds to sleep between iterations",
    ),

    # Path settings
    plans_dir: str = typer.Option(
        ".ide/tasks/plans", "--plans", "-p",
        help="Directory containing phase plan files",
    ),
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory for Claude",
    ),

    # Claude settings
    model: Optional[str] = typer.Option(
        None, "--model",
        help="Claude model to use (e.g., 'sonnet', 'opus')",
    ),
    no_skip_permissions: bool = typer.Option(
        False, "--no-skip-permissions",
        help="Don't use --dangerously-skip-permissions flag",
    ),

    # Misc
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Minimal output mode",
    ),
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """
    Run Ralph autonomous agent to implement phased plans.

    Ralph will read your plan files, implement phases one at a time,
    run quality checks, and commit changes automatically.

    Examples:

        ralph              # Run with defaults (10 iterations, 30s timeout)

        ralph -m 20        # Run up to 20 iterations

        ralph -t 60        # Use 60 second idle timeout

        ralph -p ./plans   # Use custom plans directory
    """
    # Resolve working directory
    working_dir = os.path.abspath(working_dir)

    # Load or create config
    config = RalphConfig(
        max_iterations=max_iterations,
        idle_timeout=idle_timeout,
        sleep_between=sleep_between,
        plans_dir=plans_dir,
        skip_permissions=not no_skip_permissions,
        model=model,
    )

    # Print banner (unless quiet)
    if not quiet:
        ui.print_banner()
        ui.print_config(
            max_iterations=config.max_iterations,
            idle_timeout=config.idle_timeout,
            plans_dir=str(Path(working_dir) / config.plans_dir),
        )

    # Verify plans directory exists
    plans_path = Path(working_dir) / config.plans_dir
    if not plans_path.exists():
        ui.print_error(
            f"Plans directory not found: {plans_path}",
        )
        raise typer.Exit(1)

    # Check for plan files
    plan_files = list(plans_path.glob("*.md"))
    if not plan_files:
        ui.print_error(
            f"No plan files (*.md) found in: {plans_path}",
        )
        raise typer.Exit(1)

    if not quiet:
        ui.print_status(f"Found {len(plan_files)} plan file(s)")

    # Run the session
    session = RalphSession(config=config, working_dir=working_dir)

    try:
        success = session.run()
        raise typer.Exit(0 if success else 1)
    except KeyboardInterrupt:
        ui.print_interrupted()
        raise typer.Exit(130)


@app.command()
def init(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory to initialize",
    ),
) -> None:
    """
    Initialize Ralph configuration in the current project.

    Creates a default configuration file and plans directory structure.
    """
    working_dir = os.path.abspath(working_dir)
    config_path = get_project_config_path(working_dir)
    plans_dir = Path(working_dir) / ".ide" / "tasks" / "plans"

    # Create plans directory
    if not plans_dir.exists():
        plans_dir.mkdir(parents=True)
        ui.print_status(f"Created plans directory: {plans_dir}")

        # Create example plan file
        example_plan = plans_dir / "00-overview.md"
        example_plan.write_text("""# Project Overview

## Phase 1: Initial Setup
- [ ] Task 1.1: Description
- [ ] Task 1.2: Description

## Phase 2: Core Implementation
- [ ] Task 2.1: Description
- [ ] Task 2.2: Description

## Phase 3: Testing & Polish
- [ ] Task 3.1: Description
- [ ] Task 3.2: Description
""")
        ui.print_status("Created example plan file")

    # Create config file
    if not config_path.exists():
        config = RalphConfig()
        config.save(config_path)
        ui.print_status(f"Created config file: {config_path}")

    ui.console.print("\n[green]✓ Ralph initialized successfully![/green]")
    ui.console.print("\nNext steps:")
    ui.console.print("  1. Edit your plan files in .ide/tasks/plans/")
    ui.console.print("  2. Run [cyan]ralph[/cyan] to start the autonomous agent")


@app.command()
def status(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory to check",
    ),
) -> None:
    """
    Show Ralph session status and progress.
    """
    working_dir = os.path.abspath(working_dir)
    config = RalphConfig()

    ui.print_banner()

    # Check plans directory
    plans_path = Path(working_dir) / config.plans_dir
    if not plans_path.exists():
        ui.console.print("[yellow]⚠ Plans directory not found[/yellow]")
        ui.console.print(f"  Expected: {plans_path}")
        ui.console.print("\n  Run [cyan]ralph init[/cyan] to set up the project")
        raise typer.Exit(1)

    # List plan files
    plan_files = sorted(plans_path.glob("*.md"))
    ui.console.print(f"\n[bold]Plan Files[/bold] ({len(plan_files)} found):")
    for pf in plan_files:
        ui.console.print(f"  • {pf.name}")

    # Check completion flag
    flag_path = Path(config.completion_flag)
    if flag_path.exists():
        ui.console.print("\n[green]✓ Completion flag found - all phases complete![/green]")
    else:
        ui.console.print("\n[dim]○ Completion flag not found - work in progress[/dim]")

    # Check logs
    log_dir = Path(working_dir) / config.log_dir
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"), reverse=True)
        if log_files:
            ui.console.print(f"\n[bold]Recent Logs[/bold] ({len(log_files)} total):")
            for lf in log_files[:5]:
                ui.console.print(f"  • {lf.name}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
