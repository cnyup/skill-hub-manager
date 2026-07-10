# Profiles

## Purpose

Profiles control which skills are visible to a given agent or project.

## Recommended model

- `public`
- `team`
- `private`
- `experimental`

## Minimal profile format

```yaml
name: project-a
agent: codex
skills:
  - k8s-finder
  - billing-labeler
```

## Rules

- Profiles are allowlists.
- Profiles do not contain skill content.
- Profiles can live in GitHub if they only reference public concepts.
- Private profiles should stay local.
- When a skill is removed via `skill-hub skill remove`, it is automatically removed from all profiles that reference it.
- Custom agent targets can be configured via `~/.skill-hub/agents.yaml` or the `SKILL_HUB_AGENTS` environment variable (JSON format).

