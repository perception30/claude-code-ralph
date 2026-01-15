"""Executor module for running Claude."""

from .prompt import PromptBuilder, ExecutionContext
from .output import OutputParser, ParsedOutput
from .retry import RetryStrategy, RetryConfig

# Lazy imports for modules with external dependencies
def __getattr__(name):
    if name == "ClaudeRunner":
        from .runner import ClaudeRunner
        return ClaudeRunner
    if name == "RalphExecutor":
        from .runner import RalphExecutor
        return RalphExecutor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "PromptBuilder",
    "ExecutionContext",
    "OutputParser",
    "ParsedOutput",
    "RetryStrategy",
    "RetryConfig",
    "ClaudeRunner",
    "RalphExecutor",
]
