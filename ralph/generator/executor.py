"""Execute Claude for generation tasks."""

import io
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

                    # Check if Claude wrote status file
                    if status_file.exists():
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
