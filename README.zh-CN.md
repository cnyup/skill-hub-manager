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

## 核心思路

- 公共 GitHub 仓库：代码、文档、模板、测试
- 私有本地 vault：真实 `SKILL.md` 和敏感资产
- Profiles：按 agent 或项目定义 allowlist
- Sync 引擎：把允许的 skills 落到各 agent 的目标目录

## 工作示意图

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

最关键的一点是：真实的 skill 内容始终只保留一份。`sync` 做的只是把“允许给谁使用的那一部分”映射到对应 agent 的目标目录。

## 内容边界

- GitHub：manager 代码、示例、schema、文档、测试
- 本地 vault：真实 skills 和私有资产
- Profiles：可根据需要选择公开或私有

## 安装方式

目前支持两种运行方式：

1. 直接从代码仓库运行，不依赖 Python 打包安装：

```bash
./bin/skill-hub --version
./bin/skill-hub --help
```

2. 在正常 Python 工作站中安装为命令：

```bash
python3 -m pip install -e .
skill-hub --version
```

当前仓库环境里，默认推荐直接使用 checkout wrapper，因为这条路径已经验证可用。

完整安装说明见 [installation.zh-CN.md](docs/installation.zh-CN.md)。

## 仓库自带 Skills

当前仓库自带 2 个公开 skill：

1. `self-installer`
   负责把 `skill-hub-manager` 自身从 Git 仓库安装或更新到当前机器。这是唯一的公开 bootstrap 入口。
2. `skill-installer`
   负责把普通业务 skill 导入到已经存在的 skill-hub-manager workspace，并可选更新 profile 与执行 sync。

这些 skill 都是公开的，不包含任何私有 vault 内容。

## 快速使用

大多数用户实际只需要下面 3 个入口：

1. 让一个已经能读取 `self-installer` 的 agent 安装 manager 本身：

```text
帮我安装这个 skills 管理器：
https://github.com/cnyup/skill-hub-manager.git
```

2. 让一个已经能读取 `skill-installer` 的 agent 安装业务 skill：

```text
帮我把这个 skill 安装到我的 skill-hub workspace：
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

3. 如果你不走 agent，直接用 CLI：

```bash
./bin/skill-hub init --root ~/.skill-hub
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/local-skill
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

如果 skill 来源是远程仓库 URL，先让 `skills/skill-installer/scripts/install_skill.py` 完成解析和缓存，再对解析出的本地目录调用 `skill-hub skill import`。

## 第二条线：安装业务 Skills

manager 装好以后，第二条线使用 `skill-installer`：

```text
帮我把这个 skill 安装到我的 skill-hub workspace：
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

`skill-installer` 应该执行：

1. 解析本地路径、Git 仓库 URL 或 GitHub tree URL
2. 将远程仓库缓存到 `~/.skill-hub/sources/`
3. 把选中的 skill 导入到 `~/.skill-hub/skills/`
4. 重建 registry
5. 可选把 skill 加入某个 profile
6. 可选把更新后的 profile sync 到目标目录

如果远程来源使用了非默认分支、tag、commit，或者 skill 不在标准路径下，优先显式给出 git ref 和 source subpath。
这一点对 GitHub tree URL 尤其重要，分支名如果带 `/`，例如 `feature/demo`，不要依赖自动猜测。

## 现在该如何安装这个管理器

推荐的 agent 驱动流程：

1. 先把 `skills/self-installer/` 暴露到一个 agent 已经能读取的 skills 目录。
2. 然后直接对 agent 说：

```text
帮我安装这个 skills 管理器：
https://github.com/cnyup/skill-hub-manager.git
```

3. `self-installer` 应该执行：
   - 检测或推断 checkout 路径、workspace 根目录
   - 先展示完整计划
   - 在任何 clone、update、workspace 初始化之前先向用户确认
   - 安装 manager
4. 安装完成后，用下面命令验证：

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

如果你当前还没有一个 agent 可读取的 skills 目录，那么先走 [installation.zh-CN.md](docs/installation.zh-CN.md) 里的手动 CLI 安装路径，之后再暴露 `self-installer`。

## 当前 CLI 能力

当前版本提供：

- `skill-hub --version`
- `skill-hub init --root <path>`
- `skill-hub skill import --root <path> --source <path> [--name <skill>] [--force] [--json]`
- `skill-hub skill source list --root <path> [--json]`
- `skill-hub skill source show --root <path> --name <skill> [--json]`
- `skill-hub registry build --root <path>`
- `skill-hub registry doctor --root <path> [--json] [--rebuild-if-drift]`
- `skill-hub scan --root <path>`
- `skill-hub ls --root <path> [--json]`
- `skill-hub find --root <path> --query <text> [--json]`
- `skill-hub audit --root <path> [--json]`
- `skill-hub profile list --root <path>`
- `skill-hub profile show --root <path> --name <profile>`
- `skill-hub profile add --root <path> --name <profile> --agent <agent> --skill <skill>`
- `skill-hub profile update --root <path> --name <profile>`
- `skill-hub profile clone --root <path> --name <profile> --to <profile>`
- `skill-hub profile rename --root <path> --name <profile> --to <profile>`
- `skill-hub profile validate --root <path> [--name <profile>]`
- `skill-hub profile remove --root <path> --name <profile>`
- `skill-hub sync --root <path> --target <path> [--dry-run] [--json]`
- `skill-hub doctor --root <path>`

## 从本地 checkout 直接运行

```bash
./bin/skill-hub init --root /Users/yup/.skill-hub
```

等价的源码运行方式：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli init --root /Users/yup/.skill-hub
```

将本地 skill 导入 workspace：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli skill import \
  --root /Users/yup/.skill-hub \
  --source /Users/yup/skills/web-access
```

对一个已经在本地解析并缓存好的远程 skill 记录来源元数据：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli skill import \
  --root /Users/yup/.skill-hub \
  --source /Users/yup/.skill-hub/sources/example-repo/skills/web-access \
  --source-ref https://github.com/example-org/example-repo/tree/main/skills/web-access \
  --source-type github-tree \
  --repo-url https://github.com/example-org/example-repo.git \
  --cache-checkout /Users/yup/.skill-hub/sources/example-org_example-repo@main \
  --import-subpath skills/web-access
```

`skill-hub skill import` 本身只负责导入本地目录。
远程仓库的解析、clone/update 和缓存管理由 `skills/skill-installer/scripts/install_skill.py` 负责。

查看已导入 skill 的来源记录：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli skill source list --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli skill source show --root /Users/yup/.skill-hub --name web-access --json
```

## Registry 管理

生成 registry：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root /Users/yup/.skill-hub
```

检查当前 vault 和保存下来的 registry 是否漂移：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub
```

当前 `registry doctor` 会报告：

- `path-mismatch`
- `stale-registry-skill`
- `unregistered-skill`

机器可读输出：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub --json
```

若检测到漂移并希望立即重建 `state/registry.yaml`：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub --rebuild-if-drift
```

生成的 registry 会稳定按 skill 名排序，并包含 `SKILL.md` frontmatter 中的：

- `path`
- `visibility`
- 非空的 `description`
- 非空的 `agents`
- 非空的 `tags`

扫描 vault：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root /Users/yup/.skill-hub
```

查询 registry：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root /Users/yup/.skill-hub --query kubernetes
```

结构化输出：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root /Users/yup/.skill-hub --json
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root /Users/yup/.skill-hub --query kubernetes --json
```

## 审计

检查 profile 在当前 vault 下的暴露情况：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root /Users/yup/.skill-hub
```

结构化输出：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root /Users/yup/.skill-hub --json
```

## Profile 管理

查看 profile：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile list --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli profile show --root /Users/yup/.skill-hub --name default
```

创建或删除 profile：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile add --root /Users/yup/.skill-hub \
  --name default \
  --agent codex \
  --skill billing-labeler \
  --skill k8s-finder \
  --exclude experimental-*

PYTHONPATH=src python3 -m skill_hub_manager.cli profile remove --root /Users/yup/.skill-hub --name default
```

增量更新 profile：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile update --root /Users/yup/.skill-hub \
  --name default \
  --agent claude \
  --add-skill release-checker \
  --remove-skill billing-labeler \
  --add-exclude legacy-* \
  --remove-exclude experimental-*
```

复制或重命名 profile：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile clone --root /Users/yup/.skill-hub \
  --name default \
  --to staging

PYTHONPATH=src python3 -m skill_hub_manager.cli profile rename --root /Users/yup/.skill-hub \
  --name staging \
  --to release
```

校验单个或全部 profile：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub --name default
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub
```

结构化输出：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub --json
```

`profile add`、`profile clone`、`profile rename` 默认不会覆盖已存在的目标 profile 文件。

## Sync 与诊断

检查最后一次同步目标中的断链：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor --root /Users/yup/.skill-hub
```

`doctor --root` 会读取 `state/last-sync.json`，并检查：

- 已损坏的 symlink
- 上一次同步记录中存在、但当前目标目录中已消失的链接

执行同步：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills
```

预览同步计划但不落盘：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills \
  --dry-run
```

结构化输出：

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills \
  --json
```

当执行 `sync --root` 时，CLI 会写入 `state/last-sync.json`，方便后续 drift 检查。

当前 sync 行为是收敛式的：

- 会删除目标目录中已不属于当前 profile 的陈旧 symlink
- 不会修改普通文件

当前所有 JSON 输出协议见 [json-output.md](docs/schema/json-output.md)。

## 状态

当前项目已经具备本地优先 CLI 的可交付能力。除非你明确要求，否则不会自动 push 代码。
