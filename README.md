# skill-hub-manager

[中文版本](README.zh-CN.md)

Private skills manager for multi-agent, multi-project workflows.

This repository is intentionally public and does **not** contain the user's actual skills.
The real skill content lives in a local vault outside the repo, and this project only manages:

- discovery
- registry generation
- profile-based access control
- symlink-based syncing
- audit and documentation

## Core idea

- Public GitHub repo: code, docs, templates, tests
- Private local vault: actual `SKILL.md` content and any sensitive assets
- Profiles: per-agent or per-project allowlists
- Sync engine: materializes allowed skills into agent-specific target directories

## How It Works

```text
                One private skill vault
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
│   Index of discovered skills and metadata         │
└────────────────────────────────────────────────────┘
                         │
                         │ profile rules decide exposure
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
           Codex                Claude             Project agent
```

The important detail is that the real skill content stays in one place. `sync` only projects the allowed subset into each agent's target directory.

## Why Use It

This project solves four concrete problems:

1. Keep one real copy of each skill instead of duplicating the same skills across agents and projects.
2. Control exposure per agent, for example one set for Codex and another set for Claude Code.
3. Bring both local skills and remote skills into one managed workspace.
4. Let agents operate the manager through conversation instead of forcing users to live in the terminal.

## Recommended Usage Model

The default design principle of this project is: **the user talks to AI, and the AI operates the manager.**

In normal usage, the user should not need to keep typing low-level commands such as:

- `init`
- `skill import`
- `registry build`
- `profile add/update`
- `sync`

The preferred flow is:

1. let an agent install `skill-hub-manager`
2. let an agent install or adopt skills
3. let an agent sync the right profile into the right agent directory

The CLI still exists, but mainly as a low-level interface and fallback path.

## Quick Usage

For a new user, the entire flow should happen through conversation with an agent.
Installing the manager itself should not require exposing a bootstrap skill first.
You can give the GitHub repository URL directly to the agent and let it perform a normal install flow.

You can say this to the agent first:

```text
Install this skills manager and initialize it:
https://github.com/cnyup/skill-hub-manager.git

Requirements:
- use ~/skill-hub-manager as the default checkout path
- use ~/.skill-hub as the default workspace
- show the plan and ask for confirmation before any clone, update, or initialization
- show me the validation commands after install
```

In practice, that means:

1. let the agent install `skill-hub-manager` directly
2. after the manager is installed, expose `skills/skill-installer/` to the agent
3. then let the agent install the business skill you actually want

### Step 1: install the manager

Tell the agent:

```text
Install this skills manager and initialize it:
https://github.com/cnyup/skill-hub-manager.git

Requirements:
- use ~/skill-hub-manager as the default checkout path
- use ~/.skill-hub as the default workspace
- show the plan and ask for confirmation before any clone, update, or initialization
- show me the validation commands after install
```

The agent should clone or reuse the checkout, initialize the local workspace, and show you the next validation commands.

### Step 2: symlink `skill-installer` into an agent-readable skills directory

After the manager exists locally, ask the agent to create a symlink from `~/skill-hub-manager/skills/skill-installer/` into an agent-readable skills directory.
The default targets are:

1. Codex: `~/.codex/skills/`
2. Claude Code: `~/.claude/skills/`

Then tell the agent:

```text
Please expose `~/skill-hub-manager/skills/skill-installer/` to this agent via a symlink.
Default target directories:
- Codex uses ~/.codex/skills/
- Claude Code uses ~/.claude/skills/

If you need to change the target directory or overwrite an existing link, show me the plan first.
```

### Step 3: install the business skill you actually want

After `skill-installer` is available, send the skill source:

```text
Install this skill into my skill-hub workspace:
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

The agent should resolve the source, import the skill into `~/.skill-hub/skills/`, rebuild the registry, and ask before any profile update or sync.

### Step 4: expose the right profile

If you want the skill available to a specific agent, tell the agent which profile to update and which target directory to sync.
You do not need to run `skill import`, `registry build`, or `sync` yourself unless you are using the CLI fallback.

### CLI fallback

If you are not using an agent, use the CLI only as a fallback path:

```bash
./bin/skill-hub init --root ~/.skill-hub
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/local-skill
./bin/skill-hub registry build --root ~/.skill-hub
./bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

If the skill source is a remote repository URL, let `skills/skill-installer/scripts/install_skill.py` resolve and cache it first, then call `skill-hub skill import` on the resolved local directory.

## What To Do Right After Installation

If you just installed the manager locally, do not start by typing CLI commands.
Instead, tell the agent which of these you want:

1. adopt existing local skills for Codex
2. install new remote skills for Claude Code

You only need to tell the agent:

- where the skills come from
- which agent should receive them
- whether you want a plan shown before execution

The manager and installer skills should handle the rest.

## Real AI Workflows

These are the two main workflows this project is built for.

### Scenario 1: adopt your existing local skills and expose them to Codex

Goal:

- you already have local skills
- you want them moved under one managed workspace
- you want only the Codex subset exposed to Codex

Recommended prompt to the agent:

```text
Help me adopt my existing local skills into skill-hub-manager.
Use the default workspace ~/.skill-hub.
Put the skills that are appropriate for Codex into a profile named codex,
then sync that profile into the Codex skills directory.
Before any operation that changes disk state, show me the plan and ask for confirmation.
```

The agent should:

1. detect whether `skill-hub-manager` is already installed
2. find your existing local skill directories
3. import those skills into `~/.skill-hub/skills/`
4. create or update the `codex` profile
5. run sync so Codex sees the selected skills

End result:

- skills are centrally managed under `~/.skill-hub/skills/`
- Codex reads only the synced projection
- future updates happen in one source location

### Scenario 2: download new remote skills and expose them to Claude Code

Goal:

- you found a remote skill repository
- you want one or more skills installed locally
- you want only the Claude Code subset exposed to Claude Code

Recommended prompt to the agent:

```text
Help me install this remote skill into my skill-hub workspace,
add it to a profile named claude-code,
and sync that profile into the Claude Code skills directory:
https://github.com/example-org/example-repo/tree/main/skills/web-access

If the repository contains multiple skills, tell me what options you found first.
Before any clone, update, profile change, or sync, show me the plan and ask for confirmation.
```

The agent should:

1. resolve the Git repository URL or GitHub tree URL
2. cache the remote repository under `~/.skill-hub/sources/`
3. import the selected skill into `~/.skill-hub/skills/`
4. create or update the `claude-code` profile
5. run sync so Claude Code sees the selected skills

End result:

- the remote skill is cached locally and brought under one manager
- Claude Code sees only the subset you allow
- later updates can reuse the same source and run `update-source`

## What lives where

- GitHub: manager code, examples, schemas, docs, tests
- Local vault: real skills and private assets
- Profiles: can be public or private depending on use

## Installation

Two supported ways to run the CLI:

1. From a checkout, without Python packaging setup:

```bash
./bin/skill-hub --version
./bin/skill-hub --help
```

2. As an installed command on a normal Python workstation:

```bash
python3 -m pip install -e .
skill-hub --version
```

The checkout wrapper path is the default recommendation because it has been verified in this repository's current development environment.

The full installation notes are in [installation.md](docs/installation.md).

## Built-In Skills

This repository ships these public skills related to installation:

1. `skill-installer`
   Imports ordinary business skills into an existing skill-hub-manager workspace, then optionally updates a profile and runs sync.
2. `self-installer`
   Still exists in the repository, but is no longer the recommended entrypoint for new users. For manager installation, it is simpler to let the agent work directly from the GitHub repository URL.

These skills are public and contain no private vault content.

## Installing Business Skills

After the manager is installed, use `skill-installer` for the second line:

```text
Install this skill into my skill-hub workspace:
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

The `skill-installer` flow should:

1. resolve a local path, Git repository URL, or GitHub tree URL
2. cache remote repositories under `~/.skill-hub/sources/`
3. import the selected skill into `~/.skill-hub/skills/`
4. rebuild the registry
5. optionally add the skill to a profile
6. optionally sync the updated profile to a target directory

For remote repositories on non-default branches, tags, commits, or custom subpaths, prefer an explicit git ref and source subpath.
This is especially important for GitHub tree URLs whose branch names contain `/`, for example `feature/demo`.

## Installing The Manager

Recommended agent-driven flow:

1. Give the manager repository URL to the agent.
2. Ask the agent:

```text
Install this skills manager and initialize it:
https://github.com/cnyup/skill-hub-manager.git

Requirements:
- use ~/skill-hub-manager as the default checkout path
- use ~/.skill-hub as the default workspace
- show the plan and ask for confirmation before any clone, update, or initialization
- show me the validation commands after install
```

3. The agent should:
   - detect or infer checkout path and workspace root
   - show the exact plan first
   - ask for confirmation before any clone, update, or workspace initialization
   - install the manager
4. Verify the result with:

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

If the agent does not have the filesystem access needed to clone or initialize locally, use the CLI flow in [installation.md](docs/installation.md) instead.

## Current CLI

The MVP provides:

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

Run from a checkout without installing:

```bash
./bin/skill-hub init --root /Users/yup/.skill-hub
```

Equivalent source-run form:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli init --root /Users/yup/.skill-hub
```

Import a local skill into the workspace:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli skill import \
  --root /Users/yup/.skill-hub \
  --source /Users/yup/skills/web-access
```

Record remote source metadata for a skill that has already been resolved and cached locally:

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

`skill-hub skill import` itself imports from a local directory only.
Remote repository parsing, clone/update, and cache management are handled by `skills/skill-installer/scripts/install_skill.py`.

Inspect imported skill source records:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli skill source list --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli skill source show --root /Users/yup/.skill-hub --name web-access --json
```

Then build a registry from the local vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root /Users/yup/.skill-hub
```

Check whether the saved registry still matches the current vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub
```

`registry doctor` currently reports:

- `path-mismatch`
- `stale-registry-skill`
- `unregistered-skill`

It also supports machine-readable output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub --json
```

If drift is detected and you want to rewrite `state/registry.yaml` immediately:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root /Users/yup/.skill-hub --rebuild-if-drift
```

The generated registry currently uses stable skill-name ordering and includes `path`, `visibility`, and any non-empty `description`, `agents`, and `tags` fields from `SKILL.md` frontmatter.

Scan the workspace vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root /Users/yup/.skill-hub
```

Query the generated registry:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root /Users/yup/.skill-hub --query kubernetes
```

For machine-readable registry entry output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root /Users/yup/.skill-hub --json
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root /Users/yup/.skill-hub --query kubernetes --json
```

Audit profile exposure against the current vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root /Users/yup/.skill-hub
```

For machine-readable audit output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root /Users/yup/.skill-hub --json
```

Inspect available profiles and their effective skills:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile list --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli profile show --root /Users/yup/.skill-hub --name default
```

Create or remove profiles without hand-editing YAML:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile add --root /Users/yup/.skill-hub \
  --name default \
  --agent codex \
  --skill billing-labeler \
  --skill k8s-finder \
  --exclude experimental-*

PYTHONPATH=src python3 -m skill_hub_manager.cli profile remove --root /Users/yup/.skill-hub --name default
```

Incrementally update an existing profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile update --root /Users/yup/.skill-hub \
  --name default \
  --agent claude \
  --add-skill release-checker \
  --remove-skill billing-labeler \
  --add-exclude legacy-* \
  --remove-exclude experimental-*
```

Clone or rename an existing profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile clone --root /Users/yup/.skill-hub \
  --name default \
  --to staging

PYTHONPATH=src python3 -m skill_hub_manager.cli profile rename --root /Users/yup/.skill-hub \
  --name staging \
  --to release
```

Validate one profile or all profiles in the workspace:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub --name default
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub
```

For automation, use JSON output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root /Users/yup/.skill-hub --json
```

`profile add`, `profile clone`, and `profile rename` now refuse to overwrite an existing target profile file.

Check for broken symlinks in the last synced target:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor --root /Users/yup/.skill-hub
```

When you run `sync --root`, the CLI also records the last sync result in `state/last-sync.json`. `doctor --root` uses that file to find the last synced target and report expected links that have disappeared since the last sync.

`sync` is now convergent for symlinks in the target directory: it removes stale symlink entries that are not part of the current profile, while leaving regular files untouched.

Use dry-run before a real sync if you want a change preview without touching the target directory or sync state:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills \
  --dry-run
```

Use JSON output for automation or external tooling:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills \
  --json
```

Current JSON output contracts are documented in [json-output.md](docs/schema/json-output.md).

## Status

Local-first CLI MVP in progress. Code is not pushed unless explicitly requested.
