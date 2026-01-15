"""Execute Claude for generation tasks."""

import re
import sys
from dataclasses import dataclass
from typing import Callable, Optional

import pexpect  # type: ignore[import-untyped]


@dataclass
class GenerationExecutionConfig:
    """Configuration for generation execution."""
    model: Optional[str] = None
    timeout: int = 300  # 5 minutes default
    idle_timeout: int = 60  # Idle timeout for interactive mode
    max_retries: int = 2
    working_dir: str = "."
    skip_permissions: bool = True
    interactive: bool = True  # Stream output to terminal
    on_output: Optional[Callable[[str], None]] = None


class GeneratorExecutor:
    """Executes Claude for generation tasks."""

    def __init__(self, config: Optional[GenerationExecutionConfig] = None):
        self.config = config or GenerationExecutionConfig()
        self.process: Optional[pexpect.spawn] = None
        self._output_buffer: list[str] = []

    def execute(self, prompt: str) -> tuple[bool, str]:
        """
        Execute Claude with the generation prompt.

        Args:
            prompt: Generation prompt to send to Claude

        Returns:
            Tuple of (success, output_content)
        """
        if self.config.interactive:
            return self._execute_interactive(prompt)
        else:
            return self._execute_batch(prompt)

    def _execute_interactive(self, prompt: str) -> tuple[bool, str]:
        """Execute Claude interactively with real-time output streaming."""
        args = []

        if self.config.skip_permissions:
            args.append("--dangerously-skip-permissions")

        if self.config.model:
            args.extend(["--model", self.config.model])

        args.append(prompt)

        self._output_buffer = []

        try:
            # Spawn claude - output goes directly to terminal
            self.process = pexpect.spawn(
                "claude",
                args,
                cwd=self.config.working_dir,
                timeout=self.config.idle_timeout,
                encoding='utf-8',
                codec_errors='ignore',
            )

            # Stream output directly to stdout
            self.process.logfile_read = sys.stdout

            # Keep waiting while there's output
            while True:
                try:
                    self.process.expect(r'.+', timeout=self.config.idle_timeout)

                    # Capture output for later processing
                    if self.process.after:
                        self._output_buffer.append(self.process.after)

                except pexpect.TIMEOUT:
                    # No output for idle_timeout - Claude is idle/done
                    break
                except pexpect.EOF:
                    # Process ended
                    break

            # Gracefully exit if still running
            if self.process.isalive():
                self.process.sendline("/exit")
                try:
                    self.process.expect(pexpect.EOF, timeout=10)
                except pexpect.TIMEOUT:
                    self.process.terminate(force=True)

            # Collect all output
            output = "".join(self._output_buffer)

            # Also get any remaining buffer content
            if self.process.before:
                before = self.process.before
                if isinstance(before, bytes):
                    output += before.decode('utf-8', errors='ignore')
                elif isinstance(before, str):
                    output += before

            return (True, output)

        except pexpect.exceptions.ExceptionPexpect as e:
            return (False, f"Claude execution failed: {e}")
        except FileNotFoundError:
            return (False, "Claude CLI not found. Please install it first.")
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

    def _execute_batch(self, prompt: str) -> tuple[bool, str]:
        """Execute Claude in batch mode (non-interactive)."""
        import subprocess

        args = ["claude", "--print"]

        if self.config.skip_permissions:
            args.append("--dangerously-skip-permissions")

        if self.config.model:
            args.extend(["--model", self.config.model])

        args.append(prompt)

        try:
            result = subprocess.run(
                args,
                cwd=self.config.working_dir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )

            output = result.stdout
            if result.returncode != 0:
                error = result.stderr or "Unknown error"
                return (False, f"Claude execution failed: {error}")

            return (True, output)

        except subprocess.TimeoutExpired:
            return (False, f"Claude execution timed out after {self.config.timeout}s")
        except FileNotFoundError:
            return (False, "Claude CLI not found. Please install it first.")
        except Exception as e:
            return (False, f"Execution failed: {e}")

    def execute_with_retry(
        self,
        prompt: str,
        validator: Optional[Callable[[str], list[str]]] = None
    ) -> tuple[bool, str, list[str]]:
        """
        Execute Claude with retry on validation failure.

        Args:
            prompt: Generation prompt
            validator: Optional function to validate output

        Returns:
            Tuple of (success, output, errors)
        """
        all_errors: list[str] = []

        for attempt in range(self.config.max_retries + 1):
            if attempt > 0:
                print(f"\n{'='*60}")
                print(f"  Retry attempt {attempt + 1}")
                print(f"{'='*60}\n")

            success, output = self.execute(prompt)

            if not success:
                all_errors.append(f"Attempt {attempt + 1}: {output}")
                continue

            # Validate if validator provided
            if validator:
                errors = validator(output)
                if errors:
                    all_errors.extend(
                        [f"Attempt {attempt + 1}: {e}" for e in errors]
                    )
                    # Modify prompt for retry
                    prompt = self._build_retry_prompt(prompt, errors)
                    continue

            return (True, output, [])

        return (False, "", all_errors)

    def _build_retry_prompt(self, original_prompt: str, errors: list[str]) -> str:
        """Build retry prompt with error feedback."""
        error_feedback = "\n".join(f"- {e}" for e in errors)

        return f"""{original_prompt}

## PREVIOUS ATTEMPT FAILED
The previous generation had the following errors:
{error_feedback}

Please fix these issues and regenerate."""

    def extract_prd_content(self, output: str) -> str:
        """
        Extract PRD markdown content from Claude's output.

        Args:
            output: Raw Claude output

        Returns:
            Extracted PRD content
        """
        # Try to extract content between markdown code blocks
        code_block_match = re.search(
            r'```(?:markdown)?\n(.*?)```',
            output,
            re.DOTALL
        )
        if code_block_match:
            return code_block_match.group(1).strip()

        # Look for PRD header
        prd_match = re.search(r'(#\s+PRD:.*)', output, re.DOTALL)
        if prd_match:
            return prd_match.group(1).strip()

        # Return full output if no markers found
        return output.strip()

    def extract_plan_files(self, output: str) -> dict[str, str]:
        """
        Extract plan files from Claude's output.

        Args:
            output: Raw Claude output

        Returns:
            Dictionary of filename -> content
        """
        files: dict[str, str] = {}

        # Pattern for file markers
        file_pattern = re.compile(
            r'===FILE:\s*(.+?)\s*===\n(.*?)===END FILE===',
            re.DOTALL
        )

        for match in file_pattern.finditer(output):
            filename = match.group(1).strip()
            content = match.group(2).strip()
            files[filename] = content

        # Fallback: try to find markdown sections
        if not files:
            files = self._extract_files_fallback(output)

        return files

    def _extract_files_fallback(self, output: str) -> dict[str, str]:
        """Fallback extraction for plan files."""
        files: dict[str, str] = {}

        # Look for file references like "### 00-overview.md" or "## File: 01-setup.md"
        file_header_pattern = re.compile(
            r'^(?:###?\s+)?(?:File:\s*)?(\d{2}-[\w-]+\.md)\s*$',
            re.MULTILINE
        )

        matches = list(file_header_pattern.finditer(output))
        for i, match in enumerate(matches):
            filename = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
            content = output[start:end].strip()

            # Clean up the content
            if content.startswith("```"):
                content = re.sub(r'^```(?:markdown)?\n?', '', content)
                content = re.sub(r'```$', '', content)

            files[filename] = content.strip()

        # Last resort: if single file detected, use overview name
        if not files and re.search(r'^#\s+.+Master Plan', output, re.MULTILINE):
            files["00-overview.md"] = output.strip()

        return files

    def interrupt(self) -> None:
        """Interrupt the current execution."""
        if self.process:
            try:
                self.process.terminate(force=True)
            except OSError:
                pass


def create_executor(
    model: Optional[str] = None,
    timeout: int = 300,
    idle_timeout: int = 60,
    working_dir: str = ".",
    interactive: bool = True,
) -> GeneratorExecutor:
    """
    Factory function to create a GeneratorExecutor.

    Args:
        model: Optional Claude model to use
        timeout: Execution timeout in seconds
        idle_timeout: Idle timeout for interactive mode
        working_dir: Working directory for execution
        interactive: Whether to stream output interactively

    Returns:
        Configured GeneratorExecutor
    """
    config = GenerationExecutionConfig(
        model=model,
        timeout=timeout,
        idle_timeout=idle_timeout,
        working_dir=working_dir,
        interactive=interactive,
    )
    return GeneratorExecutor(config)
