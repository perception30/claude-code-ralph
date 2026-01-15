"""Ralph CLI - Autonomous Claude Code Agent Runner."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import RalphConfig, get_project_config_path
from .executor.retry import RetryConfig
from .executor.runner import RalphExecutor
from .input.base import InputSource
from .input.config import ConfigInput
from .input.plans import PlansInput
from .input.prd import PRDInput
from .input.prompt import PromptInput
from .parser.markdown import MarkdownParser
from .state.models import TaskStatus
from .state.store import StateStore
from .state.tracker import ProgressTracker
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
    # Input sources (mutually exclusive)
    prompt: Optional[str] = typer.Option(
        None, "--prompt", "-p",
        help="Direct prompt to execute",
    ),
    prd: Optional[str] = typer.Option(
        None, "--prd",
        help="PRD markdown file to parse",
    ),
    plans: Optional[str] = typer.Option(
        None, "--plans",
        help="Directory containing plan files",
    ),
    files: Optional[list[str]] = typer.Option(
        None, "--files", "-f",
        help="Specific plan files to parse",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c",
        help="JSON configuration file",
    ),

    # Execution settings
    max_iterations: int = typer.Option(
        50, "--max", "-m",
        help="Maximum number of iterations",
    ),
    idle_timeout: int = typer.Option(
        60, "--timeout", "-t",
        help="Seconds to wait for Claude response",
    ),
    sleep_between: int = typer.Option(
        2, "--sleep", "-s",
        help="Seconds between iterations",
    ),
    retry: int = typer.Option(
        3, "--retry",
        help="Max retries on failure",
    ),

    # Claude settings
    model: Optional[str] = typer.Option(
        None, "--model",
        help="Claude model to use",
    ),
    no_skip_permissions: bool = typer.Option(
        False, "--no-skip-permissions",
        help="Don't use --dangerously-skip-permissions",
    ),

    # Output settings
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Minimal output",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Verbose output",
    ),
    log_file: Optional[str] = typer.Option(
        None, "--log-file",
        help="Write logs to file",
    ),

    # Behavior settings
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Parse and plan but don't execute",
    ),
    no_commit: bool = typer.Option(
        False, "--no-commit",
        help="Don't auto-commit changes",
    ),
    no_state: bool = typer.Option(
        False, "--no-state",
        help="Don't persist state",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Auto-confirm prompts",
    ),

    # Working directory
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),

    version: bool = typer.Option(
        False, "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """
    Run Ralph autonomous agent.

    Ralph reads plan files, implements tasks iteratively, runs quality checks,
    and commits changes automatically.

    Examples:
        ralph run --prompt "Add dark mode to the app"
        ralph run --prd ./docs/PRD.md
        ralph run --plans ./phases/
        ralph run --config ./ralph.json
    """
    working_dir = os.path.abspath(working_dir)

    # Print banner
    if not quiet:
        ui.print_banner()

    # Determine input source and parse
    project = None
    source_files = []

    input_source: InputSource
    if prompt:
        # Direct prompt
        input_source = PromptInput(prompt=prompt)
        result = input_source.parse()
        if result.is_valid:
            project = result.project
            source_files = result.source_files
        else:
            for err in result.errors:
                ui.print_error(err)
            raise typer.Exit(1)

    elif prd:
        # PRD file
        input_source = PRDInput(prd_file=prd)
        errors = input_source.validate()
        if errors:
            for err in errors:
                ui.print_error(err)
            raise typer.Exit(1)

        result = input_source.parse()
        if result.is_valid:
            project = result.project
            source_files = result.source_files
        else:
            for err in result.errors:
                ui.print_error(err)
            raise typer.Exit(1)

    elif plans:
        # Plans directory
        input_source = PlansInput(plans_dir=plans)
        errors = input_source.validate()
        if errors:
            for err in errors:
                ui.print_error(err)
            raise typer.Exit(1)

        result = input_source.parse()
        if result.is_valid:
            project = result.project
            source_files = result.source_files
        else:
            for err in result.errors:
                ui.print_error(err)
            raise typer.Exit(1)

    elif config:
        # Config file
        config_input = ConfigInput(config_file=config)
        input_source = config_input
        errors = input_source.validate()
        if errors:
            for err in errors:
                ui.print_error(err)
            raise typer.Exit(1)

        result = input_source.parse()
        if result.is_valid:
            project = result.project
            source_files = result.source_files
            # Override settings from config
            if config_input.config:
                cfg = config_input.config
                max_iterations = cfg.max_iterations
                idle_timeout = cfg.idle_timeout
                sleep_between = cfg.sleep_between
                retry = cfg.retry_attempts
                model = cfg.model or model
        else:
            for err in result.errors:
                ui.print_error(err)
            raise typer.Exit(1)

    else:
        # Default: look for plans directory
        default_plans = Path(working_dir) / ".ide" / "tasks" / "plans"
        if default_plans.exists():
            input_source = PlansInput(plans_dir=str(default_plans))
            result = input_source.parse()
            if result.is_valid:
                project = result.project
                source_files = result.source_files
            else:
                ui.print_error("No input source specified and no default plans found")
                ui.console.print("\nUsage:")
                ui.console.print("  ralph run --prompt 'Your task'")
                ui.console.print("  ralph run --prd ./PRD.md")
                ui.console.print("  ralph run --plans ./plans/")
                raise typer.Exit(1)
        else:
            ui.print_error("No input source specified")
            ui.console.print("\nUsage:")
            ui.console.print("  ralph run --prompt 'Your task'")
            ui.console.print("  ralph run --prd ./PRD.md")
            ui.console.print("  ralph run --plans ./plans/")
            ui.console.print("  ralph run --config ./ralph.json")
            raise typer.Exit(1)

    # Display configuration
    if not quiet:
        ui.print_config(
            max_iterations=max_iterations,
            idle_timeout=idle_timeout,
            plans_dir=str(source_files[0]) if source_files else "N/A",
        )

        # Show project summary
        if project:
            ui.console.print(f"\n[bold]Project:[/bold] {project.name}")
            total = project.total_tasks
            completed = project.completed_tasks
            ui.console.print(f"[bold]Tasks:[/bold] {total} total, {completed} completed")
            ui.console.print(f"[bold]Phases:[/bold] {len(project.phases)}")

    # Dry run - just show what would be done
    if dry_run:
        ui.console.print("\n[yellow]Dry run mode - not executing[/yellow]")
        _show_task_list(project)
        raise typer.Exit(0)

    # Confirm execution
    if not yes and not quiet:
        if not typer.confirm("\nStart execution?", default=True):
            raise typer.Exit(0)

    # Create executor
    retry_config = RetryConfig(max_attempts=retry)

    # Project must be set at this point (all code paths either set it or exit)
    assert project is not None, "No project available for execution"

    executor = RalphExecutor(
        project=project,
        working_dir=working_dir,
        max_iterations=max_iterations,
        idle_timeout=idle_timeout,
        sleep_between=sleep_between,
        model=model,
        skip_permissions=not no_skip_permissions,
        commit_prefix="feat:" if not no_commit else "",
        update_source=not no_state,
        on_output=lambda line: ui.print_claude_line(line) if not quiet else None,
        retry_config=retry_config,
    )

    # Run execution
    try:
        ui.start_session(max_iterations)
        success = executor.run()

        if success:
            tracker_project = executor.tracker.project
            ui.print_all_complete(
                tracker_project.current_iteration if tracker_project else 0,
                executor.start_time
            )
        else:
            ui.print_max_iterations_reached(max_iterations, executor.start_time)

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
    Initialize Ralph in the current project.

    Creates configuration and plans directory structure.
    """
    working_dir = os.path.abspath(working_dir)
    config_path = get_project_config_path(working_dir)
    plans_dir = Path(working_dir) / ".ide" / "tasks" / "plans"
    state_dir = Path(working_dir) / ".ralph"

    # Create directories
    if not plans_dir.exists():
        plans_dir.mkdir(parents=True)
        ui.print_status(f"Created plans directory: {plans_dir}")

        # Create example plan
        example = plans_dir / "00-overview.md"
        example.write_text("""# Project Overview

## Phase 1: Initial Setup
- [ ] Task 1.1: Set up project structure
- [ ] Task 1.2: Configure dependencies

## Phase 2: Core Implementation
- [ ] Task 2.1: Implement main feature
- [ ] Task 2.2: Add tests

## Phase 3: Polish
- [ ] Task 3.1: Code review and cleanup
- [ ] Task 3.2: Documentation
""")
        ui.print_status("Created example plan file")

    if not state_dir.exists():
        state_dir.mkdir(parents=True)
        ui.print_status(f"Created state directory: {state_dir}")

    if not config_path.exists():
        config = RalphConfig()
        config.save(config_path)
        ui.print_status(f"Created config: {config_path}")

    ui.console.print("\n[green]Ralph initialized![/green]")
    ui.console.print("\nNext steps:")
    ui.console.print("  1. Edit plans in .ide/tasks/plans/")
    ui.console.print("  2. Run [cyan]ralph run[/cyan]")


@app.command()
def status(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),
    json_output: bool = typer.Option(
        False, "--json",
        help="Output as JSON",
    ),
    detailed: bool = typer.Option(
        False, "--detailed",
        help="Show all tasks",
    ),
) -> None:
    """Show Ralph status and progress."""
    working_dir = os.path.abspath(working_dir)
    store = StateStore(working_dir)

    if not store.exists():
        ui.console.print("[yellow]No Ralph state found[/yellow]")
        ui.console.print("Run [cyan]ralph run[/cyan] to start")
        raise typer.Exit(0)

    project = store.load()
    if not project:
        ui.console.print("[red]Failed to load state[/red]")
        raise typer.Exit(1)

    tracker = ProgressTracker(store)

    if json_output:
        import json
        ui.console.print(json.dumps(tracker.get_progress(), indent=2))
        return

    # Print status panel
    ui.print_banner()

    progress = tracker.get_progress()

    # Status panel
    status_table = Table(show_header=False, box=None, padding=(0, 2))
    status_table.add_column("Key", style="cyan")
    status_table.add_column("Value")

    status_table.add_row("Project", project.name)
    status_table.add_row("Status", progress["status"].upper())
    completed = progress['completed_tasks']
    total = progress['total_tasks']
    pct = progress['progress_percent']
    status_table.add_row("Progress", f"{completed}/{total} tasks ({pct}%)")
    status_table.add_row("Iterations", str(progress["current_iteration"]))

    ui.console.print(Panel(status_table, title="[bold]Ralph Status[/bold]"))

    # Phase summary
    ui.console.print("\n[bold]Phases:[/bold]")
    for phase in tracker.get_phases_summary():
        status = phase["status"]
        if status == "completed":
            icon = "✓"
        elif status == "in_progress":
            icon = "→"
        else:
            icon = "○"
        done = phase['tasks_completed']
        total_tasks = phase['tasks_total']
        ui.console.print(f"  {icon} {phase['name']}: {done}/{total_tasks}")

    if detailed:
        _show_task_list(project)


@app.command()
def resume(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),
    max_iterations: int = typer.Option(
        50, "--max", "-m",
        help="Maximum additional iterations",
    ),
) -> None:
    """Resume interrupted Ralph session."""
    working_dir = os.path.abspath(working_dir)
    store = StateStore(working_dir)

    if not store.exists():
        ui.console.print("[red]No state to resume[/red]")
        ui.console.print("Run [cyan]ralph run[/cyan] to start")
        raise typer.Exit(1)

    project = store.load()
    if not project:
        ui.console.print("[red]Failed to load state[/red]")
        raise typer.Exit(1)

    if project.is_complete:
        ui.console.print("[green]Project already complete![/green]")
        raise typer.Exit(0)

    ui.print_banner()
    ui.console.print(f"[bold]Resuming:[/bold] {project.name}")
    done = project.completed_tasks
    total = project.total_tasks
    ui.console.print(f"[bold]Progress:[/bold] {done}/{total} tasks")

    # Run executor
    executor = RalphExecutor(
        project=project,
        working_dir=working_dir,
        max_iterations=max_iterations,
        on_output=lambda line: ui.print_claude_line(line),
    )

    try:
        ui.start_session(max_iterations)
        success = executor.run()
        raise typer.Exit(0 if success else 1)
    except KeyboardInterrupt:
        ui.print_interrupted()
        raise typer.Exit(130)


@app.command()
def history(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),
    limit: int = typer.Option(
        10, "--limit", "-n",
        help="Number of iterations to show",
    ),
) -> None:
    """Show iteration history."""
    working_dir = os.path.abspath(working_dir)
    store = StateStore(working_dir)

    if not store.exists():
        ui.console.print("[yellow]No history found[/yellow]")
        raise typer.Exit(0)

    project = store.load()
    if not project:
        ui.console.print("[yellow]Could not load project history[/yellow]")
        raise typer.Exit(0)

    tracker = ProgressTracker(store)

    ui.console.print(f"\n[bold]Iteration History[/bold] ({len(project.iterations)} total)\n")

    table = Table()
    table.add_column("#", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Tasks Completed")

    for it in tracker.get_iteration_history(limit):
        it_status = it["status"]
        if it_status == "success":
            status_style = "green"
        elif it_status == "failed":
            status_style = "red"
        else:
            status_style = "yellow"
        duration = f"{it['duration_seconds']:.1f}s" if it["duration_seconds"] else "-"
        table.add_row(
            str(it["number"]),
            f"[{status_style}]{it['status']}[/{status_style}]",
            duration,
            ", ".join(it["tasks_completed"]) or "-"
        )

    ui.console.print(table)


@app.command()
def tasks(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),
    status_filter: Optional[str] = typer.Option(
        None, "--status",
        help="Filter by status (pending, completed, failed, blocked)",
    ),
) -> None:
    """List all tasks with status."""
    working_dir = os.path.abspath(working_dir)
    store = StateStore(working_dir)

    if not store.exists():
        ui.console.print("[yellow]No tasks found[/yellow]")
        raise typer.Exit(0)

    project = store.load()

    # Parse filter
    filter_status = None
    if status_filter:
        try:
            filter_status = TaskStatus(status_filter.lower())
        except ValueError:
            ui.console.print(f"[red]Invalid status: {status_filter}[/red]")
            raise typer.Exit(1)

    _show_task_list(project, filter_status)


@app.command()
def validate(
    file_path: str = typer.Argument(
        ...,
        help="Plan or PRD file to validate",
    ),
) -> None:
    """Validate a plan or PRD file."""
    path = Path(file_path)

    if not path.exists():
        ui.console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    try:
        parser = MarkdownParser()
        project = parser.parse_file(file_path)

        ui.console.print(f"\n[green]Valid![/green] {file_path}")
        ui.console.print(f"\nProject: {project.name}")
        ui.console.print(f"Phases: {len(project.phases)}")
        ui.console.print(f"Tasks: {project.total_tasks}")

        for phase in project.phases:
            ui.console.print(f"\n  [bold]{phase.name}[/bold] ({len(phase.tasks)} tasks)")
            for task in phase.tasks[:5]:
                icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
                ui.console.print(f"    {icon} {task.id}: {task.name}")
            if len(phase.tasks) > 5:
                ui.console.print(f"    ... and {len(phase.tasks) - 5} more")

    except Exception as e:
        ui.console.print(f"[red]Invalid: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reset(
    working_dir: str = typer.Option(
        ".", "--dir", "-d",
        help="Working directory",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation",
    ),
) -> None:
    """Reset Ralph state (start fresh)."""
    working_dir = os.path.abspath(working_dir)
    store = StateStore(working_dir)

    if not store.exists():
        ui.console.print("[yellow]No state to reset[/yellow]")
        raise typer.Exit(0)

    if not yes:
        if not typer.confirm("Reset all progress?", default=False):
            raise typer.Exit(0)

    # Backup before reset
    try:
        backup = store.backup(suffix="_pre_reset")
        ui.console.print(f"[dim]Backup saved: {backup}[/dim]")
    except Exception:
        pass

    store.reset()
    ui.console.print("[green]State reset![/green]")


def _show_task_list(project, status_filter: Optional[TaskStatus] = None) -> None:
    """Display task list in table format."""
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Phase")
    table.add_column("Status")
    table.add_column("Iteration")

    for phase in project.phases:
        for task in phase.tasks:
            if status_filter and task.status != status_filter:
                continue

            status_style = {
                TaskStatus.PENDING: "dim",
                TaskStatus.IN_PROGRESS: "yellow",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.BLOCKED: "magenta",
            }.get(task.status, "")

            table.add_row(
                task.id,
                task.name[:40] + "..." if len(task.name) > 40 else task.name,
                phase.name[:20],
                f"[{status_style}]{task.status.value}[/{status_style}]",
                str(task.iteration) if task.iteration else "-"
            )

    ui.console.print(table)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
