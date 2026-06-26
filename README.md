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
