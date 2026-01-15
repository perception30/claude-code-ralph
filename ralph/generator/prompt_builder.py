"""Build AI prompts for generation tasks."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import GeneratorContext
from .templates import (
    PLANS_GENERATION_TEMPLATE,
    PRD_GENERATION_TEMPLATE,
    PRD_TO_PLANS_TEMPLATE,
)


@dataclass
class GeneratorPromptConfig:
    """Configuration for prompt building."""
    include_examples: bool = True
    strict_format: bool = True
    max_context_length: int = 4000


class GeneratorPromptBuilder:
    """Builds prompts for PRD and plans generation."""

    def __init__(self, config: Optional[GeneratorPromptConfig] = None):
        self.config = config or GeneratorPromptConfig()

    def build_prd_prompt(self, context: GeneratorContext) -> str:
        """Build prompt for PRD generation."""
        output_path = str(Path(context.output_path).resolve())

        return PRD_GENERATION_TEMPLATE.format(
            user_prompt=context.prompt,
            output_path=output_path,
        )

    def build_plans_prompt(self, context: GeneratorContext) -> str:
        """Build prompt for plans generation."""
        output_path = str(Path(context.output_path).resolve())

        return PLANS_GENERATION_TEMPLATE.format(
            user_prompt=context.prompt,
            output_path=output_path,
        )

    def build_prd_to_plans_prompt(
        self,
        prd_content: str,
        context: GeneratorContext
    ) -> str:
        """Build prompt for converting PRD to plans."""
        output_path = str(Path(context.output_path).resolve())

        return PRD_TO_PLANS_TEMPLATE.format(
            prd_content=prd_content,
            output_path=output_path,
        )
