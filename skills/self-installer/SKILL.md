---
name: self-installer
description: "[Deprecated] Use when a user wants skill-hub-manager itself installed or updated from a Git repository on the current machine. For new users, prefer giving the agent the GitHub URL directly — see Quick Start in README.md. This skill is kept for legacy compatibility only."
deprecated: true
---

# Self Installer (Deprecated)

> **This skill is deprecated.** For installing skill-hub-manager, give the agent the GitHub URL directly instead of using this skill. See the README Quick Start section.

## Overview

Install `skill-hub-manager` itself from a repository URL onto the current machine.
This skill only bootstraps the manager and initializes its local workspace.
It does not install ordinary business skills, create sync profiles, or write into agent skill targets.

## When To Use

- Fresh-machine setup for `skill-hub-manager`
- Reinstalling or repairing a broken local manager checkout
- Recreating the local manager workspace such as `~/.skill-hub`
- Updating an existing local checkout before re-running initialization

Do not use this skill to install ordinary business skills. That is a later workflow.

## Workflow

1. Read the repository URL from the user request. If none is provided, default to `https://github.com/cnyup/skill-hub-manager.git`.
2. Detect or infer:
   - checkout directory, default `~/skill-hub-manager`
   - workspace root, default `~/.skill-hub`
3. Before any write action, show the exact values and ask the user to confirm:
   - repository URL
   - clone or update path
   - workspace root
   - whether manager update is needed
4. After confirmation, run `scripts/install_manager.py` with the confirmed values.
5. After install succeeds, show:
   - checkout path
   - workspace root
   - current manager revision
   - validation commands the user can run next

## Rules

- Always ask before `git clone`, `git pull`, or workspace initialization.
- If the checkout already exists, show whether its `origin` matches the requested repository before continuing.
- If the checkout already exists, ask whether it should be updated before continuing.
- Keep the install additive. Do not create profiles or sync into any agent target directory in this bootstrap flow.
- If install fails, report the exact failing command or path instead of summarizing vaguely.

## Interaction Template

Use this interaction shape before any write action:

1. Show the proposed install plan:
   - repo URL
   - checkout path
   - checkout status
   - workspace root
   - whether manager update is needed
2. Ask for explicit confirmation.
3. If a local checkout already exists:
   - tell the user whether its `origin` matches the requested repo
   - ask whether to reuse it as-is or update it first
4. Only after confirmation, run the installer script without `--plan-only`.

Example confirmation question:

```text
Planned install:
- repo: https://github.com/cnyup/skill-hub-manager.git
- checkout: ~/skill-hub-manager
- checkout status: origin matches requested repo
- workspace: ~/.skill-hub
- update manager: no

Do you want me to continue with clone/update and workspace initialization using these values?
```

## Script

```bash
python3 scripts/install_manager.py --help
```
