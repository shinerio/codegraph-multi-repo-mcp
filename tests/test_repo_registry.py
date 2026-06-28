from pathlib import Path

import pytest

from codegraph_multi_repo_mcp.models import AppConfig, RepoConfig, Settings
from codegraph_multi_repo_mcp.repo_registry import RepoRegistry


def make_registry(tmp_path: Path) -> RepoRegistry:
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / ".codegraph").mkdir()
    config = AppConfig(
        settings=Settings(),
        repos=[
            RepoConfig(
                name="demo",
                path=repo,
                description="Demo service",
                tags=["python"],
                aliases=["demo-api"],
                language="python",
                components=[{"group_id": "com.example", "artifact_id": "demo-api"}],
            )
        ],
    )
    return RepoRegistry(config)


def test_list_repos_reports_path_and_index(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.list_repos()

    assert result[0]["name"] == "demo"
    assert result[0]["path_exists"] is True
    assert result[0]["has_codegraph"] is True
    assert result[0]["aliases"] == ["demo-api"]
    assert result[0]["language"] == "python"
    assert result[0]["components"] == [{"name": "", "group_id": "com.example", "artifact_id": "demo-api"}]


def test_get_matches_name_and_alias(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    assert registry.get("demo").name == "demo"
    assert registry.get("demo-api").name == "demo"


def test_get_unknown_repo_raises_key_error(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    with pytest.raises(KeyError, match="Unknown repository"):
        registry.get("missing")
