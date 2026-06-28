from pathlib import Path

from codegraph_multi_repo_mcp.models import AppConfig, RepoConfig, Settings
from codegraph_multi_repo_mcp import server
from codegraph_multi_repo_mcp.server import build_orchestrator


def test_build_orchestrator_from_config(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = AppConfig(settings=Settings(), repos=[RepoConfig(name="repo", path=repo)])

    orchestrator = build_orchestrator(config)

    assert orchestrator.registry.get("repo").name == "repo"


async def test_tool_descriptions_guide_codegraph_triggering() -> None:
    mcp_server = server.create_mcp_server()

    tools = {tool.name: tool for tool in await mcp_server.list_tools()}

    ask_description = tools["ask_multi_repo"].description or ""
    assert "PRIMARY code-understanding tool" in ask_description
    assert "Call FIRST" in ask_description
    assert "how code works" in ask_description
    assert "before editing symbols/files" in ask_description
    assert "Do not use for non-code questions" in ask_description
    assert "groupId:artifactId" in ask_description

    trace_description = tools["trace_across_repos"].description or ""
    assert "Trace a specific code identifier" in trace_description
    assert "symbol, API route, DTO, event, topic, artifactId, groupId" in trace_description


def test_main_configures_streamable_http_transport(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []
    created: list[tuple[str, int, str]] = []

    class FakeMCP:
        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            calls.append((transport, mount_path))

    def fake_create_mcp_server(host: str, port: int, path: str) -> FakeMCP:
        created.append((host, port, path))
        return FakeMCP()

    monkeypatch.setattr(server, "create_mcp_server", fake_create_mcp_server)

    server.main(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--path",
            "/codegraph",
        ]
    )

    assert created == [("0.0.0.0", 9000, "/codegraph")]
    assert calls == [("streamable-http", None)]


def test_http_main_defaults_to_streamable_http(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []
    created: list[tuple[str, int, str]] = []

    class FakeMCP:
        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            calls.append((transport, mount_path))

    def fake_create_mcp_server(host: str, port: int, path: str) -> FakeMCP:
        created.append((host, port, path))
        return FakeMCP()

    monkeypatch.setattr(server, "create_mcp_server", fake_create_mcp_server)
    monkeypatch.setattr("sys.argv", ["codegraph-multi-repo-mcp-http"])

    server.http_main()

    assert created == [("0.0.0.0", 8000, "/mcp")]
    assert calls == [("streamable-http", None)]


def test_main_handles_keyboard_interrupt(monkeypatch) -> None:
    class FakeMCP:
        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            raise KeyboardInterrupt

    monkeypatch.setattr(server, "create_mcp_server", lambda host, port, path: FakeMCP())

    server.main([])
