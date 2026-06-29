# JSON Output Schemas

This document describes the current machine-readable output formats exposed by the CLI.

## `sync --json`

Commands:

```bash
skill-hub sync --root <path> --target <path> --json
skill-hub sync --root <path> --target <path> --dry-run --json
```

Shape:

```json
{
  "mode": "apply",
  "profile": "default",
  "agent": "codex",
  "target": "/path/to/target",
  "linked": ["k8s-finder"],
  "missing": [],
  "removed": []
}
```

Notes:

- `mode` is `apply` or `dry-run`
- `linked` is the final desired linked skill set processed in this run
- `missing` contains requested skills not found in the vault
- `removed` contains stale symlink names removed or planned for removal

## `profile validate --json`

Command:

```bash
skill-hub profile validate --root <path> --json
```

Shape:

```json
{
  "profiles": [
    {
      "profile": "default",
      "valid": false,
      "issues": ["missing-skill: missing-skill"]
    }
  ]
}
```

Notes:

- `valid` is `true` when `issues` is empty
- `issues` currently includes:
  - `empty-skills`
  - `duplicate-skill: <name>`
  - `missing-skill: <name>`

## `registry doctor --json`

Command:

```bash
skill-hub registry doctor --root <path> --json
```

Shape:

```json
{
  "ok": false,
  "issues": [
    "path-mismatch: k8s-finder registry=/tmp/old vault=/tmp/new",
    "stale-registry-skill: stale-skill"
  ]
}
```

Notes:

- `ok` is `true` when `issues` is empty
- `issues` currently includes:
  - `path-mismatch: <skill> registry=<path> vault=<path>`
  - `stale-registry-skill: <skill>`
  - `unregistered-skill: <skill>`

## `ls --json` and `find --json`

Commands:

```bash
skill-hub ls --root <path> --json
skill-hub find --root <path> --query <text> --json
```

Shape:

```json
{
  "skills": [
    {
      "name": "k8s-finder",
      "path": "/path/to/skill",
      "visibility": "team",
      "description": "Find Kubernetes services",
      "agents": ["codex"],
      "tags": ["infra", "kubernetes"]
    }
  ]
}
```

Notes:

- `skills` is ordered the same way as the loaded registry entries
- optional fields may be absent if not present in `registry.yaml`

## `audit --json`

Command:

```bash
skill-hub audit --root <path> --json
```

Shape:

```json
{
  "profiles": [
    {
      "profile": "default",
      "agent": "codex",
      "effective_skills": ["k8s-finder", "missing-skill"],
      "missing_skills": ["missing-skill"]
    }
  ]
}
```

Notes:

- `effective_skills` reflects `exclude` processing
- `missing_skills` is the subset of effective skills absent from the vault
