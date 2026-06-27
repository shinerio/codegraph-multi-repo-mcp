# CodeGraph Multi-Repo MCP

一个独立的 Python MCP 服务，用于把本地多个仓库的 CodeGraph 能力暴露给支持 MCP 的 AI 编程助手，例如 Codex、Claude Code 等。

它可以在两种模式下运行：

- `stdio`：适合本机 Codex / Claude Code 直接拉起进程使用。
- `streamable-http`：适合部署到服务端，通过 HTTP endpoint 共享给团队或多个客户端使用。

## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)，用于通过 `uvx` 启动
- 本机或服务端可执行的 `codegraph` CLI，并且在 `PATH` 中
- 要查询的仓库已经完成 CodeGraph 索引

检查 CodeGraph 是否可用：

```bash
codegraph --help
```

## 快速开始

先创建默认配置目录：

```bash
mkdir -p ~/.config/codegraph-multi-repo-mcp
```

仓库配置会影响 `ask_multi_repo` 和 `trace_across_repos` 的自动路由效果，尤其是 `description`、`tags`、`aliases`。这些字段不只是展示信息，建议让 AI agent 根据仓库内容生成和维护，而不是完全手写。

首次生成配置时，可以把下面这段提示词发给本机 AI 编程助手，例如 Codex 或 Claude Code：

```text
请帮我为 codegraph-multi-repo-mcp 生成仓库配置文件。

要求：
1. 扫描我指定的本地仓库目录，确认每个仓库路径存在。
2. 优先检查每个仓库是否有 .codegraph 目录；没有索引的仓库请列出来提醒我先运行 CodeGraph 初始化。
3. 为每个仓库生成稳定、简短、唯一的 name。
4. 根据 README、包名、目录结构、主要源码、配置文件推断 description、tags、aliases。
5. description 写清楚仓库的业务职责和主要能力，方便自然语言问题路由。
6. tags 使用业务域、技术栈、系统类型、关键模块等短词。
7. aliases 使用团队可能会说出的简称、历史名称、服务名、模块名或产品名。
8. 写入 ~/.config/codegraph-multi-repo-mcp/repos.yaml；如果文件已存在，请保留已有有效配置，只更新变化的仓库并追加新仓库。
9. 生成后帮我检查 YAML 格式、重复 name、路径是否存在，并总结哪些仓库没有 CodeGraph 索引。

仓库根目录列表：
- /path/to/repo-a
- /path/to/repo-b
```

配置格式如下：

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

后续要更新已有仓库配置或添加新仓库，也建议继续让 AI agent 修改同一个文件。给它新增仓库路径，并要求它保留已有 `name` 稳定、只在职责变化时更新 `description`，把新出现的业务域、技术栈和常用叫法补进 `tags` / `aliases`。

本地 stdio 模式启动：

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

可共享的 streamable HTTP 模式启动：

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git \
  codegraph-multi-repo-mcp \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 8000 \
  --path /mcp
```

默认 HTTP endpoint：

```text
http://localhost:8000/mcp
```

也可以使用专门的 HTTP 启动命令：

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp-http
```

`codegraph-multi-repo-mcp-http` 默认监听 `0.0.0.0:8000`，并在 `/mcp` 路径提供 MCP 服务。

## MCP 客户端配置

本机使用建议选择 stdio。部署到共享服务器时，建议选择 streamable HTTP。

### Codex

本地 stdio 配置，写入 `~/.codex/config.toml`：

```toml
[mcp_servers.codegraph-multi-repo]
command = "uvx"
args = ["--from", "git+https://github.com/shinerio/codegraph-multi-repo-mcp.git", "codegraph-multi-repo-mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 120
```

如果你的仓库配置文件不在默认位置，可以显式传入：

```toml
[mcp_servers.codegraph-multi-repo.env]
CODEGRAPH_MULTI_REPO_CONFIG = "/absolute/path/to/repos.yaml"
```

远程 streamable HTTP 配置：

```toml
[mcp_servers.codegraph-multi-repo]
url = "https://your-server.example.com/mcp"
tool_timeout_sec = 120
```

### Claude Code

本地 stdio 配置：

```bash
claude mcp add --transport stdio --scope user \
  codegraph-multi-repo \
  -- uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

如果你的仓库配置文件不在默认位置：

```bash
claude mcp add --transport stdio --scope user \
  --env CODEGRAPH_MULTI_REPO_CONFIG=/absolute/path/to/repos.yaml \
  codegraph-multi-repo \
  -- uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp
```

远程 streamable HTTP 配置：

```bash
claude mcp add --transport http --scope user \
  codegraph-multi-repo \
  https://your-server.example.com/mcp
```

### 通用 MCP JSON

本地 stdio：

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

streamable HTTP：

```json
{
  "mcpServers": {
    "codegraph-multi-repo": {
      "url": "https://your-server.example.com/mcp"
    }
  }
}
```

## 服务端部署

在服务端准备环境：

1. 安装 Python 3.11+、`uv` 和 `codegraph` CLI。
2. Clone 或挂载你希望暴露给 MCP 的代码仓库。
3. 在这些仓库中建立 CodeGraph 索引。
4. 创建 `~/.config/codegraph-multi-repo-mcp/repos.yaml`，里面的仓库路径必须是服务端本地路径。
5. 启动 streamable HTTP 服务：

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git \
  codegraph-multi-repo-mcp-http
```

如果要修改监听地址、端口或路径：

```bash
uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git \
  codegraph-multi-repo-mcp \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 8000 \
  --path /mcp
```

面向团队或公网部署时，建议在前面加反向代理或网关，启用 TLS 和认证。这个服务会暴露 `repos.yaml` 中列出的仓库的 CodeGraph 查询结果；除非这些仓库本来就可以公开访问，否则不要裸奔到公网。

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

运行测试：

```bash
python -m pytest
```

## 工具列表

- `list_repos`：列出已配置仓库以及索引是否存在。
- `refresh_repos`：刷新仓库元信息，可选返回 `codegraph status` 输出。
- `explore_repo`：针对单个仓库运行 `codegraph explore`。
- `ask_multi_repo`：根据问题自动路由到候选仓库，并发运行 CodeGraph 探索。
- `trace_across_repos`：跨仓库搜索符号、API、topic、DTO、表名等标识符。

## 说明

这个 MCP 服务不会直接生成最终的自然语言回答。它返回结构化证据和原始 CodeGraph 输出，由调用它的 AI agent 继续推理和组织答案。

## License

MIT
