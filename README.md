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
- `skill-hub scan --vault <path>`
- `skill-hub sync --vault <path> --profile <profile.yaml> --target <path>`
- `skill-hub doctor --target <path>`

Run from a checkout without installing:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --vault /Users/yup/.skill-hub/skills
```

## Status

Local-first CLI MVP in progress. Code is not pushed unless explicitly requested.
