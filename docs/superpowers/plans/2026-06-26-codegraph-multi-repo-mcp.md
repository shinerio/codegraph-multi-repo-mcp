# CodeGraph Multi-Repo MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python stdio MCP server that orchestrates the local `codegraph` CLI across multiple configured repositories.

**Architecture:** The server loads repository metadata from YAML, validates and routes queries to candidate repositories, invokes `codegraph` CLI with safe subprocess argument arrays, and returns structured MCP tool results. The implementation is split into focused modules for models, config, registry, routing, CLI calls, orchestration, and MCP exposure.

**Tech Stack:** Python 3.11+, `mcp` Python SDK, `pydantic`, `PyYAML`, `pytest`, `pytest-asyncio`, local `codegraph` CLI.

---

## File Map

- `pyproject.toml`: package metadata, dependencies, console script, pytest configuration.
- `README.md`: installation, configuration, MCP client setup, and usage examples.
- `config/repos.example.yaml`: sample multi-repo configuration.
- `src/codegraph_multi_repo_mcp/__init__.py`: package version.
- `src/codegraph_multi_repo_mcp/models.py`: shared Pydantic models.
- `src/codegraph_multi_repo_mcp/config.py`: configuration lookup, YAML parsing, validation.
- `src/codegraph_multi_repo_mcp/repo_registry.py`: repository lookup and status helpers.
- `src/codegraph_multi_repo_mcp/router.py`: deterministic lexical repo routing.
- `src/codegraph_multi_repo_mcp/codegraph_cli.py`: async CLI adapter around `codegraph`.
- `src/codegraph_multi_repo_mcp/orchestrator.py`: multi-repo fanout and trace behavior.
- `src/codegraph_multi_repo_mcp/server.py`: MCP tool definitions and stdio entrypoint.
- `tests/test_config.py`: config loading tests.
- `tests/test_repo_registry.py`: registry tests.
- `tests/test_router.py`: routing tests.
- `tests/test_codegraph_cli.py`: subprocess adapter tests.
- `tests/test_orchestrator.py`: multi-repo orchestration tests.
- `tests/test_server.py`: MCP tool smoke tests against directly-called tool functions.

---

## Task 1: Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/codegraph_multi_repo_mcp/__init__.py`
- Create: `README.md`
- Create: `config/repos.example.yaml`

- [ ] **Step 1: Create package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "codegraph-multi-repo-mcp"
version = "0.1.0"
description = "Multi-repository CodeGraph orchestrator exposed as an MCP server"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.0.0",
  "pydantic>=2.7.0",
  "PyYAML>=6.0.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
]

[project.scripts]
codegraph-multi-repo-mcp = "codegraph_multi_repo_mcp.server:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Add package version**

Create `src/codegraph_multi_repo_mcp/__init__.py`:

```python
"""CodeGraph multi-repo MCP server."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Add example repository config**

Create `config/repos.example.yaml`:

```yaml
settings:
  codegraph_binary: codegraph
  default_max_repos: 5
  default_max_files: 8
  per_repo_timeout_seconds: 20
  max_concurrency: 4

repos:
  - name: eda
    path: /Users/shinerio/Workspace/code/eda
    description: EDA application repository
    tags: [eda, java, workflow]
    aliases: [eda-platform]
```

- [ ] **Step 4: Add initial README**

Create `README.md`:

```markdown
# CodeGraph Multi-Repo MCP

Standalone Python MCP server that orchestrates the local `codegraph` CLI across multiple repositories.

## Requirements

- Python 3.11+
- Local `codegraph` CLI on `PATH`
- Repositories indexed with CodeGraph (`.codegraph/` at repo root)

## Configuration

Copy `config/repos.example.yaml` to `config/repos.yaml` or set `CODEGRAPH_MULTI_REPO_CONFIG`.

## Run

```bash
codegraph-multi-repo-mcp
```
```

- [ ] **Step 5: Run skeleton checks**

Run:

```bash
python -m compileall src
```

Expected: compile succeeds.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md config/repos.example.yaml src/codegraph_multi_repo_mcp/__init__.py
git commit -m "chore: add Python package skeleton"
```

---

## Task 2: Shared Models And Config Loader

**Files:**
- Create: `src/codegraph_multi_repo_mcp/models.py`
- Create: `src/codegraph_multi_repo_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run config tests to verify failure**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: FAIL because `config.py` and `models.py` do not exist.

- [ ] **Step 3: Implement models**

Create `src/codegraph_multi_repo_mcp/models.py`:

```python
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
```

- [ ] **Step 4: Implement config loader**

Create `src/codegraph_multi_repo_mcp/config.py`:

```python
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
```

- [ ] **Step 5: Run config tests**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/codegraph_multi_repo_mcp/models.py src/codegraph_multi_repo_mcp/config.py tests/test_config.py
git commit -m "feat: load repository configuration"
```

---

## Task 3: Repo Registry

**Files:**
- Create: `src/codegraph_multi_repo_mcp/repo_registry.py`
- Test: `tests/test_repo_registry.py`

- [ ] **Step 1: Write registry tests**

Create `tests/test_repo_registry.py`:

```python
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


def test_get_matches_name_and_alias(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    assert registry.get("demo").name == "demo"
    assert registry.get("demo-api").name == "demo"


def test_get_unknown_repo_raises_key_error(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    with pytest.raises(KeyError, match="Unknown repository"):
        registry.get("missing")
```

- [ ] **Step 2: Run registry tests to verify failure**

Run:

```bash
pytest tests/test_repo_registry.py -v
```

Expected: FAIL because `repo_registry.py` does not exist.

- [ ] **Step 3: Implement registry**

Create `src/codegraph_multi_repo_mcp/repo_registry.py`:

```python
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
```

- [ ] **Step 4: Run registry tests**

Run:

```bash
pytest tests/test_repo_registry.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codegraph_multi_repo_mcp/repo_registry.py tests/test_repo_registry.py
git commit -m "feat: add repository registry"
```

---

## Task 4: Lexical Router

**Files:**
- Create: `src/codegraph_multi_repo_mcp/router.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: Write router tests**

Create `tests/test_router.py`:

```python
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
```

- [ ] **Step 2: Run router tests to verify failure**

Run:

```bash
pytest tests/test_router.py -v
```

Expected: FAIL because `router.py` does not exist.

- [ ] **Step 3: Implement router**

Create `src/codegraph_multi_repo_mcp/router.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import RepoConfig


TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/-]+")


@dataclass(frozen=True)
class RepoCandidate:
    repo: RepoConfig
    score: int
    reason: str


def tokenize(value: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(value)}


class RepoRouter:
    def __init__(self, repos: list[RepoConfig]) -> None:
        self.repos = repos

    def route(self, query: str, max_repos: int) -> list[RepoCandidate]:
        query_lower = query.lower()
        query_tokens = tokenize(query)
        candidates = [self._score(repo, query_lower, query_tokens) for repo in self.repos]
        candidates.sort(key=lambda item: (-item.score, self.repos.index(item.repo)))
        return candidates[:max_repos]

    def _score(self, repo: RepoConfig, query_lower: str, query_tokens: set[str]) -> RepoCandidate:
        score = 0
        reasons: list[str] = []

        if repo.name.lower() in query_lower:
            score += 100
            reasons.append(f"name:{repo.name}")

        for alias in repo.aliases:
            if alias.lower() in query_lower:
                score += 80
                reasons.append(f"alias:{alias}")

        for tag in repo.tags:
            if tag.lower() in query_tokens:
                score += 25
                reasons.append(f"tag:{tag}")

        description_tokens = tokenize(repo.description)
        desc_matches = sorted(query_tokens & description_tokens)
        if desc_matches:
            score += 10 * len(desc_matches)
            reasons.append("description:" + ",".join(desc_matches))

        path_tokens = tokenize(str(repo.path))
        path_matches = sorted(query_tokens & path_tokens)
        if path_matches:
            score += 5 * len(path_matches)
            reasons.append("path:" + ",".join(path_matches))

        reason = "; ".join(reasons) if reasons else "fallback:config-order"
        return RepoCandidate(repo=repo, score=score, reason=reason)
```

- [ ] **Step 4: Run router tests**

Run:

```bash
pytest tests/test_router.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codegraph_multi_repo_mcp/router.py tests/test_router.py
git commit -m "feat: route questions to repositories"
```

---

## Task 5: CodeGraph CLI Adapter

**Files:**
- Create: `src/codegraph_multi_repo_mcp/codegraph_cli.py`
- Test: `tests/test_codegraph_cli.py`

- [ ] **Step 1: Write CLI adapter tests**

Create `tests/test_codegraph_cli.py`:

```python
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from codegraph_multi_repo_mcp.codegraph_cli import CodeGraphCLI, CodeGraphTimeout


class FakeProcess:
    def __init__(self, stdout: bytes, stderr: bytes, returncode: int) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


@pytest.mark.asyncio
async def test_explore_builds_safe_argument_array(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_exec(*args: str, **kwargs: object) -> FakeProcess:
        calls.append(args)
        return FakeProcess(b"source output", b"", 0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    result = await CodeGraphCLI("codegraph").explore(tmp_path, "hello world", max_files=3, timeout_seconds=5)

    assert calls == [("codegraph", "explore", "-p", str(tmp_path), "--max-files", "3", "hello world")]
    assert result.success is True
    assert result.stdout == "source output"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_status_builds_safe_argument_array(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_exec(*args: str, **kwargs: object) -> FakeProcess:
        calls.append(args)
        return FakeProcess(b"status output", b"", 0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    result = await CodeGraphCLI("cg").status(tmp_path, timeout_seconds=5)

    assert calls == [("cg", "status", str(tmp_path))]
    assert result.stdout == "status output"


@pytest.mark.asyncio
async def test_timeout_kills_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    process = FakeProcess(b"", b"", 0)

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return b"", b""

    process.communicate = slow_communicate  # type: ignore[method-assign]

    async def fake_exec(*args: str, **kwargs: object) -> FakeProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    with pytest.raises(CodeGraphTimeout):
        await CodeGraphCLI("codegraph").explore(tmp_path, "query", max_files=1, timeout_seconds=0.01)

    assert process.killed is True
```

- [ ] **Step 2: Run CLI tests to verify failure**

Run:

```bash
pytest tests/test_codegraph_cli.py -v
```

Expected: FAIL because `codegraph_cli.py` does not exist.

- [ ] **Step 3: Implement CLI adapter**

Create `src/codegraph_multi_repo_mcp/codegraph_cli.py`:

```python
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path


class CodeGraphTimeout(RuntimeError):
    """Raised when a codegraph subprocess exceeds its timeout."""


@dataclass(frozen=True)
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class CodeGraphCLI:
    def __init__(self, binary: str) -> None:
        self.binary = binary

    async def explore(
        self,
        repo_path: Path,
        query: str,
        *,
        max_files: int,
        timeout_seconds: float,
    ) -> CommandResult:
        return await self._run(
            [self.binary, "explore", "-p", str(repo_path), "--max-files", str(max_files), query],
            timeout_seconds=timeout_seconds,
        )

    async def status(self, repo_path: Path, *, timeout_seconds: float) -> CommandResult:
        return await self._run([self.binary, "status", str(repo_path)], timeout_seconds=timeout_seconds)

    async def _run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise CodeGraphTimeout(f"Command timed out after {timeout_seconds} seconds: {args}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return CommandResult(
            success=process.returncode == 0,
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode,
            duration_ms=duration_ms,
        )
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
pytest tests/test_codegraph_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codegraph_multi_repo_mcp/codegraph_cli.py tests/test_codegraph_cli.py
git commit -m "feat: wrap codegraph CLI"
```

---

## Task 6: Multi-Repo Orchestrator

**Files:**
- Create: `src/codegraph_multi_repo_mcp/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write orchestrator tests**

Create `tests/test_orchestrator.py`:

```python
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
```

- [ ] **Step 2: Run orchestrator tests to verify failure**

Run:

```bash
pytest tests/test_orchestrator.py -v
```

Expected: FAIL because `orchestrator.py` does not exist.

- [ ] **Step 3: Implement orchestrator**

Create `src/codegraph_multi_repo_mcp/orchestrator.py`:

```python
from __future__ import annotations

import asyncio
from typing import Protocol

from .codegraph_cli import CodeGraphTimeout, CommandResult
from .models import RepoConfig, Settings
from .repo_registry import RepoRegistry
from .router import RepoCandidate, RepoRouter


class CodeGraphClient(Protocol):
    async def explore(self, repo_path, query: str, *, max_files: int, timeout_seconds: float) -> CommandResult: ...
    async def status(self, repo_path, *, timeout_seconds: float) -> CommandResult: ...


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
```

- [ ] **Step 4: Run orchestrator tests**

Run:

```bash
pytest tests/test_orchestrator.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codegraph_multi_repo_mcp/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrate multi-repo exploration"
```

---

## Task 7: MCP Server

**Files:**
- Create: `src/codegraph_multi_repo_mcp/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write server smoke tests**

Create `tests/test_server.py`:

```python
from pathlib import Path

import pytest

from codegraph_multi_repo_mcp.models import AppConfig, RepoConfig, Settings
from codegraph_multi_repo_mcp.server import build_orchestrator


def test_build_orchestrator_from_config(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = AppConfig(settings=Settings(), repos=[RepoConfig(name="repo", path=repo)])

    orchestrator = build_orchestrator(config)

    assert orchestrator.registry.get("repo").name == "repo"
```

- [ ] **Step 2: Run server tests to verify failure**

Run:

```bash
pytest tests/test_server.py -v
```

Expected: FAIL because `server.py` does not exist.

- [ ] **Step 3: Implement MCP server**

Create `src/codegraph_multi_repo_mcp/server.py`:

```python
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
```

- [ ] **Step 4: Run server tests**

Run:

```bash
pytest tests/test_server.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codegraph_multi_repo_mcp/server.py tests/test_server.py
git commit -m "feat: expose MCP server tools"
```

---

## Task 8: Documentation And Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with full usage documentation**

Replace `README.md` with:

```markdown
# CodeGraph Multi-Repo MCP

Standalone Python MCP server that exposes multi-repository CodeGraph exploration to MCP-compatible AI agents.

## Requirements

- Python 3.11+
- Local `codegraph` CLI available on `PATH`
- Local repositories indexed with CodeGraph

Check CodeGraph:

```bash
codegraph --help
```

## Install For Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Configure Repositories

Copy the example config:

```bash
cp config/repos.example.yaml config/repos.yaml
```

Or set:

```bash
export CODEGRAPH_MULTI_REPO_CONFIG=/absolute/path/to/repos.yaml
```

Example:

```yaml
settings:
  codegraph_binary: codegraph
  default_max_repos: 5
  default_max_files: 8
  per_repo_timeout_seconds: 20
  max_concurrency: 4

repos:
  - name: eda
    path: /Users/shinerio/Workspace/code/eda
    description: EDA application repository
    tags: [eda, java, workflow]
    aliases: [eda-platform]
```

## MCP Client Configuration

Use stdio transport:

```json
{
  "mcpServers": {
    "codegraph-multi-repo": {
      "command": "codegraph-multi-repo-mcp",
      "env": {
        "CODEGRAPH_MULTI_REPO_CONFIG": "/absolute/path/to/repos.yaml"
      }
    }
  }
}
```

If the console script is not on the client's `PATH`, use the venv executable path:

```json
{
  "mcpServers": {
    "codegraph-multi-repo": {
      "command": "/absolute/path/to/codegraph-multi-repo-mcp/.venv/bin/codegraph-multi-repo-mcp",
      "env": {
        "CODEGRAPH_MULTI_REPO_CONFIG": "/absolute/path/to/repos.yaml"
      }
    }
  }
}
```

## Tools

- `list_repos`: list configured repositories and index presence.
- `refresh_repos`: inspect configured repositories and optionally include `codegraph status`.
- `explore_repo`: run `codegraph explore` against one repository.
- `ask_multi_repo`: route a question to candidate repositories and explore them concurrently.
- `trace_across_repos`: search an identifier across repositories.

## Notes

This MCP server does not generate the final natural-language answer. It returns structured evidence and raw CodeGraph output so the calling agent can reason over it.
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 3: Run compile check**

Run:

```bash
python -m compileall src tests
```

Expected: compile succeeds.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: only README changes before the final commit.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document MCP server usage"
```

---

## Self-Review

- Spec coverage: The plan covers package setup, YAML config, repository registry, deterministic routing, safe CLI subprocess calls, multi-repo fanout, partial failures, MCP tools, and documentation.
- Non-goals preserved: No LLM provider, no automatic CodeGraph indexing, no vector database, and no required changes inside registered repositories.
- Error handling coverage: Missing config, missing repo path, missing `.codegraph`, non-zero CLI exit, and timeout are implemented in config, CLI adapter, and orchestrator tasks.
- Type consistency: `Settings`, `RepoConfig`, `AppConfig`, `RepoRegistry`, `RepoRouter`, `CodeGraphCLI`, and `MultiRepoOrchestrator` names are consistent across tasks.
