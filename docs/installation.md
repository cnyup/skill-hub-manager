# Installation

[中文版本](installation.zh-CN.md)

This project currently supports two practical ways to run `skill-hub`.

## Skill-Based Flow

The public installer skill bootstraps the manager only. It does not contain private skills, private vault content, or other sensitive assets.

### How To Use The Installer Skill

1. Clone this repository on the new machine:

```bash
git clone https://github.com/cnyup/skill-hub-manager.git ~/skill-hub-manager
cd ~/skill-hub-manager
```

2. Copy the installer skill into a skill directory your agent already reads:

```bash
mkdir -p ~/.codex/skills
cp -R ~/skill-hub-manager/skills/install-skill-hub ~/.codex/skills/
```

3. In the agent, send a request like:

```text
Use the install-skill-hub skill. Install skill-hub-manager for Codex, detect the target skills directory, ask me to confirm every clone, update, and sync path, then sync the selected profile.
```

4. Confirm these values before the agent proceeds:
- manager checkout path
- workspace root such as `~/.skill-hub`
- profile name such as `codex`
- target skills directory such as `~/.codex/skills`

5. Verify the final result:

```bash
~/skill-hub-manager/bin/skill-hub install-state show --root ~/.skill-hub --agent codex --json
```

Detection order:

1. Use the checkout wrapper if `./bin/skill-hub` is available.
2. Otherwise use an installed `skill-hub` command on `PATH`.
3. Otherwise ask before cloning the public repository into a local workspace.
4. Before any update to an existing checkout, ask for explicit confirmation.
5. Before any sync to a target directory, ask for explicit confirmation.

## Manual CLI Example

Use the wrapper when working from a checkout:

```bash
./bin/skill-hub init --root ~/.skill-hub
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills --dry-run
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

Use the installed command on a normal workstation:

```bash
python3 -m pip install -e .
skill-hub init --root ~/.skill-hub
skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

## Agent-Driven Install Example

When an agent handles installation, it should follow the same detection order and pause before changing anything external:

```text
1. Detect an existing checkout wrapper.
2. Detect an installed `skill-hub` command on PATH.
3. If neither exists, ask before cloning the public repository.
4. If an existing checkout needs an update, ask before touching it.
5. If a sync is needed, ask before writing to the target directory.
```

The agent installs the public manager, not private skills.

## Option 1: Wrapper Script From Checkout

This path does not require packaging tools such as `setuptools`.

From the repository root:

```bash
./bin/skill-hub --version
./bin/skill-hub --help
```

The wrapper exports `PYTHONPATH=src` for the current process and then runs:

```bash
python3 -m skill_hub_manager.cli
```

Use this path when:

- you are working directly from the Git checkout
- you are in a restricted or offline environment
- you want the simplest local developer workflow

## Option 2: Editable Install

On a normal machine with Python packaging prerequisites available:

```bash
python3 -m pip install -e .
skill-hub --version
```

This uses the console script declared in `pyproject.toml`.

Use this path when:

- you want `skill-hub` on your shell `PATH`
- you are using a normal online Python environment
- you want shell aliases or automation to call the installed command directly

## Current Limitation

In the current restricted environment used during development verification here, `pip install -e .` could not be fully verified because:

- the Python 3.14 virtual environment did not include `setuptools`
- build isolation attempted to download packaging dependencies from PyPI
- outbound package index access was unavailable

That affects installation verification in this environment, not the CLI runtime itself.

In other words:

- `./bin/skill-hub` is the verified path in the current repository environment
- `pip install -e .` is the standard distribution path for normal Python workstations

## Recommended Local Workflow

For local development and testing:

```bash
./bin/skill-hub --version
PYTHONPATH=src python3 -m unittest discover -s tests
```

For end-user installation on a normal workstation:

```bash
python3 -m pip install -e .
skill-hub --help
```
