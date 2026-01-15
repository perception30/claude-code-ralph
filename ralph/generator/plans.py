"""Phased implementation plans generator."""

from pathlib import Path
from typing import Optional

from .base import Generator, GeneratorContext, GeneratorResult
from .executor import GenerationExecutionConfig, GeneratorExecutor
from .prompt_builder import GeneratorPromptBuilder
from .prompt_loader import PromptLoader


class PlansGenerator(Generator):
    """Generates phased implementation plans from natural language prompts."""

    def __init__(
        self,
        model: Optional[str] = None,
        idle_timeout: int = 60,
        working_dir: str = ".",
    ):
        self.model = model
        self.idle_timeout = idle_timeout
        self.working_dir = working_dir

        self.prompt_loader = PromptLoader()
        self.prompt_builder = GeneratorPromptBuilder()

        exec_config = GenerationExecutionConfig(
            model=model,
            idle_timeout=idle_timeout,
            working_dir=working_dir,
            expected_task_id="generate-plans",
        )
        self.executor = GeneratorExecutor(exec_config)

    def generate(self, context: GeneratorContext) -> GeneratorResult:
        """Generate phased plans - Claude writes files directly."""
        # Load prompt if it's a file path
        user_prompt = self.prompt_loader.load(context.prompt)

        # Build context
        gen_context = GeneratorContext(
            prompt=user_prompt,
            output_path=context.output_path,
            project_name=context.project_name,
            num_phases=context.num_phases,
            max_tasks_per_phase=context.max_tasks_per_phase,
        )

        # Build generation prompt
        prompt = self.prompt_builder.build_plans_prompt(gen_context)

        # Execute - Claude writes files and status directly
        success, output = self.executor.execute(prompt)

        return GeneratorResult(
            success=success,
            content=output,
            output_path=context.output_path,
        )

    def validate_output(self, content: str) -> list[str]:
        """Validation not needed - Claude handles it."""
        return []

    def generate_from_prd(
        self,
        prd_path: str,
        output_path: str,
        num_phases: Optional[int] = None,
    ) -> GeneratorResult:
        """Generate plans from an existing PRD file."""
        prd_file = Path(prd_path)
        if not prd_file.exists():
            return GeneratorResult(
                success=False,
                errors=[f"PRD file not found: {prd_path}"],
            )

        prd_content = prd_file.read_text(encoding='utf-8')

        context = GeneratorContext(
            prompt="",
            output_path=output_path,
            num_phases=num_phases,
        )

        prompt = self.prompt_builder.build_prd_to_plans_prompt(prd_content, context)

        success, output = self.executor.execute(prompt)

        return GeneratorResult(
            success=success,
            content=output,
            output_path=output_path,
        )

    def dry_run(self, context: GeneratorContext) -> str:
        """Return the prompt that would be sent to Claude."""
        user_prompt = self.prompt_loader.load(context.prompt)
        gen_context = GeneratorContext(
            prompt=user_prompt,
            output_path=context.output_path,
            project_name=context.project_name,
            num_phases=context.num_phases,
            max_tasks_per_phase=context.max_tasks_per_phase,
        )
        return self.prompt_builder.build_plans_prompt(gen_context)
