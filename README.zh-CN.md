# skill-hub-manager

[English Version](README.md)

一个面向多 Agent、多项目工作流的私有 skills 管理器。

这个仓库刻意保持公开，但**不会**包含你真实的私有 skills。
真实 skill 内容存放在仓库外部的本地 vault 中，这个项目只负责：

- skills 发现
- registry 生成
- 基于 profile 的访问控制
- 基于 symlink 的同步
- 审计与文档

## 前置条件

安装前请确认你具备以下条件：

| 条件 | 验证 | 说明 |
|---|---|---|
| **Python 3.11+** | `python3 --version` | CLI 和安装脚本必需 |
| **Git** | `git --version` | 克隆管理器和远程 skill 必需 |
| **macOS 或 Linux** | — | Windows 尚未测试（symlink 需要特殊配置） |
| **pip + setuptools**（可选） | `python3 -m pip --version` | 仅在需要把 `skill-hub` 放到 PATH 时需要 |

## 平台支持

- **macOS**：完全测试，推荐使用。
- **Linux**：开箱即用。依赖标准 Python 3.11+ 和 POSIX symlink。
- **Windows**：尚未测试。创建 symlink 需要管理员权限或开发者模式。如果你尝试了，请反馈结果。

## 为什么要用

1. **只保留一份** — 真实 skills 始终只存一份，不再为多个 agent、多个项目复制副本。
2. **按 agent 分配权限** — 只给 Codex 一部分 skill，只给 Claude Code 另一部分，通过 profile 控制。
3. **本地 + 远程** — 从本地目录或远程 Git 仓库导入 skill。
4. **Agent 驱动** — 全程通过和 AI 对话完成，不需要长期手敲终端命令。

## 工作原理

真实 skill 内容存放在一个私有 vault 中。Profile 决定每个 agent 能看到哪些 skill。Sync 通过 symlink 把允许的子集映射到各 agent 的目标目录 — 不做任何复制。

<details>
<summary>架构示意图</summary>

```text
                  一份真实私有 skill 仓库
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/skills/                              │
│   demo-skill/                                     │
│   k8s-finder/                                     │
│   billing-labeler/                                │
└────────────────────────────────────────────────────┘
                         │
                         │ scan / registry build
                         ▼
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/state/registry.yaml                  │
│   已发现的 skill 索引和元数据                     │
└────────────────────────────────────────────────────┘
                         │
                         │ profile 规则决定暴露范围
                         ▼
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/profiles/                            │
│   codex.yaml      -> demo-skill, k8s-finder       │
│   claude.yaml     -> billing-labeler              │
│   project-a.yaml  -> demo-skill                   │
└────────────────────────────────────────────────────┘
             │                    │                    │
             │ sync               │ sync               │ sync
             ▼                    ▼                    ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ ~/.codex/skills/    │ │ ~/.claude/skills/   │ │ ~/project-a/.skills/│
│ demo-skill -> ...   │ │ billing-labeler->...│ │ demo-skill -> ...   │
│ k8s-finder -> ...   │ │                     │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
             │                    │                    │
             ▼                    ▼                    ▼
            Codex               Claude             项目 Agent
```

</details>

## 快速使用（Agent 驱动）

默认设计理念是：**你直接和 AI 沟通，AI 来操作这个管理器。**

从零到同步一个 skill，一共四步。以下路径均假设 checkout 在 `~/skill-hub-manager`。

### 第一步：安装 manager

把这段话发给你的 agent（Codex、Claude Code 等）：

```text
帮我安装这个 skills 管理器，并完成初始化：
https://github.com/cnyup/skill-hub-manager.git

要求：
- checkout 放在 ~/skill-hub-manager
- workspace 放在 ~/.skill-hub
- 任何 clone 或初始化之前先确认
```

agent clone（或复用）checkout 并初始化 workspace。

验证：

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

也可以不走 agent，直接运行 CLI。两种方式：

```bash
# 从 checkout 运行（不需要打包工具）
~/skill-hub-manager/bin/skill-hub --version

# 或者安装到 PATH
python3 -m pip install -e .
skill-hub --version
```

完整安装说明：[docs/installation.zh-CN.md](docs/installation.zh-CN.md)。

### 第二步：把 `skill-installer` 软链到 agent 目录

**为什么需要这步**：agent 需要在它的 skills 目录里看到 `skill-installer` 这个 skill，才能在第三步帮你安装业务 skill。没有它，agent 没有安装能力。

```text
把 ~/skill-hub-manager/skills/skill-installer/ 软链到我的 agent skills 目录（~/.codex/skills/ 或 ~/.claude/skills/）。
```

默认目标：
- **Codex**：`~/.codex/skills/`
- **Claude Code**：`~/.claude/skills/`
- **Cursor**：`~/.cursor/skills/`
- **Windsurf**：`~/.codeium/windsurf/skills/`

### 第三步：安装业务 skill

现在 agent 可以从本地路径或远程仓库导入 skill 了：

```text
帮我把这个 skill 安装到我的 skill-hub workspace：
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

agent 负责解析来源、导入到 `~/.skill-hub/skills/`、重建 registry，并在 profile 更新或 sync 之前征求确认。

如果远程来源使用了非默认分支、tag、commit，或者 skill 不在标准路径下，优先显式给出 git ref 和 source subpath。分支名带 `/` 时尤为重要。

### 第四步：通过 profile + sync 暴露 skill

告诉 agent 更新哪个 profile、同步到哪个目标目录：

```text
把 web-access 加入 claude-code profile 并同步到 ~/.claude/skills/
```

你只需要告诉 agent：skill 来源在哪、想给哪个 agent 用、是否要先展示计划。

### CLI 兜底路径

如果不走 agent，直接用 CLI：

```bash
~/skill-hub-manager/bin/skill-hub init --root ~/.skill-hub
~/skill-hub-manager/bin/skill-hub skill import --root ~/.skill-hub --source /path/to/local-skill
~/skill-hub-manager/bin/skill-hub registry build --root ~/.skill-hub
~/skill-hub-manager/bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

如果 skill 来源是远程仓库 URL，先让 `skills/skill-installer/scripts/install_skill.py` 完成解析和缓存，再导入本地目录。

## 进阶用法

### 同一个 skill 给多个 agent 使用

```text
我的 vault 里有 web-access。把它同时加入 codex 和 claude-code 两个 profile，
然后分别同步到各自的 agent 目录。
同步之前先展示计划。
```

### 批量导入本地已有 skills

```text
扫描 ~/my-skills/ 下的 skill 目录。先列出你找到了什么，
然后把它们全部导入 ~/.skill-hub/skills/ 并加入 codex profile。
导入前先确认。
```

### 从远程源更新已有 skill

```text
从缓存的远程源更新 web-access。更新完成后重新同步 claude-code profile。
```

Profile 文档：[docs/profiles.md](docs/profiles.md)。完整 CLI 参考：[docs/quick-start.md](docs/quick-start.md)。

## 仓库自带 Skills

- **`skill-installer`** — 从本地路径、Git 仓库或 GitHub tree URL 导入业务 skill。这是主要的安装 skill（在上方第二步暴露）。
- **`self-installer`** *（已废弃）* — 保留用于兼容。manager 安装请直接把 GitHub 地址给 agent（见快速使用第一步）。

## CLI 参考

| 分组 | 命令 |
|---|---|
| **Skill** | `import`、`remove`、`update`、`source list/show` |
| **Registry** | `build`、`doctor` |
| **Profile** | `list/show/add/update/clone/rename/validate/remove` |
| **Sync** | `sync --dry-run`、`doctor` |
| **查询** | `scan`、`ls`、`find`、`audit` |
| **Agent** | `agent detect`、`install-state show/record` |

大部分命令支持 `--json` 输出。完整示例：[docs/quick-start.md](docs/quick-start.md)。JSON schema：[docs/schema/json-output.md](docs/schema/json-output.md)。

## 状态

**当前**：本地优先 CLI MVP，支持完整 skill 生命周期（import/remove/update）、profile 管理、sync 和审计。

**路线图**：
- [x] 核心 CLI（init、import、registry、profiles、sync、doctor）
- [x] Agent 驱动安装流程（skill-installer + self-installer）
- [x] 远程 skill 缓存和来源元数据跟踪
- [ ] Windows symlink 支持测试
- [ ] 交互式 profile 管理 TUI
- [ ] Vault 浏览 Web UI

## 贡献

欢迎提交 PR。Fork → 分支 → 运行 `PYTHONPATH=src python3 -m unittest discover -s tests` → 提交。

## 许可证

[Apache License 2.0](LICENSE)
