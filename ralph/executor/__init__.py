"""Executor module for running Claude."""

from .output import OutputParser, ParsedOutput
from .prompt import ExecutionContext, PromptBuilder
from .retry import RetryConfig


# Lazy imports for modules with external dependencies
def __getattr__(name: str):
    if name == "ClaudeRunner":
        from .runner import ClaudeRunner

        return ClaudeRunner
    if name == "RalphExecutor":
        from .runner import RalphExecutor

        return RalphExecutor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ClaudeRunner",
    "ExecutionContext",
    "OutputParser",
    "ParsedOutput",
    "PromptBuilder",
    "RalphExecutor",
    "RetryConfig",
]
