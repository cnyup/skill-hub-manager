---
name: skill-installer
description: Use when a user wants to install a business skill into an existing skill-hub-manager workspace from a local path, a Git repository URL, or a GitHub tree URL, and optionally expose it through a profile and sync target.
---

# Skill Installer

## Overview

Install ordinary business skills into an existing `skill-hub-manager` workspace.
This skill assumes the manager is already installed.
It can import a skill from a local path, a Git repository URL, or a GitHub tree URL, then optionally add the skill to a profile and sync that profile to a target directory.
For remote repositories with non-default branches, tags, commits, or nonstandard skill locations, prefer passing an explicit git ref and source subpath.
For GitHub tree URLs whose branch names contain `/`, require an explicit git ref instead of guessing.

## Workflow

1. Read the requested skill source.
2. Detect or infer:
   - workspace root, default `~/.skill-hub`
   - source cache path under `~/.skill-hub/sources/` for remote repositories
   - local import source directory
   - optional explicit git ref
   - optional explicit source subpath inside a repository
   - optional profile name
   - optional sync target directory
3. Before any write action, show the exact plan and ask the user to confirm:
   - source URL or local path
   - clone or update path if the source is remote
   - workspace root
   - final imported skill directory
   - whether to update a profile
   - whether to run sync
4. After confirmation, run `scripts/install_skill.py`.
5. After import succeeds, show:
   - imported skill name
   - workspace path
   - whether the profile was updated
   - whether sync ran

## Rules

- Always ask before `git clone`, `git pull`, profile updates, or sync.
- Use `skill-hub skill import` as the canonical import step after resolving a local skill directory. Do not copy files manually when the CLI can do it.
- If the source is remote and already cached locally, ask whether it should be updated first.
- If the source uses a non-default branch, tag, commit, or nested skill path, prefer an explicit git ref and source subpath instead of guessing.
- If the user does not explicitly ask for profile changes or sync, stop after import and registry rebuild.
- If install fails, report the exact failing command or path.
- When `--update-source` is set, the import automatically uses `--force` to overwrite the existing skill in the vault. This is intentional — the user explicitly asked for an update.

## Script

```bash
python3 scripts/install_skill.py --help
```
