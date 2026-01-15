"""PRD (Product Requirements Document) generator."""

from typing import Optional

from .base import Generator, GeneratorContext, GeneratorResult
from .executor import GenerationExecutionConfig, GeneratorExecutor
from .prompt_builder import GeneratorPromptBuilder
from .prompt_loader import PromptLoader


class PRDGenerator(Generator):
    """Generates PRD documents from natural language prompts."""

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
            expected_task_id="generate-prd",
        )
        self.executor = GeneratorExecutor(exec_config)

    def generate(self, context: GeneratorContext) -> GeneratorResult:
        """Generate a PRD - Claude writes file directly."""
        # Load prompt if it's a file path
        user_prompt = self.prompt_loader.load(context.prompt)

        # Build context with user prompt
        gen_context = GeneratorContext(
            prompt=user_prompt,
            output_path=context.output_path,
            project_name=context.project_name,
        )

        # Build generation prompt
        prompt = self.prompt_builder.build_prd_prompt(gen_context)

        # Execute - Claude writes file and status directly
        success, output = self.executor.execute(prompt)

        return GeneratorResult(
            success=success,
            content=output,
            output_path=context.output_path,
        )

    def validate_output(self, content: str) -> list[str]:
        """Validation not needed - Claude handles it."""
        return []

    def dry_run(self, context: GeneratorContext) -> str:
        """Return the prompt that would be sent to Claude."""
        user_prompt = self.prompt_loader.load(context.prompt)
        gen_context = GeneratorContext(
            prompt=user_prompt,
            output_path=context.output_path,
            project_name=context.project_name,
        )
        return self.prompt_builder.build_prd_prompt(gen_context)
