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

## 为什么要用

这个项目主要解决 4 个问题：

1. 你的真实 skills 只保留一份，不再为多个 agent、多个项目复制多份副本。
2. 你可以按 agent 分配权限，例如只给 Codex 一部分 skill，只给 Claude Code 另一部分 skill。
3. 你可以从远程仓库安装新 skill，也可以把本地已有 skill 纳入统一管理。
4. 整个流程可以尽量通过 agent 对话完成，而不是让用户自己长期手敲终端命令。

## 推荐使用方式

这个项目的默认设计理念是：**用户直接和 AI 沟通，AI 来操作这个管理器。**

也就是说，正常使用时你不应该长期自己手敲这些命令：

- `init`
- `skill import`
- `registry build`
- `profile add/update`
- `sync`

更推荐的方式是：

1. 先让 agent 安装 `skill-hub-manager`
2. 再让 agent 安装或接管 skills
3. 最后让 agent 把目标 profile 同步到对应 agent 目录

CLI 仍然保留，但更偏向底层能力和兜底路径。

## 快速使用

新用户的完整流程应该尽量都通过和 agent 对话完成。
manager 本身不需要先暴露某个 skill 才能安装。
你可以直接把 GitHub 仓库地址给 agent，让它按正常安装流程完成 manager 安装。

你可以直接先对 agent 说：

```text
帮我安装这个 skills 管理器，并完成初始化：
https://github.com/cnyup/skill-hub-manager.git

要求：
- checkout 默认放在 ~/skill-hub-manager
- workspace 默认使用 ~/.skill-hub
- 在任何 clone、update、初始化之前先展示计划并征求确认
- 安装完成后帮我给出验证命令
```

实际流程就是：

1. 先让 agent 直接安装 `skill-hub-manager`
2. manager 装好后，先把 `skills/skill-installer/` 暴露给 agent
3. 然后再让 agent 去装你真正要用的业务 skill

### 第一步：安装 manager

直接对 agent 说：

```text
帮我安装这个 skills 管理器，并完成初始化：
https://github.com/cnyup/skill-hub-manager.git

要求：
- checkout 默认放在 ~/skill-hub-manager
- workspace 默认使用 ~/.skill-hub
- 在任何 clone、update、初始化之前先展示计划并征求确认
- 安装完成后帮我给出验证命令
```

agent 应该负责 clone 或复用现有 checkout、初始化本地 workspace，并告诉你后续验证命令。

### 第二步：先把 `skill-installer` 软链到 agent 可识别的 skills 目录

等 manager 已经存在本地后，让 agent 先把 `~/skill-hub-manager/skills/skill-installer/` 建立软链到 agent 可识别的 skills 目录里。
默认说明如下：

1. Codex 默认目录：`~/.codex/skills/`
2. Claude Code 默认目录：`~/.claude/skills/`

然后对 agent 说：

```text
请先把 `~/skill-hub-manager/skills/skill-installer/` 通过软链暴露给当前 agent。
默认目标目录：
- Codex 使用 ~/.codex/skills/
- Claude Code 使用 ~/.claude/skills/

如果你需要修改目标目录，或者要覆盖现有同名链接，先把计划展示给我确认。
```

### 第三步：安装你真正需要的业务 skill

等 `skill-installer` 已经暴露成功后，再把具体 skill 发给 agent：

```text
帮我把这个 skill 安装到我的 skill-hub workspace：
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

agent 应该负责解析来源、把 skill 导入到 `~/.skill-hub/skills/`、重建 registry，并且在任何 profile 更新或 sync 之前先征求确认。

### 第四步：让对应 agent 看见它

如果你希望某个 agent 能使用这个 skill，再让 agent 处理 profile 和 sync。
只要你走的是 agent 流程，就不需要自己手工执行 `skill import`、`registry build` 或 `sync`。

### CLI 兜底路径

如果你不走 agent，才使用 CLI 作为兜底路径：

```bash
./bin/skill-hub init --root ~/.skill-hub
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/local-skill
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

如果 skill 来源是远程仓库 URL，先让 `skills/skill-installer/scripts/install_skill.py` 完成解析和缓存，再对解析出的本地目录调用 `skill-hub skill import`。

## 安装后下一步该做什么

如果你刚刚把 manager 安装到本地，最推荐的下一步不是手工敲命令，而是立刻告诉 agent 你要走哪条线：

1. 接管本地已有 skills，给 Codex 用
2. 下载新的 remote skills，给 Claude Code 用

你只需要告诉 agent：

- skill 来源在哪
- 想给哪个 agent 用
- 是否要先展示计划再执行

剩下的事情交给这个管理器和 installer skills 去完成。

## AI 实际用法

下面两条就是这个项目最重要的实际使用路径。

### 场景一：把你本地已有 skills 纳入统一管理，并给 Codex 使用

目标：

- 你本地已经有一批 skills
- 你希望它们进入统一 workspace
- 然后只同步一部分给 Codex 使用

推荐直接对 agent 说：

```text
帮我把我本地已有的 skills 纳入 skill-hub-manager 管理。
workspace 用默认的 ~/.skill-hub。
把适合 Codex 使用的 skills 放到 codex 这个 profile，
然后同步到 Codex 的 skills 目录。
如果有任何会修改磁盘状态的操作，先把计划展示给我确认。
```

这条链路里，agent 应该完成：

1. 检测 `skill-hub-manager` 是否已经安装
2. 识别你现有的本地 skill 目录
3. 把这些 skill 导入 `~/.skill-hub/skills/`
4. 建立或更新 `codex` profile
5. 执行 sync，把 profile 暴露到 Codex 目录

最终效果是：

- skill 内容在 `~/.skill-hub/skills/` 里统一管理
- Codex 实际读取的是 sync 后的目标目录
- 以后更新 skill，只需要维护一份源 skill

### 场景二：下载新的 remote skills，并给 Claude Code 使用

目标：

- 你发现了一个远程 skill 仓库
- 你想把其中一个或多个 skills 下载到本地
- 再只同步给 Claude Code 使用

推荐直接对 agent 说：

```text
帮我把这个远程 skill 安装到我的 skill-hub workspace，
然后把它加入 claude-code 这个 profile，
最后同步到 Claude Code 的 skills 目录：
https://github.com/example-org/example-repo/tree/main/skills/web-access

如果仓库里有多个 skills，先告诉我你识别到哪些可选项。
如果有 clone、update、profile 变更或 sync，先展示计划给我确认。
```

这条链路里，agent 应该完成：

1. 解析 Git 仓库 URL 或 GitHub tree URL
2. 将远程仓库缓存到 `~/.skill-hub/sources/`
3. 把目标 skill 导入 `~/.skill-hub/skills/`
4. 建立或更新 `claude-code` profile
5. 执行 sync，把 profile 暴露到 Claude Code 目录

最终效果是：

- 远程 skill 被本地缓存并纳入统一管理
- Claude Code 只读取你允许它使用的那部分 skill
- 后续更新时，agent 可以继续基于同一来源做 update-source

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

当前仓库里和安装链路相关的公开 skill 主要是：

1. `skill-installer`
   负责把普通业务 skill 导入到已经存在的 skill-hub-manager workspace，并可选更新 profile 与执行 sync。
2. `self-installer`
   仍然保留在仓库中，但不再作为推荐的新用户入口。manager 本身更适合让 agent 直接根据 GitHub 仓库地址执行安装。

这些 skill 都是公开的，不包含任何私有 vault 内容。

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

1. 直接把 manager 仓库地址交给 agent。
2. 然后直接对 agent 说：

```text
帮我安装这个 skills 管理器，并完成初始化：
https://github.com/cnyup/skill-hub-manager.git

要求：
- checkout 默认放在 ~/skill-hub-manager
- workspace 默认使用 ~/.skill-hub
- 在任何 clone、update、初始化之前先展示计划并征求确认
- 安装完成后帮我给出验证命令
```

3. agent 应该执行：
   - 检测或推断 checkout 路径、workspace 根目录
   - 先展示完整计划
   - 在任何 clone、update、workspace 初始化之前先向用户确认
   - 安装 manager
4. 安装完成后，用下面命令验证：

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

如果你当前还没有合适的 agent 文件系统权限，才退回到 [installation.zh-CN.md](docs/installation.zh-CN.md) 里的 CLI 路径。

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
