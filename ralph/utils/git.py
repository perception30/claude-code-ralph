"""Git utility functions."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitStatus:
    """Git repository status."""
    is_repo: bool = False
    branch: str = ""
    has_changes: bool = False
    staged_files: list[str] = None
    modified_files: list[str] = None
    untracked_files: list[str] = None

    def __post_init__(self):
        self.staged_files = self.staged_files or []
        self.modified_files = self.modified_files or []
        self.untracked_files = self.untracked_files or []


class GitHelper:
    """Helper for git operations."""

    def __init__(self, working_dir: str = "."):
        self.working_dir = Path(working_dir).resolve()

    def _run(
        self,
        *args: str,
        capture: bool = True
    ) -> tuple[bool, str]:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.working_dir,
                capture_output=capture,
                text=True,
            )
            return (result.returncode == 0, result.stdout.strip())
        except Exception as e:
            return (False, str(e))

    def is_repo(self) -> bool:
        """Check if directory is a git repository."""
        success, _ = self._run("rev-parse", "--is-inside-work-tree")
        return success

    def get_branch(self) -> str:
        """Get current branch name."""
        success, output = self._run("branch", "--show-current")
        return output if success else ""

    def get_status(self) -> GitStatus:
        """Get comprehensive git status."""
        status = GitStatus()

        if not self.is_repo():
            return status

        status.is_repo = True
        status.branch = self.get_branch()

        # Get status --porcelain
        success, output = self._run("status", "--porcelain")
        if not success:
            return status

        for line in output.split('\n'):
            if not line:
                continue

            indicator = line[:2]
            filename = line[3:]

            if indicator[0] != ' ' and indicator[0] != '?':
                status.staged_files.append(filename)

            if indicator[1] != ' ':
                if indicator[1] == '?':
                    status.untracked_files.append(filename)
                else:
                    status.modified_files.append(filename)

        status.has_changes = bool(
            status.staged_files or
            status.modified_files or
            status.untracked_files
        )

        return status

    def get_recent_commits(self, count: int = 5) -> list[dict]:
        """Get recent commit summaries."""
        success, output = self._run(
            "log",
            f"-{count}",
            "--pretty=format:%H|%h|%s|%an|%ar"
        )
        if not success:
            return []

        commits = []
        for line in output.split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "message": parts[2],
                    "author": parts[3],
                    "relative_time": parts[4],
                })
        return commits

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        status = self.get_status()
        return status.has_changes

    def stage_files(self, *files: str) -> bool:
        """Stage files for commit."""
        if not files:
            return True
        success, _ = self._run("add", *files)
        return success

    def commit(self, message: str) -> tuple[bool, str]:
        """Create a commit with the given message."""
        return self._run("commit", "-m", message)

    def get_diff(self, staged: bool = False) -> str:
        """Get diff output."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        success, output = self._run(*args)
        return output if success else ""

    def get_root(self) -> Optional[str]:
        """Get git repository root directory."""
        success, output = self._run("rev-parse", "--show-toplevel")
        return output if success else None
