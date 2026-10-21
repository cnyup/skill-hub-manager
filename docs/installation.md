# Installation

[中文版本](installation.zh-CN.md)

This project currently supports two practical ways to run `skill-hub`.

## Prerequisites

Before installing, ensure you have:

- **Python 3.11+** — check with `python3 --version`
- **Git** — required for cloning the manager and any remote skills — check with `git --version`
- **macOS or Linux** — Windows is not yet tested (symlink support requires special configuration)
- Optional: **pip + setuptools** — only needed if you want `skill-hub` on your shell `PATH` instead of using the bundled `./bin/skill-hub` wrapper

If any of these are missing, install them first:

```bash
# Python (via your preferred method, e.g. pyenv, homebrew, apt)
python3 --version    # must be >= 3.11

# Git
git --version        # macOS ships git with Xcode Command Line Tools
```

## Skill-Based Flow

This is the agent-first flow. The user should only need to talk to an agent.

Installing the manager itself should not require exposing a bootstrap skill first.
The recommended path is to give the GitHub repository URL directly to the agent and let it perform a normal install flow.

### Recommended Bootstrap Flow

Send:

```text
Install this skills manager and initialize it:
https://github.com/cnyup/skill-hub-manager.git

Requirements:
- use ~/skill-hub-manager as the default checkout path
- use ~/.skill-hub as the default workspace
- show the plan and ask for confirmation before any clone, update, or initialization
- show me the validation commands after install
```

The agent should:

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

Use the manual CLI path below first.
After the manager is installed, expose `skills/skill-installer/` to the agent so future business skill installs can stay conversational. OpenCode can load this bootstrap skill from `~/.config/opencode/skills/` globally or from `<project>/.opencode/skills/` for one project.

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

If you want the skill visible to a specific agent, keep talking to the agent and ask it to update the relevant profile and sync target.
Do not run those steps yourself unless you are using the CLI fallback.

### OpenCode Through an LLM

Use the global target `~/.config/opencode/skills/` only for skills that should be available in every OpenCode project. For project isolation, sync to `<project>/.opencode/skills/` instead.

From an OpenCode session opened in the target project, send:

```text
Install this skill into my skill-hub workspace and expose it only to this OpenCode project:
https://github.com/example-org/example-repo/tree/main/skills/web-access

Project directory: /path/to/project
Profile name: opencode-project
Sync target: /path/to/project/.opencode/skills
Before any clone, update, profile change, or sync, show the complete plan and ask for confirmation.
```

The LLM should keep the source in `~/.skill-hub`, update only the named profile, and sync only to the requested project target. It must not substitute the global target unless you explicitly request global availability. Quit and restart OpenCode after syncing because it loads skills at startup.

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

OpenCode global example:

```bash
./bin/skill-hub sync --root ~/.skill-hub --target ~/.config/opencode/skills
```

For a project-only OpenCode install, replace the target with `/path/to/project/.opencode/skills`.

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

## Notes on Installation Methods

Both installation methods are fully supported:

- **`./bin/skill-hub`** (checkout wrapper) is the simplest path — no packaging tools needed. It sets `PYTHONPATH=src` and runs the CLI directly. Use this when working from a Git checkout, in restricted environments, or for local development.
- **`pip install -e .`** (editable install) puts `skill-hub` on your shell `PATH` via a console script declared in `pyproject.toml`. Use this on a normal workstation where you want the command available globally.

If `pip install -e .` fails, the most common causes are:
- Missing `setuptools` in your Python environment — fix with `python3 -m pip install setuptools`
- Build isolation unable to reach PyPI — try `pip install -e . --no-build-isolation`

The checkout wrapper always works regardless of packaging tool availability.

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
