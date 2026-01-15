"""Prompt loader for generation tasks."""

from pathlib import Path


class PromptLoader:
    """Load prompts from various sources."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".prompt"}

    def __init__(self):
        self._cache: dict[str, str] = {}

    def load(self, source: str) -> str:
        """
        Load prompt from string or file.

        Args:
            source: Direct prompt string or path to prompt file

        Returns:
            Prompt content as string
        """
        # Check if it's a file path
        path = Path(source)
        if path.exists() and path.is_file():
            return self.load_file(str(path))

        # Return as direct prompt
        return source

    def load_file(self, file_path: str) -> str:
        """
        Load prompt from file.

        Args:
            file_path: Path to prompt file

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file extension not supported
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: {path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        # Check cache
        cache_key = str(path.resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]

        content = path.read_text(encoding='utf-8').strip()
        self._cache[cache_key] = content
        return content

    def load_directory(self, dir_path: str) -> dict[str, str]:
        """
        Load all prompt files from a directory.

        Args:
            dir_path: Path to directory containing prompt files

        Returns:
            Dictionary mapping filename to content
        """
        path = Path(dir_path)

        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        prompts: dict[str, str] = {}
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in path.glob(f"*{ext}"):
                prompts[file_path.name] = self.load_file(str(file_path))

        return prompts

    def validate(self, source: str) -> list[str]:
        """
        Validate prompt source.

        Args:
            source: Prompt string or file path

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        # Check if it's a file path
        path = Path(source)
        if path.exists():
            if path.is_file():
                if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    errors.append(
                        f"Unsupported file extension: {path.suffix}. "
                        f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
                    )
                try:
                    content = path.read_text(encoding='utf-8')
                    if not content.strip():
                        errors.append("Prompt file is empty")
                except OSError as e:
                    errors.append(f"Failed to read file: {e}")
            elif path.is_dir():
                # Check if directory has any prompt files
                has_prompts = False
                for ext in self.SUPPORTED_EXTENSIONS:
                    if list(path.glob(f"*{ext}")):
                        has_prompts = True
                        break
                if not has_prompts:
                    errors.append(f"No prompt files found in directory: {source}")
        else:
            # Treat as direct prompt - validate it's not empty
            if not source.strip():
                errors.append("Prompt cannot be empty")

        return errors

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()
