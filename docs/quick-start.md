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

## 5. Verify

Run the doctor or audit command to confirm all links resolve correctly.

