from pathlib import Path

import pytest

from codegraph_multi_repo_mcp.config import ConfigError, load_config


def test_load_config_from_explicit_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config_file = tmp_path / "repos.yaml"
    config_file.write_text(
        f"""
settings:
  codegraph_binary: /usr/local/bin/codegraph
  default_max_repos: 3
  default_max_files: 7
  per_repo_timeout_seconds: 11
  max_concurrency: 2
repos:
  - name: demo
    path: {repo}
    description: Demo repo
    tags: [python, api]
    aliases: [demo-api]
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.settings.codegraph_binary == "/usr/local/bin/codegraph"
    assert config.settings.default_max_repos == 3
    assert config.settings.default_max_files == 7
    assert config.settings.per_repo_timeout_seconds == 11
    assert config.settings.max_concurrency == 2
    assert config.repos[0].name == "demo"
    assert config.repos[0].path == repo.resolve()
    assert config.repos[0].aliases == ["demo-api"]


def test_load_config_rejects_duplicate_repo_names(tmp_path: Path) -> None:
    config_file = tmp_path / "repos.yaml"
    config_file.write_text(
        """
repos:
  - name: demo
    path: /tmp/demo-one
  - name: demo
    path: /tmp/demo-two
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Duplicate repository name"):
        load_config(config_file)


def test_load_config_rejects_missing_repos(tmp_path: Path) -> None:
    config_file = tmp_path / "repos.yaml"
    config_file.write_text("settings: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="at least one repository"):
        load_config(config_file)


def test_load_config_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(tmp_path / "missing.yaml")
