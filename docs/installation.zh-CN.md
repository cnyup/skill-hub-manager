# 安装说明

[English Version](installation.md)

当前项目支持两种实际可用的 `skill-hub` 运行方式。

## 基于 Skill 的安装流程

公共 installer skill 只负责引导安装和使用 `skill-hub-manager`，不会包含任何私有 skills、私有 vault 内容或其他敏感资产。

检测顺序如下：

1. 如果 `./bin/skill-hub` 可用，就优先使用 checkout wrapper。
2. 否则使用 `PATH` 中已安装的 `skill-hub` 命令。
3. 如果两者都没有，先确认再 clone 公开仓库到本地工作区。
4. 在更新已有 checkout 之前，先请求明确确认。
5. 在同步到目标目录之前，先请求明确确认。

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
5. 如果需要 sync，先确认再写入目标目录。
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
