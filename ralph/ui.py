"""Rich terminal UI components for Ralph CLI."""

from datetime import datetime, timedelta
from typing import Optional

from rich.box import DOUBLE, HEAVY, ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

console = Console()


class RalphUI:
    """Rich UI manager for Ralph CLI."""

    def __init__(self):
        self.console = console
        self.start_time: Optional[datetime] = None
        self.current_iteration = 0
        self.max_iterations = 0
        self.status = "initializing"

    def print_banner(self) -> None:
        """Print the Ralph banner."""
        banner = """
    ╦═╗╔═╗╦  ╔═╗╦ ╦
    ╠╦╝╠═╣║  ╠═╝╠═╣
    ╩╚═╩ ╩╩═╝╩  ╩ ╩
    Autonomous Agent Runner
        """
        self.console.print(Panel(
            Text(banner, style="bold cyan", justify="center"),
            box=DOUBLE,
            border_style="cyan",
            padding=(0, 2)
        ))
        self.console.print()

    def print_config(self, max_iterations: int, idle_timeout: int, plans_dir: str) -> None:
        """Print configuration summary."""
        table = Table(box=ROUNDED, border_style="dim")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Max Iterations", str(max_iterations))
        table.add_row("Idle Timeout", f"{idle_timeout}s")
        table.add_row("Plans Directory", plans_dir)

        self.console.print(Panel(table, title="[bold]Configuration[/bold]", border_style="blue"))
        self.console.print()

    def start_session(self, max_iterations: int) -> None:
        """Mark the start of a Ralph session."""
        self.start_time = datetime.now()
        self.max_iterations = max_iterations
        self.current_iteration = 0

    def print_iteration_start(self, iteration: int) -> None:
        """Print iteration start header."""
        self.current_iteration = iteration
        elapsed = ""
        if self.start_time:
            delta = datetime.now() - self.start_time
            elapsed = f" │ Elapsed: {self._format_duration(delta)}"

        header = f"  Iteration {iteration} of {self.max_iterations}{elapsed}  "
        self.console.print()
        self.console.rule(f"[bold cyan]{header}[/bold cyan]", style="cyan")
        self.console.print()

    def print_iteration_complete(self, iteration: int, duration: timedelta) -> None:
        """Print iteration completion message."""
        self.console.print()
        duration_str = self._format_duration(duration)
        msg = f"  [green]✓[/green] Iteration {iteration} completed in {duration_str}"
        self.console.print(msg, style="dim")

    def print_waiting(self) -> None:
        """Print waiting message."""
        self.console.print("\n  [dim]Waiting for Claude to finish...[/dim]")

    def print_sending_exit(self) -> None:
        """Print exit signal message."""
        self.console.print("  [yellow]→[/yellow] Sending exit signal...", style="dim")

    def print_claude_output_start(self) -> None:
        """Print Claude output section header."""
        self.console.print("  [bold blue]Claude:[/bold blue]")
        self.console.print("  " + "─" * 60, style="dim")

    def print_claude_line(self, line: str) -> None:
        """Print a line of Claude's output."""
        # Clean up the line and add indentation
        cleaned = line.rstrip()
        if cleaned:
            self.console.print(f"  {cleaned}")

    def print_all_complete(self, iterations: int, start_time) -> None:
        """Print all tasks complete message."""
        self.console.print()

        # Handle both datetime and timedelta
        if isinstance(start_time, datetime):
            total_duration = datetime.now() - start_time
        else:
            total_duration = start_time

        panel = Panel(
            Text.assemble(
                ("All phases completed!\n\n", "bold green"),
                ("Iterations: ", "dim"),
                (str(iterations), "cyan"),
                ("\nTotal time: ", "dim"),
                (self._format_duration(total_duration), "cyan"),
            ),
            title="[bold green]✓ Success[/bold green]",
            border_style="green",
            box=HEAVY,
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_max_iterations_reached(self, max_iterations: int, start_time) -> None:
        """Print max iterations reached message."""
        self.console.print()

        # Handle both datetime and timedelta
        if isinstance(start_time, datetime):
            total_duration = datetime.now() - start_time
        else:
            total_duration = start_time

        panel = Panel(
            Text.assemble(
                (f"Reached maximum iterations ({max_iterations})\n\n", "yellow"),
                ("Total time: ", "dim"),
                (self._format_duration(total_duration), "cyan"),
                ("\n\nRun [cyan]ralph resume[/cyan] to continue.", "dim"),
            ),
            title="[bold yellow]⚠ Iteration Limit[/bold yellow]",
            border_style="yellow",
            box=HEAVY,
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Print error message."""
        self.console.print()
        error_text = Text()
        error_text.append(f"{message}\n", style="bold red")
        if exception:
            error_text.append(f"\n{type(exception).__name__}: {exception}", style="dim red")

        panel = Panel(
            error_text,
            title="[bold red]✗ Error[/bold red]",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_interrupted(self) -> None:
        """Print interrupted message."""
        self.console.print()
        self.console.print(
            Panel(
                "[yellow]Session interrupted by user[/yellow]",
                border_style="yellow",
                padding=(0, 2)
            )
        )

    def print_status(self, status: str) -> None:
        """Print a status update."""
        self.console.print(f"  [dim]→ {status}[/dim]")

    def create_spinner(self, message: str) -> Progress:
        """Create a spinner progress indicator."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )

    def _format_duration(self, delta: timedelta) -> str:
        """Format a timedelta as a human-readable string."""
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


# Global UI instance
ui = RalphUI()
