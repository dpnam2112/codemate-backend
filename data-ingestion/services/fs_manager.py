#!fs_manager.py
import fsspec
from fsspec.spec import AbstractFileSystem
from typing import Any


class FSManager:
    """File system manager using fsspec for abstracted file system operations."""

    def __init__(self, protocol: str = "file", **fs_options: Any) -> None:
        """Initialize the FSManager.

        Args:
            protocol: The protocol to use with fsspec.
            **fs_options: Additional options for fsspec filesystem.
        """
        self.fs: AbstractFileSystem = fsspec.filesystem(protocol, **fs_options)

    def exists(self, path: str) -> bool:
        """Check if a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        return self.fs.exists(path)

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        """Make directories recursively.

        Args:
            path: The directory path.
            exist_ok: Whether to ignore if the directory exists.
        """
        self.fs.makedirs(path, exist_ok=exist_ok)

    def open(self, path: str, mode: str = "rb", **kwargs: Any):
        """Open a file at the given path.

        Args:
            path: The file path.
            mode: The mode to open the file.
            **kwargs: Additional arguments.

        Returns:
            A file-like object.
        """
        return self.fs.open(path, mode, **kwargs)

