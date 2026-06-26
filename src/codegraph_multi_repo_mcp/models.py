from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
    codegraph_binary: str = "codegraph"
    default_max_repos: int = Field(default=5, ge=1)
    default_max_files: int = Field(default=8, ge=1)
    per_repo_timeout_seconds: float = Field(default=20.0, gt=0)
    max_concurrency: int = Field(default=4, ge=1)


class RepoConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    path: Path
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("repository name cannot be empty")
        return stripped

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class AppConfig(BaseModel):
    settings: Settings = Field(default_factory=Settings)
    repos: list[RepoConfig]
