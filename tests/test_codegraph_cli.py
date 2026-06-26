import asyncio
from pathlib import Path

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
