"""Repository cloning and file enumeration — Windows-safe."""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "java": (".java",),
    "go": (".go",),
}

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    "dist", "build", "target", ".idea", ".vscode", "vendor",
    "coverage", ".next", ".pytest_cache",
}


class RepositoryIngestionError(Exception):
    pass


def parse_github_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise RepositoryIngestionError(f"Cannot parse owner/repo from: {url}")
    owner, name = parts[0], parts[1].removesuffix(".git")
    return owner, name


def _get_clone_base() -> Path:
    """
    Return the clone base path, always resolved to an absolute Path.
    The validator in config already normalised backslashes to forward slashes,
    so Path() handles it correctly on all platforms.
    """
    raw = settings.clone_base_path  # e.g. "C:/tmp/cue_repos"
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


class RepositoryService:
    def __init__(self, base_path: str | None = None) -> None:
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = _get_clone_base()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Clone base path: %s", self.base_path)

    def clone(self, url: str, repo_id: str, branch: str | None = None) -> str:
        target_dir = self.base_path / repo_id
        # Always remove and recreate to avoid stale data
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(target_dir)]

        logger.info("Cloning %s into %s", url, target_dir)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=600, check=False,
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise RepositoryIngestionError("Clone timed out after 10 minutes")
        except FileNotFoundError:
            raise RepositoryIngestionError(
                "git not found. Please install Git and ensure it is on your PATH."
            )

        if proc.returncode != 0:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise RepositoryIngestionError(f"git clone failed: {proc.stderr.strip()}")

        self._validate_size(target_dir)
        return str(target_dir)

    def _validate_size(self, path: Path) -> None:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        limit = settings.max_repo_size_mb * 1024 * 1024
        if total > limit:
            shutil.rmtree(path, ignore_errors=True)
            raise RepositoryIngestionError(
                f"Repository too large ({total // 1024 // 1024} MB > {settings.max_repo_size_mb} MB limit)"
            )

    def enumerate_source_files(self, local_path: str) -> dict[str, list[str]]:
        root = Path(local_path)
        result: dict[str, list[str]] = {lang: [] for lang in LANGUAGE_EXTENSIONS}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            for lang, exts in LANGUAGE_EXTENSIONS.items():
                if path.suffix in exts:
                    result[lang].append(str(path))
                    break
        return {k: v for k, v in result.items() if v}

    def cleanup(self, local_path: str) -> None:
        shutil.rmtree(local_path, ignore_errors=True)
