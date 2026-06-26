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
