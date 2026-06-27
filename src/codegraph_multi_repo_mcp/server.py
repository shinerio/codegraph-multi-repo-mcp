from __future__ import annotations

import argparse
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .codegraph_cli import CodeGraphCLI
from .config import load_config
from .models import AppConfig
from .orchestrator import MultiRepoOrchestrator
from .repo_registry import RepoRegistry


Transport = Literal["stdio", "sse", "streamable-http"]


def build_orchestrator(config: AppConfig | None = None) -> MultiRepoOrchestrator:
    app_config = config or load_config()
    registry = RepoRegistry(app_config)
    cli = CodeGraphCLI(app_config.settings.codegraph_binary)
    return MultiRepoOrchestrator(registry, cli, app_config.settings)


def create_mcp_server(host: str = "127.0.0.1", port: int = 8000, path: str = "/mcp") -> FastMCP:
    server = FastMCP("codegraph-multi-repo", host=host, port=port, streamable_http_path=path)

    @server.tool()
    async def list_repos() -> dict[str, Any]:
        """List repositories configured for multi-repo CodeGraph exploration."""
        return await build_orchestrator().list_repos()

    @server.tool()
    async def refresh_repos(include_status: bool = False) -> dict[str, Any]:
        """Refresh repository metadata and optionally include `codegraph status` output."""
        return await build_orchestrator().refresh_repos(include_status=include_status)

    @server.tool()
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

    @server.tool()
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

    @server.tool()
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

    return server


mcp = create_mcp_server()


def parse_args(
    argv: list[str] | None = None,
    *,
    default_transport: Transport = "stdio",
    default_host: str = "127.0.0.1",
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CodeGraph multi-repo MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=default_transport,
        help=f"MCP transport to use. Defaults to {default_transport}.",
    )
    parser.add_argument("--host", default=default_host, help="HTTP bind host for sse or streamable-http.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port for sse or streamable-http.")
    parser.add_argument("--path", default="/mcp", help="HTTP endpoint path for streamable-http.")
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    default_transport: Transport = "stdio",
    default_host: str = "127.0.0.1",
) -> None:
    global mcp

    args = parse_args(argv, default_transport=default_transport, default_host=default_host)
    transport: Transport = args.transport
    mcp = create_mcp_server(host=args.host, port=args.port, path=args.path)
    try:
        mcp.run(transport=transport)
    except KeyboardInterrupt:
        pass


def http_main() -> None:
    main(default_transport="streamable-http", default_host="0.0.0.0")
