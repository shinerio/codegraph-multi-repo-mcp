from pathlib import Path

import pytest

from codegraph_multi_repo_mcp.codegraph_cli import CommandResult
from codegraph_multi_repo_mcp.models import AppConfig, RepoConfig, Settings
from codegraph_multi_repo_mcp.orchestrator import MultiRepoOrchestrator
from codegraph_multi_repo_mcp.repo_registry import RepoRegistry


class FakeCLI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int, float]] = []

    async def explore(self, repo_path: Path, query: str, *, max_files: int, timeout_seconds: float) -> CommandResult:
        self.calls.append((repo_path.name, query, max_files, timeout_seconds))
        if repo_path.name == "broken":
            return CommandResult(False, "", "boom", 2, 12)
        return CommandResult(True, f"output for {repo_path.name}", "", 0, 10)

    async def status(self, repo_path: Path, *, timeout_seconds: float) -> CommandResult:
        return CommandResult(True, f"status for {repo_path.name}", "", 0, 5)


def make_orchestrator(tmp_path: Path) -> tuple[MultiRepoOrchestrator, FakeCLI]:
    repos = []
    for name in ["orders", "billing", "broken"]:
        path = tmp_path / name
        path.mkdir()
        (path / ".codegraph").mkdir()
        repos.append(RepoConfig(name=name, path=path, tags=[name], description=f"{name} service"))
    config = AppConfig(
        settings=Settings(default_max_repos=2, default_max_files=4, per_repo_timeout_seconds=9, max_concurrency=2),
        repos=repos,
    )
    cli = FakeCLI()
    return MultiRepoOrchestrator(RepoRegistry(config), cli, config.settings), cli


@pytest.mark.asyncio
async def test_explore_repo_returns_single_repo_result(tmp_path: Path) -> None:
    orchestrator, cli = make_orchestrator(tmp_path)

    result = await orchestrator.explore_repo("orders", "create flow", max_files=None, timeout_seconds=None)

    assert result["repo"] == "orders"
    assert result["success"] is True
    assert result["stdout"] == "output for orders"
    assert cli.calls == [("orders", "create flow", 4, 9)]


@pytest.mark.asyncio
async def test_ask_multi_repo_routes_and_fans_out(tmp_path: Path) -> None:
    orchestrator, cli = make_orchestrator(tmp_path)

    result = await orchestrator.ask_multi_repo("orders billing interaction", repos=None, max_repos=2, max_files_per_repo=3)

    assert result["repos_queried"] == ["orders", "billing"]
    assert [item["repo"] for item in result["results"]] == ["orders", "billing"]
    assert result["errors"] == []
    assert len(cli.calls) == 2


@pytest.mark.asyncio
async def test_ask_multi_repo_keeps_partial_failures(tmp_path: Path) -> None:
    orchestrator, _ = make_orchestrator(tmp_path)

    result = await orchestrator.ask_multi_repo("broken billing", repos=["broken", "billing"], max_repos=2, max_files_per_repo=2)

    assert [item["repo"] for item in result["results"]] == ["billing"]
    assert result["errors"][0]["repo"] == "broken"
    assert result["errors"][0]["exit_code"] == 2
