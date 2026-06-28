from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from .codegraph_cli import CodeGraphTimeout, CommandResult
from .models import RepoConfig, Settings
from .repo_registry import RepoRegistry
from .router import RepoCandidate, RepoRouter


class CodeGraphClient(Protocol):
    async def explore(self, repo_path: Path, query: str, *, max_files: int, timeout_seconds: float) -> CommandResult: ...
    async def status(self, repo_path: Path, *, timeout_seconds: float) -> CommandResult: ...


class MultiRepoOrchestrator:
    def __init__(self, registry: RepoRegistry, cli: CodeGraphClient, settings: Settings) -> None:
        self.registry = registry
        self.cli = cli
        self.settings = settings
        self.router = RepoRouter(registry.repos)

    async def list_repos(self) -> dict[str, object]:
        return {"repos": self.registry.list_repos()}

    async def refresh_repos(self, *, include_status: bool) -> dict[str, object]:
        repos = self.registry.repos
        results: list[dict[str, object]] = []
        for repo in repos:
            item = self._repo_metadata(repo)
            if include_status and item["path_exists"] and item["has_codegraph"]:
                command = await self.cli.status(repo.path, timeout_seconds=self.settings.per_repo_timeout_seconds)
                item["status"] = self._command_dict(command)
            results.append(item)
        return {"repos": results}

    async def explore_repo(
        self,
        repo: str,
        query: str,
        *,
        max_files: int | None,
        timeout_seconds: float | None,
    ) -> dict[str, object]:
        repo_config = self.registry.get(repo)
        return await self._explore_candidate(
            RepoCandidate(repo_config, score=100, reason="explicit-repo"),
            query,
            max_files=max_files or self.settings.default_max_files,
            timeout_seconds=timeout_seconds or self.settings.per_repo_timeout_seconds,
        )

    async def ask_multi_repo(
        self,
        question: str,
        *,
        repos: list[str] | None,
        max_repos: int | None,
        max_files_per_repo: int | None,
    ) -> dict[str, object]:
        candidates = self._select_candidates(question, repos, max_repos)
        query_results = await self._fanout(candidates, question, max_files_per_repo or self.settings.default_max_files)
        return self._aggregate(question, candidates, query_results)

    async def trace_across_repos(
        self,
        identifier: str,
        *,
        repos: list[str] | None,
        max_repos: int | None,
        max_files_per_repo: int | None,
    ) -> dict[str, object]:
        query = f"Trace identifier across repositories: {identifier}"
        return await self.ask_multi_repo(
            query,
            repos=repos,
            max_repos=max_repos,
            max_files_per_repo=max_files_per_repo,
        )

    def _select_candidates(self, question: str, repos: list[str] | None, max_repos: int | None) -> list[RepoCandidate]:
        limit = max_repos or self.settings.default_max_repos
        if repos:
            return [RepoCandidate(self.registry.get(repo), score=100, reason="explicit-repo") for repo in repos[:limit]]
        return self.router.route(question, max_repos=limit)

    async def _fanout(self, candidates: list[RepoCandidate], query: str, max_files: int) -> list[dict[str, object]]:
        semaphore = asyncio.Semaphore(self.settings.max_concurrency)

        async def run(candidate: RepoCandidate) -> dict[str, object]:
            async with semaphore:
                return await self._explore_candidate(
                    candidate,
                    query,
                    max_files=max_files,
                    timeout_seconds=self.settings.per_repo_timeout_seconds,
                )

        return await asyncio.gather(*(run(candidate) for candidate in candidates))

    async def _explore_candidate(
        self,
        candidate: RepoCandidate,
        query: str,
        *,
        max_files: int,
        timeout_seconds: float,
    ) -> dict[str, object]:
        repo = candidate.repo
        base: dict[str, object] = {
            "repo": repo.name,
            "path": str(repo.path),
            "query": query,
            "route_score": candidate.score,
            "route_reason": candidate.reason,
        }
        if not repo.path.exists():
            return {**base, "success": False, "recoverable": True, "error": "Repository path does not exist"}
        if not (repo.path / ".codegraph").is_dir():
            return {
                **base,
                "success": False,
                "recoverable": True,
                "error": "CodeGraph index not found",
                "hint": f"Run: codegraph init {repo.path}",
            }
        try:
            result = await self.cli.explore(
                repo.path,
                query,
                max_files=max_files,
                timeout_seconds=timeout_seconds,
            )
        except CodeGraphTimeout as exc:
            return {**base, "success": False, "recoverable": True, "error": str(exc)}
        return {**base, **self._command_dict(result)}

    def _aggregate(
        self,
        question: str,
        candidates: list[RepoCandidate],
        query_results: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "question": question,
            "repos_queried": [candidate.repo.name for candidate in candidates],
            "results": [item for item in query_results if item.get("success") is True],
            "errors": [item for item in query_results if item.get("success") is not True],
        }

    def _repo_metadata(self, repo: RepoConfig) -> dict[str, object]:
        return {
            "name": repo.name,
            "path": str(repo.path),
            "description": repo.description,
            "tags": repo.tags,
            "aliases": repo.aliases,
            "language": repo.language,
            "components": [component.model_dump() for component in repo.components],
            "path_exists": repo.path.exists(),
            "has_codegraph": (repo.path / ".codegraph").is_dir(),
        }

    def _command_dict(self, result: CommandResult) -> dict[str, object]:
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        }
