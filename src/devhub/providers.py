from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

from .core import DevhubError, git


class GitHubReadback(Protocol):
    def read_commit(self, repository: str, revision: str) -> dict: ...


class CIReadback(Protocol):
    def read_run(self, repository: str, run_id: str) -> dict: ...


class TargetHostReadback(Protocol):
    def read_release(self, project_id: str, revision: str) -> dict: ...


class LocalGitProvider:
    """Read-only Git access to commits, files, and blobs in a local checkout."""

    def __init__(self, checkout: Path):
        self.checkout = checkout.resolve()
        self.repo_root = Path(git(self.checkout, "rev-parse", "--show-toplevel")).resolve()
        self.base_path = self.checkout.relative_to(self.repo_root).as_posix()

    def read_commit(self, revision: str) -> str:
        return git(self.checkout, "rev-parse", "--verify", "--end-of-options",
                   f"{revision}^{{commit}}")

    def read_file(self, revision: str, relative_path: str) -> bytes:
        windows_path = PureWindowsPath(relative_path)
        path = PurePosixPath(relative_path)
        if (windows_path.is_absolute() or windows_path.drive or ".." in windows_path.parts
                or path.is_absolute() or ".." in path.parts):
            raise DevhubError(f"Read path must be checkout-relative: {relative_path}")
        commit = self.read_commit(revision)
        return git_bytes(self.repo_root, "show", f"{commit}:{self._relative(relative_path)}")

    def read_blob(self, revision: str, relative_path: str) -> bytes:
        path = PurePosixPath(relative_path)
        windows_path = PureWindowsPath(relative_path)
        if (path.is_absolute() or ".." in path.parts or windows_path.is_absolute()
                or windows_path.drive or ".." in windows_path.parts):
            raise DevhubError(f"Read path must be checkout-relative: {relative_path}")
        commit = self.read_commit(revision)
        blob = git(self.repo_root, "rev-parse", "--verify", f"{commit}:{self._relative(relative_path)}")
        return git_bytes(self.repo_root, "cat-file", "blob", blob)

    def _relative(self, relative_path: str) -> str:
        return relative_path if self.base_path == "." else f"{self.base_path}/{relative_path}"


def git_bytes(checkout: Path, *args: str) -> bytes:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(checkout), *args],
        capture_output=True, check=False,
    )
    if result.returncode:
        raise DevhubError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout
