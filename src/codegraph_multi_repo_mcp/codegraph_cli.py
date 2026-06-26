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
