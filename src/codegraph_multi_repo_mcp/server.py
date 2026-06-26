from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .codegraph_cli import CodeGraphCLI
from .config import load_config
from .models import AppConfig
from .orchestrator import MultiRepoOrchestrator
from .repo_registry import RepoRegistry


mcp = FastMCP("codegraph-multi-repo")


def build_orchestrator(config: AppConfig | None = None) -> MultiRepoOrchestrator:
    app_config = config or load_config()
    registry = RepoRegistry(app_config)
    cli = CodeGraphCLI(app_config.settings.codegraph_binary)
    return MultiRepoOrchestrator(registry, cli, app_config.settings)


@mcp.tool()
async def list_repos() -> dict[str, Any]:
    """List repositories configured for multi-repo CodeGraph exploration."""
    return await build_orchestrator().list_repos()


@mcp.tool()
async def refresh_repos(include_status: bool = False) -> dict[str, Any]:
    """Refresh repository metadata and optionally include `codegraph status` output."""
    return await build_orchestrator().refresh_repos(include_status=include_status)


@mcp.tool()
async def explore_repo(
    repo: str,
    query: str,
    max_files: int | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Explore one configured repository with `codegraph explore`."""
    return await build_orchestrator().explore_repo(
        repo,
        query,
        max_files=max_files,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
async def ask_multi_repo(
    question: str,
    repos: list[str] | None = None,
    max_repos: int | None = None,
    max_files_per_repo: int | None = None,
) -> dict[str, Any]:
    """Route a question to multiple repositories and run CodeGraph exploration."""
    return await build_orchestrator().ask_multi_repo(
        question,
        repos=repos,
        max_repos=max_repos,
        max_files_per_repo=max_files_per_repo,
    )


@mcp.tool()
async def trace_across_repos(
    identifier: str,
    repos: list[str] | None = None,
    max_repos: int | None = None,
    max_files_per_repo: int | None = None,
) -> dict[str, Any]:
    """Trace an identifier such as a symbol, API route, topic, DTO, or table across repositories."""
    return await build_orchestrator().trace_across_repos(
        identifier,
        repos=repos,
        max_repos=max_repos,
        max_files_per_repo=max_files_per_repo,
    )


def main() -> None:
    mcp.run()
