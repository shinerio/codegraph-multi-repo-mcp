from __future__ import annotations

from .models import AppConfig, RepoConfig


class RepoRegistry:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._by_name: dict[str, RepoConfig] = {}
        for repo in config.repos:
            self._by_name[repo.name] = repo
            for alias in repo.aliases:
                self._by_name[alias] = repo

    @property
    def repos(self) -> list[RepoConfig]:
        return list(self.config.repos)

    def get(self, name_or_alias: str) -> RepoConfig:
        try:
            return self._by_name[name_or_alias]
        except KeyError as exc:
            raise KeyError(f"Unknown repository: {name_or_alias}") from exc

    def list_repos(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for repo in self.config.repos:
            items.append(
                {
                    "name": repo.name,
                    "path": str(repo.path),
                    "description": repo.description,
                    "tags": repo.tags,
                    "aliases": repo.aliases,
                    "path_exists": repo.path.exists(),
                    "has_codegraph": (repo.path / ".codegraph").is_dir(),
                }
            )
        return items
