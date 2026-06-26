from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import AppConfig


class ConfigError(RuntimeError):
    """Raised when repository configuration cannot be loaded."""


DEFAULT_CONFIG_PATHS = (
    Path("./config/repos.yaml"),
    Path("~/.config/codegraph-multi-repo-mcp/repos.yaml").expanduser(),
)


def candidate_config_paths() -> list[Path]:
    env_path = os.environ.get("CODEGRAPH_MULTI_REPO_CONFIG")
    paths: list[Path] = []
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.extend(DEFAULT_CONFIG_PATHS)
    return paths


def find_config_path() -> Path:
    for path in candidate_config_paths():
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in candidate_config_paths())
    raise ConfigError(f"Config file not found. Searched: {searched}")


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path).expanduser() if path is not None else find_config_path()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not raw.get("repos"):
        raise ConfigError("Config must contain at least one repository in 'repos'")

    try:
        config = AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid config in {config_path}: {exc}") from exc

    names: set[str] = set()
    for repo in config.repos:
        if repo.name in names:
            raise ConfigError(f"Duplicate repository name: {repo.name}")
        names.add(repo.name)

    return config
