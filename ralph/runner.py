"""Core Claude runner using pexpect for terminal interaction."""

import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pexpect  # type: ignore[import-untyped]

from .config import RalphConfig
from .ui import ui


class ClaudeRunner:
    """Runs Claude CLI with streaming output and automatic exit."""

    def __init__(
        self,
        config: RalphConfig,
        working_dir: str = ".",
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.working_dir = working_dir
        self.on_output = on_output or self._default_output_handler
        self.process: Optional[pexpect.spawn] = None
        self._interrupted = False

    def _default_output_handler(self, line: str) -> None:
        """Default output handler - prints to console."""
        ui.print_claude_line(line)

    def run(self, prompt: str) -> tuple[bool, str]:
        """
        Run Claude with the given prompt.

        Returns:
            Tuple of (success, output)
        """
        self._interrupted = False
        output_lines = []

        # Build command
        cmd = "claude"
        args = []

        if self.config.skip_permissions:
            args.append("--dangerously-skip-permissions")

        if self.config.model:
            args.extend(["--model", self.config.model])

        # Add prompt as positional argument
        args.append(prompt)

        try:
            ui.print_claude_output_start()

            # Spawn Claude process
            self.process = pexpect.spawn(
                cmd,
                args,
                cwd=self.working_dir,
                encoding='utf-8',
                timeout=self.config.idle_timeout,
                dimensions=(50, 200),  # rows, cols
            )

            # Set up environment
            self.process.env = os.environ.copy()

            # Read output until idle timeout
            while True:
                try:
                    # Read one line
                    line = self.process.readline()

                    if not line:
                        # Process might have exited
                        if not self.process.isalive():
                            break
                        continue

                    # Store and display the line
                    output_lines.append(line)
                    self.on_output(line)

                except pexpect.TIMEOUT:
                    # No output for idle_timeout seconds - Claude is done
                    ui.print_sending_exit()
                    self._send_exit()
                    break

                except pexpect.EOF:
                    # Process ended
                    break

                if self._interrupted:
                    break

            # Wait for process to fully terminate
            if self.process.isalive():
                self.process.wait()

            output = ''.join(output_lines)
            return (True, output)

        except Exception as e:
            ui.print_error("Failed to run Claude", e)
            return (False, str(e))

        finally:
            self._cleanup()

    def _send_exit(self) -> None:
        """Send /exit command to Claude."""
        if self.process and self.process.isalive():
            try:
                self.process.sendline("/exit")
                # Give it a moment to process
                self.process.expect(pexpect.EOF, timeout=5)
            except Exception:
                # Force kill if /exit doesn't work
                self.process.terminate(force=True)

    def _cleanup(self) -> None:
        """Clean up the process."""
        if self.process:
            try:
                if self.process.isalive():
                    self.process.terminate(force=True)
            except Exception:
                pass
            self.process = None

    def interrupt(self) -> None:
        """Interrupt the current run."""
        self._interrupted = True
        self._cleanup()


class RalphSession:
    """Manages a Ralph autonomous agent session."""

    def __init__(self, config: RalphConfig, working_dir: str = "."):
        self.config = config
        self.working_dir = os.path.abspath(working_dir)
        self.runner: Optional[ClaudeRunner] = None
        self._interrupted = False
        self.start_time: Optional[datetime] = None
        self.iteration_outputs: list[str] = []

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def handler(_signum, _frame):
            self._interrupted = True
            if self.runner:
                self.runner.interrupt()
            ui.print_interrupted()

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _clear_completion_flag(self) -> None:
        """Clear any existing completion flag."""
        flag_path = Path(self.config.completion_flag)
        if flag_path.exists():
            flag_path.unlink()

    def _check_completion(self) -> bool:
        """Check if all phases are complete."""
        return Path(self.config.completion_flag).exists()

    def _ensure_log_dir(self) -> Path:
        """Ensure log directory exists and return path."""
        log_dir = Path(self.working_dir) / self.config.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _save_iteration_log(self, iteration: int, output: str) -> None:
        """Save iteration output to log file."""
        log_dir = self._ensure_log_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"iteration_{iteration:03d}_{timestamp}.log"

        with open(log_file, 'w') as f:
            f.write(f"# Ralph Iteration {iteration}\n")
            f.write(f"# Timestamp: {timestamp}\n")
            f.write(f"# Working Directory: {self.working_dir}\n")
            f.write("#" + "=" * 60 + "\n\n")
            f.write(output)

    def run(self) -> bool:
        """
        Run the Ralph session.

        Returns:
            True if all phases completed, False otherwise.
        """
        self._setup_signal_handlers()
        self._clear_completion_flag()

        self.start_time = datetime.now()
        ui.start_session(self.config.max_iterations)

        prompt = self.config.get_prompt(self.working_dir)

        for iteration in range(1, self.config.max_iterations + 1):
            if self._interrupted:
                break

            ui.print_iteration_start(iteration)
            iteration_start = datetime.now()

            # Create runner for this iteration
            self.runner = ClaudeRunner(
                config=self.config,
                working_dir=self.working_dir,
            )

            # Run Claude
            success, output = self.runner.run(prompt)
            self.iteration_outputs.append(output)

            iteration_duration = datetime.now() - iteration_start
            ui.print_iteration_complete(iteration, iteration_duration)

            # Save log
            self._save_iteration_log(iteration, output)

            # Check for completion
            if self._check_completion():
                total_duration = datetime.now() - self.start_time
                ui.print_all_complete(iteration, total_duration)
                return True

            if self._interrupted:
                break

            # Sleep before next iteration
            if iteration < self.config.max_iterations:
                import time
                ui.print_status(f"Sleeping {self.config.sleep_between}s before next iteration...")
                time.sleep(self.config.sleep_between)

        if not self._interrupted:
            total_duration = datetime.now() - self.start_time
            ui.print_max_iterations_reached(self.config.max_iterations, total_duration)

        return False
