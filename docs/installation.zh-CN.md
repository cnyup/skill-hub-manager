# 安装说明

[English Version](installation.md)

当前项目支持两种实际可用的 `skill-hub` 运行方式。

## 基于 Skill 的安装流程

仓库自带 1 个和安装相关的公开 skill：

1. `self-installer`
   负责把 `skill-hub-manager` 自身从仓库 URL bootstrap 到当前机器。

这个 skill 不包含任何私有 skills 或私有 vault 内容。

### 推荐的 Bootstrap 流程

如果你的 agent 已经能读取 `self-installer`，直接发送：

```text
帮我安装这个 skills 管理器：
https://github.com/cnyup/skill-hub-manager.git
```

这条 skill 应该执行：

1. 检测或推断 checkout 路径、workspace 根目录
2. 先展示完整计划
3. 在任何 clone、update、workspace 初始化之前先确认
4. 本地安装 manager
5. 初始化 workspace 并生成空 registry
6. 展示后续验证命令

最后用下面命令确认结果：

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

### 如果你当前还没有任何 Agent 可读取的 Skills 目录

先使用下面的手动 CLI 安装方式。manager 装好后，再把 `skills/self-installer/` 暴露给 agent。

## 安装业务 Skills

当本地已经有 manager 之后，把 `skills/skill-installer/` 暴露给 agent，并发送类似请求：

```text
帮我把这个 skill 安装到我的 skill-hub workspace：
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

这条安装器应该执行：

1. 解析来源
2. 将远程仓库缓存到 `~/.skill-hub/sources/`
3. 从缓存中解析出本地 skill 目录
4. 运行 `skill-hub skill import --root ~/.skill-hub --source <local-skill-dir>`
5. 重建 registry
6. 可选通过 `profile update --add-skill` 更新 profile
7. 可选执行 `sync`

如果仓库使用了非默认分支、tag、commit，或者 skill 在自定义路径下，建议显式给出 git ref 和 source subpath。
如果 GitHub tree URL 对应的分支名本身带 `/`，例如 `feature/demo`，更不要依赖自动猜测。

手动 CLI 示例：

```bash
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/skill-dir
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub skill source list --root ~/.skill-hub
./bin/skill-hub skill source show --root ~/.skill-hub --name web-access --json
```

`skill-hub skill import` 本身只接受本地 skill 目录。
远程仓库 URL 的解析能力在 `skills/skill-installer/scripts/install_skill.py` 中。

## 手动 CLI 示例

从 checkout 直接运行时：

```bash
./bin/skill-hub init --root ~/.skill-hub
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills --dry-run
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

在正常工作站上安装后直接使用命令：

```bash
python3 -m pip install -e .
skill-hub init --root ~/.skill-hub
skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

## Agent 驱动安装示例

当 agent 负责安装时，也应遵循相同的检测顺序，并且在修改外部内容前暂停确认：

```text
1. 检测是否已经存在 checkout wrapper。
2. 检测 `PATH` 中是否已有 `skill-hub` 命令。
3. 如果两者都没有，先确认再 clone 公开仓库。
4. 如果已有 checkout 需要更新，先确认再修改。
5. 在初始化或修复本地 workspace 之前，先确认 workspace 根目录。
```

agent 安装的是公开 manager，不是私有 skills。

## 方式一：从代码仓库直接运行 Wrapper

这条路径不依赖 `setuptools` 之类的 Python 打包工具。

在仓库根目录执行：

```bash
./bin/skill-hub --version
./bin/skill-hub --help
```

这个 wrapper 会先为当前进程导出 `PYTHONPATH=src`，然后执行：

```bash
python3 -m skill_hub_manager.cli
```

适合以下场景：

- 你直接在 Git checkout 里工作
- 你所处环境受限或离线
- 你想要最简单的本地开发工作流

## 方式二：Editable Install

在正常的 Python 工作站中，可以直接安装为命令：

```bash
python3 -m pip install -e .
skill-hub --version
```

这会使用 `pyproject.toml` 里声明的 console script。

适合以下场景：

- 你希望 `skill-hub` 直接出现在 shell `PATH` 中
- 你使用的是正常联网的 Python 环境
- 你希望 alias、脚本或自动化直接调用安装后的命令

## 当前限制

在这次开发验证所处的受限环境中，`pip install -e .` 没能被完整验证，原因是：

- Python 3.14 的虚拟环境里没有自带 `setuptools`
- build isolation 会尝试从 PyPI 下载构建依赖
- 当前环境没有可用的外网包索引访问能力

这影响的是“安装验证”，不是 CLI 本身的运行逻辑。

换句话说：

- `./bin/skill-hub` 是当前仓库环境里已经验证通过的路径
- `pip install -e .` 是面向正常 Python 工作站的标准分发路径

## 推荐本地工作流

本地开发和测试：

```bash
./bin/skill-hub --version
PYTHONPATH=src python3 -m unittest discover -s tests
```

正常工作站上的终端安装：

```bash
python3 -m pip install -e .
skill-hub --help
```
