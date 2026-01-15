"""Build AI prompts for generation tasks."""

from dataclasses import dataclass
from typing import Optional

from .base import GeneratorContext
from .templates import (
    PLANS_GENERATION_TEMPLATE,
    PRD_GENERATION_TEMPLATE,
    PRD_TO_PLANS_TEMPLATE,
    build_codebase_context,
    build_tech_stack_context,
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
        """
        Build prompt for PRD generation.

        Args:
            context: GeneratorContext with user prompt and settings

        Returns:
            Formatted prompt for Claude
        """
        additional_context = self._build_additional_context(context)

        return PRD_GENERATION_TEMPLATE.format(
            user_prompt=context.prompt,
            additional_context=additional_context,
        )

    def build_plans_prompt(self, context: GeneratorContext) -> str:
        """
        Build prompt for plans generation.

        Args:
            context: GeneratorContext with user prompt and settings

        Returns:
            Formatted prompt for Claude
        """
        additional_context = self._build_additional_context(context)
        num_phases = context.num_phases or "3-5"

        return PLANS_GENERATION_TEMPLATE.format(
            user_prompt=context.prompt,
            additional_context=additional_context,
            num_phases=num_phases,
        )

    def build_prd_to_plans_prompt(
        self,
        prd_content: str,
        context: GeneratorContext
    ) -> str:
        """
        Build prompt for converting PRD to plans.

        Args:
            prd_content: PRD markdown content
            context: GeneratorContext with settings

        Returns:
            Formatted prompt for Claude
        """
        additional_context = self._build_additional_context(context)

        return PRD_TO_PLANS_TEMPLATE.format(
            prd_content=prd_content,
            additional_context=additional_context,
        )

    def _build_additional_context(self, context: GeneratorContext) -> str:
        """Build additional context section for prompts."""
        parts: list[str] = []

        # Project name
        if context.project_name:
            parts.append(f"**Project Name:** {context.project_name}")

        # Tech stack
        if context.tech_stack:
            parts.append(build_tech_stack_context(context.tech_stack))

        # Codebase patterns
        if context.codebase_patterns:
            parts.append(build_codebase_context(context.codebase_patterns))

        # Custom context
        if context.additional_context:
            parts.append(context.additional_context)

        # Generation constraints
        if context.max_tasks_per_phase:
            parts.append(f"**Max tasks per phase:** {context.max_tasks_per_phase}")

        if context.num_phases:
            parts.append(f"**Target phases:** {context.num_phases}")

        return "\n".join(parts) if parts else "None specified"

    def estimate_token_count(self, prompt: str) -> int:
        """
        Estimate token count for a prompt.

        Args:
            prompt: Prompt string

        Returns:
            Estimated token count (rough approximation)
        """
        # Rough estimate: ~4 characters per token for English text
        return len(prompt) // 4

    def truncate_context(self, context: str, max_tokens: int = 2000) -> str:
        """
        Truncate context to fit within token limit.

        Args:
            context: Context string to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated context string
        """
        max_chars = max_tokens * 4
        if len(context) <= max_chars:
            return context

        # Truncate with ellipsis
        return context[:max_chars - 50] + "\n\n... (context truncated)"
