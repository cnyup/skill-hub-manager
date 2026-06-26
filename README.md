# skill-hub-manager

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

## What lives where

- GitHub: manager code, examples, schemas, docs, tests
- Local vault: real skills and private assets
- Profiles: can be public or private depending on use

## Current CLI

The MVP provides:

- `skill-hub --version`
- `skill-hub init --root <path>`
- `skill-hub registry build --root <path>`
- `skill-hub scan --root <path>`
- `skill-hub sync --root <path> --target <path>`
- `skill-hub doctor --root <path>`

Run from a checkout without installing:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli init --root /Users/yup/.skill-hub
```

Then build a registry from the local vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root /Users/yup/.skill-hub
```

The generated registry currently includes `path`, `description`, `visibility`, `agents`, and `tags` when those fields exist in `SKILL.md` frontmatter.

Scan the workspace vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root /Users/yup/.skill-hub
```

Check for broken symlinks in the workspace skill directory:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor --root /Users/yup/.skill-hub
```

## Status

Local-first CLI MVP in progress. Code is not pushed unless explicitly requested.
