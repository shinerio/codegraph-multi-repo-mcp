# CodeGraph Multi-Repo MCP

Standalone Python MCP server that exposes multi-repository CodeGraph exploration to MCP-compatible AI agents.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for `uvx` installation
- Local `codegraph` CLI available on `PATH`
- Local repositories indexed with CodeGraph

Check CodeGraph:

```bash
codegraph --help
```

## Quick Start

Create a repository config in the default location:

```bash
mkdir -p ~/.config/codegraph-multi-repo-mcp
$EDITOR ~/.config/codegraph-multi-repo-mcp/repos.yaml
```

Add repositories that already have a local CodeGraph index:

```yaml
settings:
  codegraph_binary: codegraph
  default_max_repos: 5
  default_max_files: 8
  per_repo_timeout_seconds: 20
  max_concurrency: 4

repos:
  - name: eda
    path: /path/to/eda
    description: EDA application repository
    tags: [eda, java, workflow]
    aliases: [eda-platform]
```

Run the MCP server with `uvx`:

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

## MCP Client Configuration

### Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.codegraph-multi-repo]
command = "uvx"
args = ["--from", "git+https://github.com/shinerio/codegraph-multi-repo-mcp.git", "codegraph-multi-repo-mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 120
```

If your repository config is not in the default location, pass it explicitly:

```toml
[mcp_servers.codegraph-multi-repo.env]
CODEGRAPH_MULTI_REPO_CONFIG = "/absolute/path/to/repos.yaml"
```

### Claude Code

```bash
claude mcp add --transport stdio --scope user \
  codegraph-multi-repo \
  -- uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

If your repository config is not in the default location:

```bash
claude mcp add --transport stdio --scope user \
  --env CODEGRAPH_MULTI_REPO_CONFIG=/absolute/path/to/repos.yaml \
  codegraph-multi-repo \
  -- uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

### Generic MCP JSON

```json
{
  "mcpServers": {
    "codegraph-multi-repo": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/shinerio/codegraph-multi-repo-mcp.git",
        "codegraph-multi-repo-mcp"
      ]
    }
  }
}
```

## Development

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

## Tools

- `list_repos`: list configured repositories and index presence.
- `refresh_repos`: inspect configured repositories and optionally include `codegraph status`.
- `explore_repo`: run `codegraph explore` against one repository.
- `ask_multi_repo`: route a question to candidate repositories and explore them concurrently.
- `trace_across_repos`: search an identifier across repositories.

## Notes

This MCP server does not generate the final natural-language answer. It returns structured evidence and raw CodeGraph output so the calling agent can reason over it.

## License

MIT
