"""Simple Claude runner - spawn and let it run."""

import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import pexpect

from .prompt import PromptBuilder, ExecutionContext
from .output import OutputParser, ParsedOutput
from .retry import RetryStrategy, RetryConfig, RetryResult
from ..state.models import Project, TaskStatus
from ..state.store import StateStore
from ..state.tracker import ProgressTracker
from ..parser.checkbox import CheckboxUpdater


class ClaudeRunner:
    """Simple Claude runner - spawns claude and lets it output."""

    def __init__(
        self,
        working_dir: str = ".",
        idle_timeout: int = 60,
        model: Optional[str] = None,
        skip_permissions: bool = True,
    ):
        self.working_dir = os.path.abspath(working_dir)
        self.idle_timeout = idle_timeout
        self.model = model
        self.skip_permissions = skip_permissions
        self.process: Optional[pexpect.spawn] = None
        self._interrupted = False

    def run(self, prompt: str) -> tuple[bool, str, ParsedOutput]:
        """
        Run Claude with the given prompt.
        Simply spawns the process and lets it output to terminal.
        """
        self._interrupted = False

        # Build command args
        args = []
        if self.skip_permissions:
            args.append("--dangerously-skip-permissions")
        if self.model:
            args.extend(["--model", self.model])
        args.append(prompt)

        try:
            # Spawn claude - output goes directly to terminal
            self.process = pexpect.spawn(
                "claude",
                args,
                cwd=self.working_dir,
                timeout=self.idle_timeout,
            )

            # Let it output directly to stdout
            self.process.logfile_read = sys.stdout.buffer

            # Wait for completion markers, EOF, or timeout
            # Pattern 0: TASK_STATUS marker (task done)
            # Pattern 1: PROJECT_COMPLETE marker
            # Pattern 2: EOF (process ended)
            # Pattern 3: TIMEOUT (idle too long)
            patterns = [
                r'TASK_STATUS:\s*(COMPLETED|FAILED|BLOCKED)',
                r'PROJECT_COMPLETE',
                pexpect.EOF,
                pexpect.TIMEOUT,
            ]

            index = self.process.expect(patterns)

            # If we matched a completion pattern (not EOF), send /exit
            if index in (0, 1) and self.process.isalive():
                # Brief pause to let any final output flush
                import time
                time.sleep(0.5)
                self.process.sendline("/exit")
                try:
                    self.process.expect(pexpect.EOF, timeout=10)
                except:
                    self.process.terminate(force=True)
            elif index == 3 and self.process.isalive():
                # Timeout - send exit
                self.process.sendline("/exit")
                try:
                    self.process.expect(pexpect.EOF, timeout=5)
                except:
                    self.process.terminate(force=True)

            # Get output for parsing
            output = ""
            if self.process.before:
                output = self.process.before.decode('utf-8', errors='ignore') if isinstance(self.process.before, bytes) else self.process.before

            parsed = OutputParser.parse(output)
            return (True, output, parsed)

        except Exception as e:
            return (False, str(e), ParsedOutput(errors=[str(e)]))

        finally:
            if self.process:
                try:
                    if self.process.isalive():
                        self.process.terminate(force=True)
                except:
                    pass
                self.process = None

    def interrupt(self) -> None:
        """Interrupt the current run."""
        self._interrupted = True
        if self.process:
            try:
                self.process.terminate(force=True)
            except:
                pass


class RalphExecutor:
    """Orchestrates the Ralph execution loop."""

    def __init__(
        self,
        project: Project,
        working_dir: str = ".",
        max_iterations: int = 50,
        idle_timeout: int = 60,
        sleep_between: int = 2,
        model: Optional[str] = None,
        skip_permissions: bool = True,
        custom_instructions: str = "",
        commit_prefix: str = "feat:",
        update_source: bool = True,
        on_output: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.project = project
        self.working_dir = os.path.abspath(working_dir)
        self.max_iterations = max_iterations
        self.idle_timeout = idle_timeout
        self.sleep_between = sleep_between
        self.model = model
        self.skip_permissions = skip_permissions
        self.custom_instructions = custom_instructions
        self.commit_prefix = commit_prefix
        self.update_source = update_source
        self.on_output = on_output
        self.on_progress = on_progress
        self.retry_config = retry_config or RetryConfig()

        # State management
        self.store = StateStore(working_dir)
        self.tracker = ProgressTracker(self.store, on_progress)
        self.prompt_builder = PromptBuilder()

        # Execution state
        self._interrupted = False
        self._current_runner: Optional[ClaudeRunner] = None
        self.start_time: Optional[datetime] = None

    def setup(self) -> None:
        """Initialize state for execution."""
        self.store._project = self.project
        self.store.save()

    def run(self) -> bool:
        """Run the execution loop."""
        self._setup_signal_handlers()
        self.setup()
        self.start_time = datetime.now()

        for iteration in range(1, self.max_iterations + 1):
            if self._interrupted:
                break

            if self.project.is_complete:
                return True

            next_task = self.project.get_next_task()
            if not next_task:
                self.project.update_status()
                if self.project.is_complete:
                    return True
                break

            self.tracker.start_iteration(iteration)

            # Build prompt
            context = ExecutionContext(
                project=self.project,
                iteration=iteration,
                working_dir=self.working_dir,
                source_files=self.project.source_files,
                custom_instructions=self.custom_instructions,
                commit_prefix=self.commit_prefix,
                update_source=self.update_source,
            )
            prompt = self.prompt_builder.build(context)

            # Run Claude
            print(f"\n{'='*60}")
            print(f"  Iteration {iteration} of {self.max_iterations}")
            print(f"{'='*60}\n")

            self._current_runner = ClaudeRunner(
                working_dir=self.working_dir,
                idle_timeout=self.idle_timeout,
                model=self.model,
                skip_permissions=self.skip_permissions,
            )
            success, output, parsed = self._current_runner.run(prompt)

            # Process results
            self._process_iteration_result(iteration, parsed)

            status = "success" if parsed.is_success else "failed"
            self.tracker.end_iteration(status=status)

            if parsed.project_complete:
                return True

            if self._interrupted:
                break

            if iteration < self.max_iterations:
                import time
                print(f"\n  Sleeping {self.sleep_between}s before next iteration...")
                time.sleep(self.sleep_between)

        return self.project.is_complete

    def _process_iteration_result(self, iteration: int, parsed: ParsedOutput) -> None:
        """Process iteration results."""
        for task_id in parsed.completed_tasks:
            task = self.project.get_task_by_id(task_id)
            if task:
                self.tracker.complete_task(task_id)
                if self.update_source and task.source_file and task.source_line:
                    CheckboxUpdater.update_file_by_line(
                        task.source_file,
                        task.source_line,
                        completed=True
                    )

        for task_id in parsed.failed_tasks:
            self.tracker.fail_task(task_id, parsed.reason or "Unknown error")

        for task_id in parsed.blocked_tasks:
            task = self.project.get_task_by_id(task_id)
            if task:
                task.mark_blocked(parsed.reason or "Unknown blocker")

        self.project.update_status()
        self.store.save()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers."""
        def handler(signum, frame):
            self._interrupted = True
            if self._current_runner:
                self._current_runner.interrupt()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def interrupt(self) -> None:
        """Interrupt execution."""
        self._interrupted = True
        if self._current_runner:
            self._current_runner.interrupt()
