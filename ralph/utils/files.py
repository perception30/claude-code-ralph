"""File utility functions."""

import os
from pathlib import Path
from typing import Optional


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def find_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False
) -> list[Path]:
    """Find files matching a pattern in a directory."""
    path = Path(directory)
    if not path.is_dir():
        return []

    if recursive:
        return sorted(path.rglob(pattern))
    else:
        return sorted(path.glob(pattern))


def read_file_safe(
    file_path: str,
    default: str = ""
) -> str:
    """Safely read a file, returning default if it doesn't exist."""
    try:
        return Path(file_path).read_text(encoding='utf-8')
    except (FileNotFoundError, PermissionError):
        return default


def write_file_safe(
    file_path: str,
    content: str,
    create_dirs: bool = True
) -> bool:
    """Safely write to a file, optionally creating parent directories."""
    try:
        path = Path(file_path)
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return True
    except (PermissionError, OSError):
        return False


def get_relative_path(
    file_path: str,
    base_path: str
) -> str:
    """Get relative path from base, or return absolute if not relative."""
    try:
        return str(Path(file_path).relative_to(base_path))
    except ValueError:
        return file_path


def file_size_human(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
