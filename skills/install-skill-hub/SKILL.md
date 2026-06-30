---
name: install-skill-hub
description: Use when installing, updating, or syncing the skill-hub package into a workspace, especially when target detection or destination confirmation is needed.
---

# Install Skill Hub

## Workflow

1. Detect the target first with `scripts/detect_target.py`.
2. Ask the user to confirm the target before any clone, update, or sync.
3. If detection fails, stop and ask for a manual target.
4. Before sync, confirm the workspace has skills to sync and that the skills are confirmed. If the workspace has zero skills or the skills are not confirmed, stop.
5. If both a previous install record and a builtin mapping exist, prefer the previous install record.
6. Do not overwrite curated profile skill lists without explicit permission.
7. After confirmation, run `scripts/install_skill_hub.py` with the confirmed target and install parameters.

## Scripts

- `scripts/detect_target.py <workspace-root> [agent]`: detect the target and report confidence, reason, and target directory.
- `scripts/install_skill_hub.py --repo-url ... --checkout-dir ... --workspace-root ... --profile ... --agent ... --target-dir ... --skill ... [--update-manager]`: perform install/update/sync after confirmation.
