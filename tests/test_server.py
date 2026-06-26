from pathlib import Path

from codegraph_multi_repo_mcp.models import AppConfig, RepoConfig, Settings
from codegraph_multi_repo_mcp.server import build_orchestrator


def test_build_orchestrator_from_config(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = AppConfig(settings=Settings(), repos=[RepoConfig(name="repo", path=repo)])

    orchestrator = build_orchestrator(config)

    assert orchestrator.registry.get("repo").name == "repo"
