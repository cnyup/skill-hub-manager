# 安装说明

[English Version](installation.md)

当前项目支持两种实际可用的 `skill-hub` 运行方式。

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
