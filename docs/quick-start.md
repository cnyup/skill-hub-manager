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

## 4. Build the registry

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root /Users/yup/.skill-hub
```

This writes `/Users/yup/.skill-hub/state/registry.yaml` with stable ordering and basic skill metadata from `SKILL.md` frontmatter.

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
