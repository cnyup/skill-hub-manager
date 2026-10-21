# JSON Output Schemas

This document describes the current machine-readable output formats exposed by the CLI.

## `sync --json`

Commands:

```bash
skill-hub sync --root <path> --target <path> --json
skill-hub sync --root <path> --target <path> --dry-run --json
skill-hub sync --root <path> --profile-name <name> --target <path> \
  --add-skill <skill> [--remove-skill <skill>] --dry-run --json
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
  "removed": [],
  "conflicts": []
}
```

Notes:

- `mode` is `apply` or `dry-run`
- `linked` contains skills linked successfully or already linked to the same vault source
- `missing` contains requested skills not found in the vault
- `removed` contains stale symlink names removed or planned for removal. Only links pointing into the current vault are managed.
- `conflicts` contains requested skill names whose target entry is a regular file, directory, or external symlink. Sync leaves these entries unchanged and returns a non-zero exit status.

The dry-run form may include `--add-skill` and `--remove-skill` with
`--profile-name`. These changes are applied to an in-memory candidate profile
only: the profile file, target directory, links, and sync state remain
unchanged. Candidate flags without `--dry-run` fail with exit code `2`.

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

## `skill import --json`

Command:

```bash
skill-hub skill import --root <path> --source <dir> [--name <skill>] [--force] --json
```

Shape (success):

```json
{
  "skill": "web-access",
  "source": "/path/to/incoming/web-access",
  "target": "/path/to/workspace/skills/web-access",
  "replaced": false,
  "state_file": "/path/to/workspace/state/skill-sources.json"
}
```

Shape (error, exit 1):

```json
{
  "skill": "web-access",
  "source": "/path/to/incoming/web-access",
  "target": "/path/to/workspace/skills/web-access",
  "replaced": false,
  "state_file": "/path/to/workspace/state/skill-sources.json",
  "error": "exists: /path/to/workspace/skills/web-access"
}
```

Notes:

- `replaced` is `true` only when `--force` overwrote an existing skill
- On error the payload carries an `error` field and the exit code is 1
- A successful import writes or updates the source record in `state_file`

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

## `profile list --json`

Command:

```bash
skill-hub profile list --root <path> --json
```

Shape:

```json
{
  "profiles": ["alpha", "default"]
}
```

Notes:

- `profiles` is sorted alphabetically (same order as the text output)

## `profile show --json`

Command:

```bash
skill-hub profile show --root <path> --name <profile> --json
```

Shape:

```json
{
  "profile": {
    "name": "default",
    "agent": "codex",
    "skills": ["k8s-finder", "experimental-k8s"],
    "exclude": ["experimental-*"],
    "effective_skills": ["k8s-finder"]
  }
}
```

Notes:

- `effective_skills` reflects `exclude` (fnmatch) processing

## `profile add --json`

Command:

```bash
skill-hub profile add --root <path> --name <n> --agent <a> --skill <s> [--exclude <e>] --json
```

Shape (success):

```json
{
  "written": "/path/to/workspace/profiles/codex.yaml"
}
```

Shape (conflict, exit code 1):

```json
{
  "error": "exists: /path/to/workspace/profiles/codex.yaml"
}
```

## `profile remove --json`

Command:

```bash
skill-hub profile remove --root <path> --name <n> --json
```

Shape:

```json
{
  "removed": true
}
```

Notes:

- `removed` is `false` (exit code 1) when the profile does not exist

## `profile update --json`

Command:

```bash
skill-hub profile update --root <path> --name <n> [--agent <a>] [--add-skill <s>] ... --json
```

Shape:

```json
{
  "updated": "/path/to/workspace/profiles/codex.yaml",
  "profile": {
    "name": "codex",
    "agent": "codex",
    "skills": ["k8s-finder", "web-access"],
    "exclude": [],
    "effective_skills": ["k8s-finder", "web-access"]
  }
}
```

## `profile clone --json` / `profile rename --json`

Commands:

```bash
skill-hub profile clone --root <path> --name <n> --to <n2> --json
skill-hub profile rename --root <path> --name <n> --to <n2> --json
```

Shapes:

```json
{
  "cloned": "/path/to/workspace/profiles/n2.yaml"
}
```

```json
{
  "renamed": "/path/to/workspace/profiles/n2.yaml"
}
```

Notes:

- Conflict path outputs `{"error": "exists: ..."}` with exit code 1 (same as `profile add`)

## `registry build --json`

Command:

```bash
skill-hub registry build --root <path> --json
```

Shape:

```json
{
  "wrote": "/path/to/workspace/state/registry.yaml"
}
```

## `doctor --json`

Command:

```bash
skill-hub doctor --target <path> [--root <path>] --json
```

Shape:

```json
{
  "broken": ["broken-link"],
  "expected_missing": []
}
```

Notes:

- Exit code 1 when either list is non-empty (same semantics as the text output)
- `expected_missing` requires `--root` (reads `state/last-sync.json`); empty otherwise
