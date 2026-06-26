# CodeGraph Multi-Repo MCP Design

## Purpose

Build a standalone, cross-platform Python MCP server that lets AI agents such as Codex and Claude Code explore and analyze multiple local code repositories through the `codegraph` CLI.

The server is not tied to any business repository. It acts as a reusable orchestration layer over many repositories that already have, or can later receive, `.codegraph/` indexes.

## Goals

- Expose multi-repository CodeGraph capabilities through MCP tools.
- Depend on the local `codegraph` CLI instead of an agent-specific CodeGraph MCP server.
- Keep repository configuration outside business code repositories.
- Support Codex, Claude Code, and other MCP-compatible agents through stdio transport.
- Return structured evidence that the calling agent can use to produce final answers.
- Handle partial failures, timeouts, and missing indexes without failing the entire multi-repo query.

## Non-Goals

- Do not embed an LLM provider or require API keys.
- Do not build or modify CodeGraph indexes automatically unless the user explicitly invokes a refresh/index command in a later version.
- Do not replace CodeGraph's single-repository analysis. This server orchestrates CodeGraph across repositories.
- Do not implement a vector database in the first release.
- Do not require changes inside registered business repositories.

## Architecture

```text
MCP Client
  Codex / Claude Code / Cursor / other agent
        |
        v
Python MCP Server
        |
        +-- Config Loader
        +-- Repo Registry
        +-- Repo Router
        +-- CodeGraph CLI Adapter
        +-- Multi-Repo Orchestrator
        +-- Evidence Normalizer
        |
        v
Local codegraph CLI
        |
        v
Indexed local repositories
```

The MCP server receives tool calls over stdio. It loads repository metadata from YAML configuration, chooses candidate repositories for a question, invokes `codegraph` CLI commands with per-repository paths, normalizes output, and returns structured results.

## Project Layout

```text
codegraph-multi-repo-mcp/
  pyproject.toml
  README.md
  config/
    repos.example.yaml
  src/codegraph_multi_repo_mcp/
    __init__.py
    server.py
    config.py
    repo_registry.py
    router.py
    codegraph_cli.py
    orchestrator.py
    models.py
  tests/
    test_config.py
    test_router.py
    test_codegraph_cli.py
    test_orchestrator.py
```

## Configuration

The first release uses a YAML file. The default lookup order is:

1. Path from `CODEGRAPH_MULTI_REPO_CONFIG`
2. `./config/repos.yaml`
3. `~/.config/codegraph-multi-repo-mcp/repos.yaml`

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

## MCP Tools

### `list_repos`

Lists registered repositories and basic metadata. It reports whether each configured path exists and whether `.codegraph/` is present at the repository root.

Input:

```json
{}
```

Output:

```json
{
  "repos": [
    {
      "name": "eda",
      "path": "/Users/shinerio/Workspace/code/eda",
      "tags": ["eda", "java", "workflow"],
      "path_exists": true,
      "has_codegraph": true
    }
  ]
}
```

### `refresh_repos`

Checks configured repositories and optionally runs `codegraph status -p <path>` for each repository. The first release does not run `codegraph init`, `index`, or `sync`.

Input:

```json
{
  "include_status": true
}
```

### `explore_repo`

Runs CodeGraph exploration against one named repository.

Equivalent CLI shape:

```bash
codegraph explore -p <repo_path> --max-files <n> <query>
```

Input:

```json
{
  "repo": "eda",
  "query": "OrderService create order flow",
  "max_files": 8,
  "timeout_seconds": 20
}
```

### `ask_multi_repo`

Routes a question to candidate repositories and runs `codegraph explore` concurrently.

Input:

```json
{
  "question": "订单创建后如何同步到结算?",
  "repos": null,
  "max_repos": 5,
  "max_files_per_repo": 8
}
```

Behavior:

- If `repos` is provided, use those repositories directly.
- Otherwise, rank repositories using lexical matches over repo name, aliases, tags, path, and description.
- Fan out CodeGraph calls with bounded concurrency.
- Return successful results and per-repository errors separately.

### `trace_across_repos`

Searches a symbol, route, event, topic, table, or other identifier across multiple repositories. It is optimized for cross-repo seams such as API paths, DTO names, message topics, and database table names.

Input:

```json
{
  "identifier": "orders.created",
  "repos": null,
  "max_repos": 8,
  "max_files_per_repo": 6
}
```

## Routing Strategy

The first release uses deterministic lexical routing:

- Exact repo name and alias matches receive the highest score.
- Tag and description matches receive medium scores.
- Path segment matches receive medium scores.
- Query token overlap receives lower scores.
- If no repository scores above zero, use a configurable fallback number of repositories, sorted by config order.

This keeps the first version dependency-light and predictable. A later version can add BM25, embeddings, or persistent query history without changing the MCP interface.

## Result Shape

The server returns structured evidence and raw CodeGraph output. It does not try to write the final natural-language answer itself.

```json
{
  "question": "订单创建后如何同步到结算?",
  "repos_queried": ["order-service", "billing-service"],
  "results": [
    {
      "repo": "order-service",
      "path": "/path/order-service",
      "query": "订单创建后如何同步到结算?",
      "success": true,
      "stdout": "...",
      "stderr": "",
      "duration_ms": 1240,
      "route_reason": "matched tag order and description token billing"
    }
  ],
  "errors": [
    {
      "repo": "legacy-service",
      "error": "CodeGraph index not found",
      "recoverable": true
    }
  ]
}
```

## Error Handling

- Missing config: return an MCP tool error with the config lookup paths.
- Invalid repo name: return a structured validation error.
- Missing repository path: return a recoverable per-repo error.
- Missing `.codegraph/`: return a recoverable per-repo error with a hint to run `codegraph init <path>`.
- CodeGraph timeout: terminate the process and return a recoverable per-repo timeout error.
- Non-zero CodeGraph exit: return stdout, stderr, exit code, and repo metadata.
- Partial multi-repo failure: preserve successful repo results and report failed repo results separately.

## Security And Portability

- Use `asyncio.create_subprocess_exec` with argument arrays, not shell strings.
- Do not interpolate user input into shell commands.
- Resolve configured paths with `pathlib.Path.expanduser().resolve()`.
- Keep the server local-first and stdio-based.
- Avoid platform-specific shell behavior so the server works on macOS, Linux, and Windows.

## Testing

The first release should include tests for:

- YAML config loading and validation.
- Repo registry lookup and path checks.
- Router scoring for repo names, aliases, tags, descriptions, and fallback behavior.
- CodeGraph CLI command argument construction.
- CodeGraph CLI adapter behavior with mocked subprocess results.
- Orchestrator partial failure behavior.
- Timeout handling with mocked subprocess behavior.

Integration testing with real `codegraph` CLI is optional and should be skipped when the binary is unavailable.

## Installation And Usage

The package should provide a console script:

```bash
codegraph-multi-repo-mcp
```

MCP client configuration should use stdio. Example shape:

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

## Future Enhancements

- Optional `codegraph sync` tool with explicit user opt-in.
- BM25 or SQLite FTS repository routing.
- Embedding-based routing for large repository sets.
- Cached status and query results.
- Cross-repo iterative trace mode that extracts identifiers from first-round results and launches second-round searches.
- Optional companion skill for Codex and Claude Code that teaches agents when and how to use the MCP tools.
