"""PRD (Product Requirements Document) generator."""

from typing import Optional

from .base import Generator, GeneratorContext, GeneratorResult
from .executor import GenerationExecutionConfig, GeneratorExecutor
from .prompt_builder import GeneratorPromptBuilder
from .prompt_loader import PromptLoader
from .validator import GeneratorValidator


class PRDGenerator(Generator):
    """Generates PRD documents from natural language prompts."""

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: int = 300,
        idle_timeout: int = 60,
        working_dir: str = ".",
        max_retries: int = 2,
        interactive: bool = True,
    ):
        """
        Initialize PRDGenerator.

        Args:
            model: Optional Claude model to use
            timeout: Execution timeout in seconds
            idle_timeout: Idle timeout for interactive mode
            working_dir: Working directory
            max_retries: Maximum retry attempts on validation failure
            interactive: Whether to stream output interactively
        """
        self.model = model
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        self.working_dir = working_dir
        self.max_retries = max_retries
        self.interactive = interactive

        self.prompt_loader = PromptLoader()
        self.prompt_builder = GeneratorPromptBuilder()
        self.validator = GeneratorValidator()

        exec_config = GenerationExecutionConfig(
            model=model,
            timeout=timeout,
            idle_timeout=idle_timeout,
            working_dir=working_dir,
            max_retries=max_retries,
            interactive=interactive,
        )
        self.executor = GeneratorExecutor(exec_config)

    def generate(self, context: GeneratorContext) -> GeneratorResult:
        """
        Generate a PRD document from the given context.

        Args:
            context: GeneratorContext with prompt and settings

        Returns:
            GeneratorResult with generated PRD content
        """
        # Load prompt if it's a file path
        user_prompt = self.prompt_loader.load(context.prompt)

        # Build generation prompt
        generation_prompt = self.prompt_builder.build_prd_prompt(
            GeneratorContext(
                prompt=user_prompt,
                output_path=context.output_path,
                project_name=context.project_name,
                additional_context=context.additional_context,
                tech_stack=context.tech_stack,
                codebase_patterns=context.codebase_patterns,
            )
        )

        # Execute generation with retry
        success, output, errors = self.executor.execute_with_retry(
            generation_prompt,
            validator=self.validate_output
        )

        if not success:
            return GeneratorResult(
                success=False,
                errors=errors or ["Generation failed"],
            )

        # Extract PRD content from output
        prd_content = self.executor.extract_prd_content(output)

        # Final validation
        validation_result = self.validator.validate_prd(prd_content)

        result = GeneratorResult(
            success=validation_result.is_valid,
            content=prd_content,
            errors=validation_result.errors,
            warnings=validation_result.warnings,
        )

        # Write output if successful
        if result.success and context.output_path:
            self.write_output(result, context.output_path)

        return result

    def validate_output(self, content: str) -> list[str]:
        """
        Validate generated PRD content.

        Args:
            content: Generated PRD content

        Returns:
            List of validation errors
        """
        # Extract PRD content first
        prd_content = self.executor.extract_prd_content(content)
        result = self.validator.validate_prd(prd_content)
        return result.errors

    def generate_from_file(
        self,
        prompt_file: str,
        output_path: str,
        project_name: Optional[str] = None,
    ) -> GeneratorResult:
        """
        Generate PRD from a prompt file.

        Args:
            prompt_file: Path to prompt file
            output_path: Path for output PRD
            project_name: Optional project name

        Returns:
            GeneratorResult with generated PRD
        """
        context = GeneratorContext(
            prompt=prompt_file,
            output_path=output_path,
            project_name=project_name,
        )
        return self.generate(context)

    def generate_from_prompt(
        self,
        prompt: str,
        output_path: str,
        project_name: Optional[str] = None,
        tech_stack: Optional[list[str]] = None,
    ) -> GeneratorResult:
        """
        Generate PRD from a direct prompt string.

        Args:
            prompt: Prompt text
            output_path: Path for output PRD
            project_name: Optional project name
            tech_stack: Optional list of technologies

        Returns:
            GeneratorResult with generated PRD
        """
        context = GeneratorContext(
            prompt=prompt,
            output_path=output_path,
            project_name=project_name,
            tech_stack=tech_stack or [],
        )
        return self.generate(context)

    def dry_run(self, context: GeneratorContext) -> str:
        """
        Perform a dry run and return the generation prompt.

        Args:
            context: GeneratorContext

        Returns:
            The prompt that would be sent to Claude
        """
        user_prompt = self.prompt_loader.load(context.prompt)
        return self.prompt_builder.build_prd_prompt(
            GeneratorContext(
                prompt=user_prompt,
                output_path=context.output_path,
                project_name=context.project_name,
                additional_context=context.additional_context,
                tech_stack=context.tech_stack,
                codebase_patterns=context.codebase_patterns,
            )
        )
