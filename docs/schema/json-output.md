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

## `scan --json`

Command:

```bash
skill-hub scan --root <path> --json
```

Shape:

```json
{
  "skills": ["k8s-finder", "billing-labeler"]
}
```

Notes:

- `skills` is sorted alphabetically
- Unlike `ls --json`, this scans the vault directly (not the registry) and returns names only

## `skill remove --json`

Command:

```bash
skill-hub skill remove --root <path> --name <skill> [--purge-source] --json
```

Shape (success):

```json
{
  "skill": "web-access",
  "target": "/path/to/workspace/skills/web-access",
  "removed": true,
  "purged_source": true,
  "updated_profiles": ["default", "codex"]
}
```

Shape (skill not found):

```json
{
  "skill": "nonexistent",
  "target": "/path/to/workspace/skills/nonexistent",
  "removed": false
}
```

Notes:

- `removed` is `false` if the skill did not exist in the vault
- `purged_source` reflects whether `--purge-source` was passed
- `updated_profiles` lists profiles that contained the skill and were modified
- The registry is always rebuilt after a successful removal

## `skill update --json`

Command:

```bash
skill-hub skill update --root <path> --name <skill> --json
```

Shape (success):

```json
{
  "skill": "web-access",
  "source": "/path/to/cached/source",
  "target": "/path/to/workspace/skills/web-access",
  "replaced": true
}
```

Shape (no source record):

```json
{
  "skill": "nonexistent",
  "updated": false,
  "error": "no source record"
}
```

Notes:

- `replaced` is always `true` for a successful update (the skill already existed)
- Requires a source record with `cache_checkout` or `source` path

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
