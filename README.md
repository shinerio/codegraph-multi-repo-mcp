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

仓库配置会影响 `ask_multi_repo` 和 `trace_across_repos` 的自动路由效果，尤其是 `description`、`language`、`tags`、`aliases`、`components`。这些字段不只是展示信息，建议让 AI agent 根据仓库内容生成和维护，而不是完全手写。

首次生成配置时，可以把下面这段提示词发给本机 AI 编程助手，例如 Codex 或 Claude Code。使用前把 `{{REPOSITORY_SCAN_ROOTS}}` 替换为实际扫描根目录的绝对路径列表，每行一个路径；每个扫描根目录下面可以包含多个仓库。

```text
请帮我为 codegraph-multi-repo-mcp 生成仓库配置文件。

要求：
1. 把我提供的路径当作扫描根目录列表，支持多个根目录；不要假设每个根目录本身就是唯一仓库。
2. 对每个扫描根目录递归查找 `.codegraph` 目录；每个 `.codegraph` 的父目录就是一个要配置的仓库根目录。
3. 只配置带有 `.codegraph` 的仓库根目录；没有 `.codegraph` 的目录不要加入配置，也不要提醒我补配置或初始化，避免扫描和分析过多无关文件。
4. 递归扫描时跳过 node_modules、target、build、dist、.venv、venv、.idea、.gradle、.mvn、.git 等依赖、构建或工具目录。
5. 确认每个仓库根目录路径存在，并按真实路径去重。
6. 为每个仓库生成稳定、简短、唯一的 name。
7. 根据 README、包名、目录结构、主要源码、配置文件推断 description、language、tags、aliases、components；只分析已发现的 `.codegraph` 仓库根目录。
8. description 写清楚仓库的业务职责和主要能力，方便自然语言问题路由。
9. language 写主要编程语言，例如 java、python、typescript；不要把语言重复写进 tags。
10. tags 使用业务域、系统类型、关键模块等短词，不放编程语言。
11. aliases 使用团队可能会说出的简称、历史名称、服务名、模块名或产品名。
12. components 描述仓库内重要可发布组件、服务或模块，优先使用构建系统里的正式组件名。
13. 对 Java/Maven 仓库，请检查 pom.xml、父子模块、groupId、artifactId；components 中为关键模块写入 name、groupId、artifactId，方便后续按 artifactId 或完整 groupId:artifactId 路由到正确仓库。
14. 写入 ~/.config/codegraph-multi-repo-mcp/repos.yaml；如果文件已存在，请保留已有有效配置，只更新变化的仓库并追加新仓库。
15. 生成后帮我检查 YAML 格式、重复 name、路径是否存在，并总结已配置的仓库数量和名称。

扫描根目录列表：
{{REPOSITORY_SCAN_ROOTS}}
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
    language: java
    tags: [eda, workflow]
    aliases: [eda-platform]
    components:
      - name: eda-platform
        groupId: com.example.eda
        artifactId: eda-platform
```

后续要更新已有仓库配置或添加新仓库，也建议继续让 AI agent 修改同一个文件。给它新增仓库路径，并要求它保留已有 `name` 稳定、只在职责变化时更新 `description`，把主要编程语言写进 `language`，把新出现的业务域和系统模块补进 `tags`，把常用叫法补进 `aliases`，把可发布组件补进 `components`。

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

### 以常驻进程运行

上面的命令在前台运行，关闭终端或退出 SSH 后进程会结束。要让 streamable HTTP 服务长期可用，请用进程管理工具把它托管成后台常驻进程。

下面三种方式任选其一。

**方式一：nohup（最简单，临时使用）**

```bash
nohup uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git \
  codegraph-multi-repo-mcp-http \
  > ~/.config/codegraph-multi-repo-mcp/server.log 2>&1 &
```

日志写到 `server.log`，停止时用 `pkill -f codegraph-multi-repo-mcp-http`。这种方式不会随系统重启自动拉起，适合临时验证。

**方式二：macOS launchd（开机自启，推荐 macOS 用户）**

创建 `~/Library/LaunchAgents/com.codegraph.multi-repo-mcp.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.codegraph.multi-repo-mcp</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/你的用户名/.local/bin/uvx</string>
    <string>--from</string>
    <string>git+https://github.com/shinerio/codegraph-multi-repo-mcp.git</string>
    <string>codegraph-multi-repo-mcp-http</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/你的用户名/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/你的用户名/.config/codegraph-multi-repo-mcp/server.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/你的用户名/.config/codegraph-multi-repo-mcp/server.err</string>
</dict>
</plist>
```

把 `你的用户名` 换成实际用户名（`uvx` 路径用 `which uvx` 确认，`codegraph` 也要在 `PATH` 里）。加载并启动：

```bash
launchctl load ~/Library/LaunchAgents/com.codegraph.multi-repo-mcp.plist
launchctl list | grep codegraph
```

停止或卸载：

```bash
launchctl unload ~/Library/LaunchAgents/com.codegraph.multi-repo-mcp.plist
```

**方式三：Linux systemd（开机自启，推荐服务器部署）**

创建 `~/.config/systemd/user/codegraph-multi-repo-mcp.service`：

```ini
[Unit]
Description=CodeGraph Multi-Repo MCP (streamable HTTP)
After=network.target

[Service]
ExecStart=%h/.local/bin/uvx --from git+https://github.com/shinerio/codegraph-multi-repo-mcp.git codegraph-multi-repo-mcp-http
Restart=always
RestartSec=3
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
```

启用并启动：

```bash
systemctl --user daemon-reload
systemctl --user enable --now codegraph-multi-repo-mcp.service
systemctl --user status codegraph-multi-repo-mcp.service
```

查看日志用 `journalctl --user -u codegraph-multi-repo-mcp.service -f`。要让用户级服务在未登录时也运行，执行 `loginctl enable-linger $USER`。

### 在客户端完成配置

服务常驻起来之后，把它的 HTTP endpoint 注册到客户端即可。以 Claude Code 为例：

```bash
claude mcp add --transport http --scope user \
  codegraph-multi-repo \
  http://localhost:8000/mcp
```

部署在远程服务器时，把 URL 换成实际地址，例如 `https://your-server.example.com/mcp`。注册后用 `claude mcp list` 验证，看到 `✔ Connected` 即表示连接成功。其他客户端的配置写法见上文「MCP 客户端配置」。

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
