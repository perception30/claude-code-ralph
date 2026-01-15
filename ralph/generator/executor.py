"""Execute Claude for generation tasks."""

import io
import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pexpect  # type: ignore[import-untyped]


@dataclass
class GenerationExecutionConfig:
    """Configuration for generation execution."""
    model: Optional[str] = None
    idle_timeout: int = 60
    working_dir: str = "."
    skip_permissions: bool = True
    expected_task_id: Optional[str] = None


class TeeWriter:
    """Writes to both stdout and captures output."""

    def __init__(self):
        self.captured = io.StringIO()

    def write(self, data: str) -> int:
        sys.stdout.write(data)
        sys.stdout.flush()
        self.captured.write(data)
        return len(data)

    def flush(self) -> None:
        sys.stdout.flush()

    def getvalue(self) -> str:
        return str(self.captured.getvalue())


class GeneratorExecutor:
    """Executes Claude for generation tasks."""

    def __init__(self, config: Optional[GenerationExecutionConfig] = None):
        self.config = config or GenerationExecutionConfig()
        self.process: Optional[pexpect.spawn] = None
        self._stop_interaction = False
        self._captured_output = io.StringIO()
        self._last_output_time: Optional[float] = None

    def _is_our_status_file(self, status_file: Path) -> bool:
        """Check if status file belongs to this process.

        Validates that the task_id in the status file matches our expected task.
        This prevents race conditions where one process reads another's status.
        """
        if not self.config.expected_task_id:
            # Legacy mode: accept any status file
            return True

        try:
            data = json.loads(status_file.read_text())
            file_task_id = data.get("task_id")
            status = data.get("status", "").upper()

            # COMPLETED status with matching task_id
            if status == "COMPLETED" and file_task_id == self.config.expected_task_id:
                return True

            return False
        except (OSError, json.JSONDecodeError):
            # File might be partially written, ignore for now
            return False

    def _monitor_status_file(self, status_file: Path) -> None:
        """Background thread to monitor status file and signal completion."""
        status_detected = False
        post_status_start = None
        max_post_status_wait = 30  # Max wait after status detected (fallback)
        idle_threshold = 3  # Exit after 3 seconds of no output

        while not self._stop_interaction:
            if status_file.exists() and self._is_our_status_file(status_file):
                if not status_detected:
                    status_detected = True
                    post_status_start = time.time()

                # Check if we should exit based on idle time or max wait
                if post_status_start:
                    elapsed = time.time() - post_status_start

                    # Primary: Exit after idle period (no output for idle_threshold seconds)
                    if self._last_output_time:
                        idle_time = time.time() - self._last_output_time
                        if idle_time > idle_threshold:
                            self._stop_interaction = True
                            if self.process and self.process.isalive():
                                try:
                                    # Send SIGTERM to gracefully terminate Claude CLI
                                    import signal as _signal
                                    os.kill(self.process.pid, _signal.SIGTERM)
                                except (OSError, ProcessLookupError):
                                    pass
                            break

                    # Fallback: Exit after max wait regardless of output
                    if elapsed > max_post_status_wait:
                        self._stop_interaction = True
                        if self.process and self.process.isalive():
                            try:
                                import signal as _signal
                                os.kill(self.process.pid, _signal.SIGTERM)
                            except (OSError, ProcessLookupError):
                                pass
                        break
            time.sleep(0.5)  # Check more frequently

    def _output_filter(self, data: bytes) -> bytes:
        """Filter to capture output while passing it through."""
        try:
            text = data.decode('utf-8', errors='ignore')
            self._captured_output.write(text)
            # Track last output time for idle detection
            self._last_output_time = time.time()
        except Exception:
            pass
        return data

    def execute(self, prompt: str) -> tuple[bool, str]:
        """Execute Claude with the generation prompt.

        Uses pexpect.interact() to allow bidirectional I/O, enabling
        Claude to ask questions and receive user input.
        """
        args = []

        if self.config.skip_permissions:
            args.append("--dangerously-skip-permissions")

        if self.config.model:
            args.extend(["--model", self.config.model])

        args.append(prompt)

        # Status file path
        status_file = Path(self.config.working_dir) / ".ralph" / "status.json"
        status_file.parent.mkdir(parents=True, exist_ok=True)

        if status_file.exists():
            status_file.unlink()

        self._stop_interaction = False
        self._captured_output = io.StringIO()
        self._last_output_time = None

        try:
            # Check if we're in a real terminal (not piped/redirected)
            is_interactive = os.isatty(sys.stdin.fileno())

            self.process = pexpect.spawn(
                "claude",
                args,
                cwd=self.config.working_dir,
                timeout=None,  # No timeout - we use interact() mode
                encoding=None,  # Use bytes for interact()
                codec_errors='ignore',
            )

            # Start background thread to monitor status file
            monitor_thread = threading.Thread(
                target=self._monitor_status_file,
                args=(status_file,),
                daemon=True
            )
            monitor_thread.start()

            if is_interactive:
                # Interactive mode: use interact() for bidirectional I/O
                # This allows Claude to ask questions and user to respond
                try:
                    self.process.interact(output_filter=self._output_filter)
                except OSError:
                    # Process may have terminated
                    pass
            else:
                # Non-interactive mode: fall back to expect loop
                tee = TeeWriter()
                self.process.logfile_read = tee

                while True:
                    try:
                        self.process.expect(r'.+', timeout=self.config.idle_timeout)

                        if status_file.exists() and self._is_our_status_file(status_file):
                            break

                    except pexpect.TIMEOUT:
                        break
                    except pexpect.EOF:
                        break

                self._captured_output.write(tee.getvalue())

            # Signal monitor thread to stop
            self._stop_interaction = True
            monitor_thread.join(timeout=2)

            # Clean up process
            if self.process and self.process.isalive():
                try:
                    # Send SIGTERM to gracefully terminate Claude CLI
                    import signal as _signal
                    os.kill(self.process.pid, _signal.SIGTERM)
                    self.process.expect(pexpect.EOF, timeout=10)
                except (pexpect.TIMEOUT, pexpect.EOF, OSError, ProcessLookupError):
                    self.process.terminate(force=True)

            return (True, self._captured_output.getvalue())

        except Exception as e:
            return (False, f"Execution failed: {e}")

        finally:
            self._stop_interaction = True
            if self.process:
                try:
                    if self.process.isalive():
                        self.process.terminate(force=True)
                except OSError:
                    pass
                self.process = None

    def interrupt(self) -> None:
        """Interrupt the current execution."""
        if self.process:
            try:
                self.process.terminate(force=True)
            except OSError:
                pass
