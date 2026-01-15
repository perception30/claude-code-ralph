"""Simple Claude runner - spawn and let it run."""

import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pexpect  # type: ignore[import-untyped]

from ..parser.checkbox import CheckboxUpdater
from ..state.identity import ProjectIdentity
from ..state.models import Project
from ..state.store import StateStore
from ..state.tracker import ProgressTracker
from .output import OutputParser, ParsedOutput
from .prompt import ExecutionContext, PromptBuilder
from .retry import RetryConfig


class ClaudeRunner:
    """Simple Claude runner - spawns claude and lets it output."""

    def __init__(
        self,
        working_dir: str = ".",
        idle_timeout: int = 10,
        model: Optional[str] = None,
        skip_permissions: bool = True,
        expected_task_id: Optional[str] = None,
    ):
        self.working_dir = os.path.abspath(working_dir)
        self.idle_timeout = idle_timeout
        self.model = model
        self.skip_permissions = skip_permissions
        self.expected_task_id = expected_task_id
        self.process: Optional[pexpect.spawn] = None
        self._interrupted = False

    def run(self, prompt: str) -> tuple[bool, str, ParsedOutput]:
        """
        Run Claude with the given prompt.
        Simply spawns the process and lets it output to terminal.
        """
        self._interrupted = False
        status_file = Path(self.working_dir) / ".ralph" / "status.json"

        # Clear status file before run
        if status_file.exists():
            status_file.unlink()

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

            # Keep waiting while there's output
            # After status file detected, use shorter timeout and max wait
            import time
            status_detected = False
            post_status_start = None
            post_status_idle_timeout = 3  # Short idle timeout after status
            max_post_status_wait = 10  # Max total wait after status (fallback)

            while True:
                try:
                    # Use shorter timeout after status is detected
                    timeout = post_status_idle_timeout if status_detected else self.idle_timeout
                    self.process.expect(r'.+', timeout=timeout)

                    # Check if Claude wrote the status file FOR THIS TASK
                    # Validates task_id to prevent cross-process interference
                    if status_file.exists() and not status_detected:
                        if self._is_our_status_file(status_file):
                            status_detected = True
                            post_status_start = time.time()

                    # Check max wait after status (fallback)
                    if status_detected and post_status_start:
                        if time.time() - post_status_start > max_post_status_wait:
                            break

                except pexpect.TIMEOUT:
                    # No output for timeout period - Claude is idle/done
                    break
                except pexpect.EOF:
                    # Process ended
                    break

            if self.process.isalive():
                self.process.sendline("/exit")
                try:
                    self.process.expect(pexpect.EOF, timeout=10)
                except pexpect.TIMEOUT:
                    self.process.terminate(force=True)

            # Get output for parsing
            output = ""
            if self.process.before:
                before = self.process.before
                if isinstance(before, bytes):
                    output = before.decode('utf-8', errors='ignore')
                else:
                    output = before

            # Read status from file (Claude writes here when done)
            parsed = self._read_status_file(status_file, output)
            return (True, output, parsed)

        except Exception as e:
            return (False, str(e), ParsedOutput(errors=[str(e)]))

        finally:
            if self.process:
                try:
                    if self.process.isalive():
                        self.process.terminate(force=True)
                except OSError:
                    pass
                self.process = None

    def _is_our_status_file(self, status_file: Path) -> bool:
        """Check if status file belongs to this process.

        Validates that the task_id in the status file matches our expected task.
        This prevents race conditions where one process reads another's status.
        If no expected_task_id is set, accepts any status file (legacy behavior).
        """
        if not self.expected_task_id:
            # Legacy mode: accept any status file
            return True

        try:
            data = json.loads(status_file.read_text())
            file_task_id = data.get("task_id")

            # Check if task_id matches (works for COMPLETED, BLOCKED, FAILED, PROJECT_COMPLETE)
            return bool(file_task_id == self.expected_task_id)
        except (OSError, json.JSONDecodeError):
            # File might be partially written, ignore for now
            return False

    def _read_status_file(self, status_file: Path, output: str) -> ParsedOutput:
        """Read status from file written by Claude."""
        parsed = ParsedOutput(raw_output=output)

        if status_file.exists():
            try:
                data = json.loads(status_file.read_text())
                status = data.get("status", "").upper()

                if status == "COMPLETED":
                    parsed.task_completed = True
                    parsed.task_status = "COMPLETED"
                    parsed.task_id = data.get("task_id")
                    if parsed.task_id:
                        parsed.completed_tasks.append(parsed.task_id)

                elif status == "BLOCKED":
                    parsed.task_status = "BLOCKED"
                    parsed.task_id = data.get("task_id")
                    parsed.reason = data.get("reason")
                    if parsed.task_id:
                        parsed.blocked_tasks.append(parsed.task_id)

                elif status == "FAILED":
                    parsed.task_status = "FAILED"
                    parsed.task_id = data.get("task_id")
                    parsed.reason = data.get("reason")
                    if parsed.task_id:
                        parsed.failed_tasks.append(parsed.task_id)

                elif status == "PROJECT_COMPLETE":
                    parsed.project_complete = True

            except (OSError, json.JSONDecodeError):
                pass

        # Fallback: also check output for markers
        if not parsed.task_completed and not parsed.project_complete:
            parsed = OutputParser.parse(output)

        return parsed

    def interrupt(self) -> None:
        """Interrupt the current run."""
        self._interrupted = True
        if self.process:
            try:
                self.process.terminate(force=True)
            except OSError:
                pass


class RalphExecutor:
    """Orchestrates the Ralph execution loop."""

    def __init__(
        self,
        project: Project,
        working_dir: str = ".",
        max_iterations: int = 50,
        idle_timeout: int = 10,
        sleep_between: int = 2,
        model: Optional[str] = None,
        skip_permissions: bool = True,
        custom_instructions: str = "",
        commit_prefix: str = "feat:",
        update_source: bool = True,
        on_output: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
        retry_config: Optional[RetryConfig] = None,
        project_identity: Optional[ProjectIdentity] = None,
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
        self.project_identity = project_identity

        # State management - use project-specific directory if identity provided
        self.store = StateStore(working_dir, project_identity=project_identity)
        self.tracker = ProgressTracker(self.store, on_progress)
        self.prompt_builder = PromptBuilder()

        # Execution state
        self._interrupted = False
        self._current_runner: Optional[ClaudeRunner] = None
        self.start_time: Optional[datetime] = None

    def setup(self) -> None:
        """Initialize state for execution.

        Merges the provided project with any existing state to preserve
        task completion status from previous runs.
        """
        # Merge with existing state to preserve progress
        self.project = self.store.merge_with_existing(self.project)
        self.store._project = self.project
        self.store.save()

    def run(self) -> bool:
        """Run the execution loop."""
        self._setup_signal_handlers()
        self.setup()
        self.start_time = datetime.now()

        # Continue from last iteration + 1
        start_iteration = self.project.current_iteration + 1
        end_iteration = start_iteration + self.max_iterations

        for iteration in range(start_iteration, end_iteration):
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
            print(f"  Iteration {iteration} (max additional: {self.max_iterations})")
            print(f"{'='*60}\n")

            self._current_runner = ClaudeRunner(
                working_dir=self.working_dir,
                idle_timeout=self.idle_timeout,
                model=self.model,
                skip_permissions=self.skip_permissions,
                expected_task_id=next_task.id,
            )
            success, output, parsed = self._current_runner.run(prompt)

            # Process results
            self._process_iteration_result(iteration, parsed)

            status = "success" if parsed.is_success else "failed"
            self.tracker.end_iteration(status=status)

            if self._interrupted:
                break

            # Decision based on status file
            if parsed.project_complete:
                print("\n  ✓ PROJECT_COMPLETE - All done!")
                return True

            if parsed.task_status == "BLOCKED":
                print(f"\n  ⊘ Task BLOCKED: {parsed.reason or 'Unknown'}")
                break

            if parsed.task_status == "FAILED":
                print(f"\n  ✗ Task FAILED: {parsed.reason or 'Unknown'}")
                break

            # Task completed - check if more tasks
            self.project.update_status()
            next_task = self.project.get_next_task()

            if not next_task or self.project.is_complete:
                print("\n  ✓ All tasks completed!")
                return True

            # More tasks - continue
            print(f"\n  ✓ Task done. Next: {next_task.name}")
            if iteration < self.max_iterations:
                import time
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
        def handler(_signum, _frame):
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
