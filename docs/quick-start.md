# Quick Start

## 1. Create a local vault

Choose a directory outside the GitHub repository, for example:

```text
/Users/yup/.skill-hub/skills
```

## 2. Place skills in the vault

Each skill should live in its own directory and contain a `SKILL.md`.

## 3. Create a profile

Start with a simple allowlist:

```yaml
name: project-a
agent: codex
skills:
  - k8s-finder
  - billing-labeler
```

## 4. Sync the profile

Use the sync command to materialize symlinks into the target agent directory.

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync \
  --vault /Users/yup/.skill-hub/skills \
  --profile /Users/yup/.config/skill-hub/profiles/project-a.yaml \
  --target /Users/yup/.codex/skills
```

## 5. Verify

Run the doctor or audit command to confirm all links resolve correctly.

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor \
  --target /Users/yup/.codex/skills
```

## Local development

Run tests without external dependencies:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
