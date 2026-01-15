"""Execute Claude for generation tasks."""

import io
import json
import sys
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

    def execute(self, prompt: str) -> tuple[bool, str]:
        """Execute Claude with the generation prompt."""
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

        tee = TeeWriter()

        try:
            self.process = pexpect.spawn(
                "claude",
                args,
                cwd=self.config.working_dir,
                timeout=self.config.idle_timeout,
                encoding='utf-8',
                codec_errors='ignore',
            )

            self.process.logfile_read = tee

            while True:
                try:
                    self.process.expect(r'.+', timeout=self.config.idle_timeout)

                    # Check if Claude wrote status file FOR THIS TASK
                    # Validates task_id to prevent cross-process interference
                    if status_file.exists() and self._is_our_status_file(status_file):
                        break

                except pexpect.TIMEOUT:
                    break
                except pexpect.EOF:
                    break

            if self.process.isalive():
                self.process.sendline("/exit")
                try:
                    self.process.expect(pexpect.EOF, timeout=10)
                except pexpect.TIMEOUT:
                    self.process.terminate(force=True)

            return (True, tee.getvalue())

        except Exception as e:
            return (False, f"Execution failed: {e}")

        finally:
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
