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

## Installer Skill

The public installer skill bootstraps `skill-hub-manager`; it does **not** contain private skills, private vault content, or other sensitive assets.

It detects the current setup in this order:

1. existing checkout wrapper: `./bin/skill-hub`
2. installed command on `PATH`: `skill-hub`
3. public repo clone when no local checkout exists, after explicit confirmation
4. update of an existing checkout after explicit confirmation
5. sync of the selected profile after explicit confirmation of the target directory

Before any `clone`, `update`, or `sync`, the agent should ask for confirmation and show the exact path or target it plans to touch.

For manual CLI and agent-driven install examples, see [installation.md](docs/installation.md).

## Current CLI

The MVP provides:

- `skill-hub --version`
- `skill-hub init --root <path>`
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
