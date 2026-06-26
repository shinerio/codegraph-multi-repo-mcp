from pathlib import Path

from codegraph_multi_repo_mcp.models import RepoConfig
from codegraph_multi_repo_mcp.router import RepoRouter


def repo(name: str, tmp_path: Path, **kwargs: object) -> RepoConfig:
    return RepoConfig(name=name, path=tmp_path / name, **kwargs)


def test_router_prioritizes_exact_repo_name(tmp_path: Path) -> None:
    repos = [
        repo("billing", tmp_path, description="Payment settlement"),
        repo("orders", tmp_path, description="Order management"),
    ]

    result = RepoRouter(repos).route("How does orders create flow work?", max_repos=2)

    assert result[0].repo.name == "orders"
    assert result[0].score > result[1].score
    assert "name:orders" in result[0].reason


def test_router_matches_aliases_tags_and_description(tmp_path: Path) -> None:
    repos = [
        repo("billing", tmp_path, aliases=["settlement"], tags=["finance"], description="Invoice service"),
        repo("orders", tmp_path, tags=["commerce"], description="Cart checkout"),
    ]

    result = RepoRouter(repos).route("settlement finance invoice", max_repos=2)

    assert result[0].repo.name == "billing"
    assert result[0].score >= 15


def test_router_uses_config_order_fallback(tmp_path: Path) -> None:
    repos = [repo("one", tmp_path), repo("two", tmp_path), repo("three", tmp_path)]

    result = RepoRouter(repos).route("unmatched tokens", max_repos=2)

    assert [candidate.repo.name for candidate in result] == ["one", "two"]
    assert all(candidate.score == 0 for candidate in result)
