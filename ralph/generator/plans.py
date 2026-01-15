"""Phased implementation plans generator."""

from pathlib import Path
from typing import Optional

from .base import Generator, GeneratorContext, GeneratorResult
from .executor import GenerationExecutionConfig, GeneratorExecutor
from .prompt_builder import GeneratorPromptBuilder
from .prompt_loader import PromptLoader
from .validator import GeneratorValidator


class PlansGenerator(Generator):
    """Generates phased implementation plans from natural language prompts."""

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: int = 300,
        working_dir: str = ".",
        max_retries: int = 2,
    ):
        """
        Initialize PlansGenerator.

        Args:
            model: Optional Claude model to use
            timeout: Execution timeout in seconds
            working_dir: Working directory
            max_retries: Maximum retry attempts on validation failure
        """
        self.model = model
        self.timeout = timeout
        self.working_dir = working_dir
        self.max_retries = max_retries

        self.prompt_loader = PromptLoader()
        self.prompt_builder = GeneratorPromptBuilder()
        self.validator = GeneratorValidator()

        exec_config = GenerationExecutionConfig(
            model=model,
            timeout=timeout,
            working_dir=working_dir,
            max_retries=max_retries,
        )
        self.executor = GeneratorExecutor(exec_config)

    def generate(self, context: GeneratorContext) -> GeneratorResult:
        """
        Generate phased plans from the given context.

        Args:
            context: GeneratorContext with prompt and settings

        Returns:
            GeneratorResult with generated plan files
        """
        # Load prompt if it's a file path
        user_prompt = self.prompt_loader.load(context.prompt)

        # Build generation prompt
        generation_prompt = self.prompt_builder.build_plans_prompt(
            GeneratorContext(
                prompt=user_prompt,
                output_path=context.output_path,
                project_name=context.project_name,
                num_phases=context.num_phases,
                max_tasks_per_phase=context.max_tasks_per_phase,
                additional_context=context.additional_context,
                tech_stack=context.tech_stack,
                codebase_patterns=context.codebase_patterns,
            )
        )

        # Execute generation
        success, output, errors = self.executor.execute_with_retry(
            generation_prompt,
            validator=lambda o: self._validate_output_files(
                self.executor.extract_plan_files(o)
            )
        )

        if not success:
            return GeneratorResult(
                success=False,
                errors=errors or ["Generation failed"],
            )

        # Extract plan files from output
        plan_files = self.executor.extract_plan_files(output)

        if not plan_files:
            return GeneratorResult(
                success=False,
                errors=["No plan files could be extracted from output"],
            )

        # Final validation
        validation_result = self.validator.validate_plans(plan_files)

        result = GeneratorResult(
            success=validation_result.is_valid,
            files=plan_files,
            errors=validation_result.errors,
            warnings=validation_result.warnings,
        )

        # Write output if successful
        if result.success and context.output_path:
            self.write_output(result, context.output_path)

        return result

    def validate_output(self, content: str) -> list[str]:
        """
        Validate generated plans content.

        Args:
            content: Generated output content

        Returns:
            List of validation errors
        """
        files = self.executor.extract_plan_files(content)
        return self._validate_output_files(files)

    def _validate_output_files(self, files: dict[str, str]) -> list[str]:
        """Validate extracted plan files."""
        if not files:
            return ["No plan files found in output"]
        result = self.validator.validate_plans(files)
        return result.errors

    def generate_from_prd(
        self,
        prd_path: str,
        output_path: str,
        num_phases: Optional[int] = None,
    ) -> GeneratorResult:
        """
        Generate plans from an existing PRD file.

        Args:
            prd_path: Path to PRD file
            output_path: Directory for output plans
            num_phases: Optional number of phases to generate

        Returns:
            GeneratorResult with generated plans
        """
        # Read PRD content
        prd_file = Path(prd_path)
        if not prd_file.exists():
            return GeneratorResult(
                success=False,
                errors=[f"PRD file not found: {prd_path}"],
            )

        prd_content = prd_file.read_text(encoding='utf-8')

        # Build conversion context
        context = GeneratorContext(
            prompt=f"Convert this PRD to implementation plans:\n\n{prd_content}",
            output_path=output_path,
            num_phases=num_phases,
        )

        # Build conversion prompt
        generation_prompt = self.prompt_builder.build_prd_to_plans_prompt(
            prd_content, context
        )

        # Execute generation
        success, output, errors = self.executor.execute_with_retry(
            generation_prompt,
            validator=lambda o: self._validate_output_files(
                self.executor.extract_plan_files(o)
            )
        )

        if not success:
            return GeneratorResult(
                success=False,
                errors=errors or ["Conversion failed"],
            )

        # Extract plan files
        plan_files = self.executor.extract_plan_files(output)

        if not plan_files:
            return GeneratorResult(
                success=False,
                errors=["No plan files could be extracted from output"],
            )

        # Validate and return
        validation_result = self.validator.validate_plans(plan_files)

        result = GeneratorResult(
            success=validation_result.is_valid,
            files=plan_files,
            errors=validation_result.errors,
            warnings=validation_result.warnings,
        )

        if result.success and output_path:
            self.write_output(result, output_path)

        return result

    def generate_from_file(
        self,
        prompt_file: str,
        output_path: str,
        num_phases: Optional[int] = None,
        max_tasks_per_phase: int = 10,
    ) -> GeneratorResult:
        """
        Generate plans from a prompt file.

        Args:
            prompt_file: Path to prompt file
            output_path: Directory for output plans
            num_phases: Optional number of phases
            max_tasks_per_phase: Max tasks per phase

        Returns:
            GeneratorResult with generated plans
        """
        context = GeneratorContext(
            prompt=prompt_file,
            output_path=output_path,
            num_phases=num_phases,
            max_tasks_per_phase=max_tasks_per_phase,
        )
        return self.generate(context)

    def generate_from_prompt(
        self,
        prompt: str,
        output_path: str,
        project_name: Optional[str] = None,
        num_phases: Optional[int] = None,
        max_tasks_per_phase: int = 10,
        tech_stack: Optional[list[str]] = None,
    ) -> GeneratorResult:
        """
        Generate plans from a direct prompt string.

        Args:
            prompt: Prompt text
            output_path: Directory for output plans
            project_name: Optional project name
            num_phases: Optional number of phases
            max_tasks_per_phase: Max tasks per phase
            tech_stack: Optional list of technologies

        Returns:
            GeneratorResult with generated plans
        """
        context = GeneratorContext(
            prompt=prompt,
            output_path=output_path,
            project_name=project_name,
            num_phases=num_phases,
            max_tasks_per_phase=max_tasks_per_phase,
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
        return self.prompt_builder.build_plans_prompt(
            GeneratorContext(
                prompt=user_prompt,
                output_path=context.output_path,
                project_name=context.project_name,
                num_phases=context.num_phases,
                max_tasks_per_phase=context.max_tasks_per_phase,
                additional_context=context.additional_context,
                tech_stack=context.tech_stack,
                codebase_patterns=context.codebase_patterns,
            )
        )

    def create_directory_structure(self, output_path: str) -> None:
        """
        Create the output directory structure.

        Args:
            output_path: Path for plans directory
        """
        path = Path(output_path)
        path.mkdir(parents=True, exist_ok=True)
