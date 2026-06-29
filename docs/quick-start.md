# Quick Start

## 1. Initialize a local workspace

Use a directory outside the GitHub repository:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli init --root /Users/yup/.skill-hub
```

This creates:

```text
/Users/yup/.skill-hub/
  skills/
  profiles/
  state/
```

## 2. Place skills in the vault

Each skill should live in its own directory and contain a `SKILL.md`.

## 3. Create or edit a profile

Prefer generating the profile through CLI so the file format stays consistent:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile add --root /Users/yup/.skill-hub \
  --name default \
  --agent codex \
  --skill k8s-finder \
  --skill billing-labeler \
  --exclude billing-labeler \
  --exclude experimental-*
```

The command writes `/Users/yup/.skill-hub/profiles/default.yaml`.

Start with a simple allowlist:

```yaml
name: default
agent: codex
skills:
  - k8s-finder
  - billing-labeler
exclude:
  - billing-labeler
  - experimental-*
```

`exclude` supports explicit skill names and simple glob patterns such as `experimental-*`.

To delete a profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile remove --root /Users/yup/.skill-hub --name default
```

To incrementally update an existing profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile update --root /Users/yup/.skill-hub \
  --name default \
  --agent claude \
  --add-skill release-checker \
  --remove-skill billing-labeler \
  --add-exclude legacy-* \
  --remove-exclude experimental-*
```

To copy or rename a profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile clone --root /Users/yup/.skill-hub \
  --name default \
  --to staging

PYTHONPATH=src python3 -m skill_hub_manager.cli profile rename --root /Users/yup/.skill-hub \
  --name staging \
  --to release
```

## 4. Build the registry

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root /Users/yup/.skill-hub
```

This writes `/Users/yup/.skill-hub/state/registry.yaml` with stable ordering and basic skill metadata from `SKILL.md` frontmatter.

You can inspect or search the generated registry:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root /Users/yup/.skill-hub --query kubernetes
```

You can also audit profiles against the current vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root /Users/yup/.skill-hub
```

## 5. Sync the profile

Use the sync command to materialize symlinks into the target agent directory.

Inspect the profile before syncing if needed:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile list --root /Users/yup/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli profile show --root /Users/yup/.skill-hub --name default
```

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills
```

Preview the sync plan first if needed:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root /Users/yup/.skill-hub \
  --target /Users/yup/.codex/skills \
  --dry-run
```

This also writes `/Users/yup/.skill-hub/state/last-sync.json` so later checks can detect drift from the last successful sync.

During sync, stale symlink entries in the target that are no longer part of the current profile are removed automatically. Regular files in the target are not modified.

You can also inspect the current vault contents:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root /Users/yup/.skill-hub
```

## 6. Verify

Run the doctor or audit command to confirm all links resolve correctly.

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor --root /Users/yup/.skill-hub
```

`doctor --root` reads the last synced target from `state/last-sync.json`, then checks both broken symlinks and links that were present in the last sync record but are no longer present in that target directory.

## Local development

Run tests without external dependencies:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
