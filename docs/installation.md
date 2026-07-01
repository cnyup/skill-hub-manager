# Installation

[中文版本](installation.zh-CN.md)

This project currently supports two practical ways to run `skill-hub`.

## Skill-Based Flow

The repository ships one public installer skill:

1. `self-installer`
   Bootstrap `skill-hub-manager` itself from a repository URL.

The skill contains no private skills or private vault content.

### Recommended Bootstrap Flow

If your agent can already read `self-installer`, send:

```text
Install this skills manager:
https://github.com/cnyup/skill-hub-manager.git
```

The skill should:

1. detect or infer checkout path and workspace root
2. show the exact plan first
3. ask for confirmation before any clone, update, or workspace initialization
4. install the manager locally
5. initialize the workspace and build an empty registry
6. show the next validation commands

Verify the final result:

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

### If You Do Not Yet Have Any Agent-Readable Skill Directory

Use the manual CLI path below first. After the manager is installed, you can expose `skills/self-installer/` to the agent.

## Installing Business Skills

After the manager exists locally, expose `skills/skill-installer/` to the agent and send a request like:

```text
Install this skill into my skill-hub workspace:
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

The installer should:

1. resolve the source
2. cache remote repositories under `~/.skill-hub/sources/`
3. resolve a local skill directory from that cache
4. run `skill-hub skill import --root ~/.skill-hub --source <local-skill-dir>`
5. rebuild the registry
6. optionally update a profile with `profile update --add-skill`
7. optionally run `sync`

If the repository uses a non-default branch, tag, commit, or a custom skill path, supply an explicit git ref and source subpath.
This is especially important when a GitHub tree URL uses a branch name containing `/`, such as `feature/demo`.

Manual CLI example:

```bash
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/skill-dir
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub skill source list --root ~/.skill-hub
./bin/skill-hub skill source show --root ~/.skill-hub --name web-access --json
```

`skill-hub skill import` itself accepts a local skill directory only.
Remote repository URL handling lives in `skills/skill-installer/scripts/install_skill.py`.

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
5. Before initializing or repairing the local workspace, ask for confirmation of the workspace root.
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
