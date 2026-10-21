# Quick Start

This page documents the manual CLI fallback.
If you are a new user and want the agent-first path, follow the README quick usage section instead.

## 0. Choose How To Run The CLI

From a local checkout, the simplest path is the bundled wrapper:

```bash
./bin/skill-hub --version
```

On a normal Python workstation, you can also install the command:

```bash
python3 -m pip install -e .
skill-hub --version
```

More details are in `docs/installation.md`.

## 1. Initialize a local workspace

Use a directory outside the GitHub repository:

```bash
./bin/skill-hub init --root ~/.skill-hub
```

Equivalent source-run form:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli init --root ~/.skill-hub
```

This creates:

```text
~/.skill-hub/
  skills/
  profiles/
  state/
```

## 2. Place skills in the vault

Each skill should live in its own directory and contain a `SKILL.md`.

Import a skill from a local directory:

```bash
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/skill-dir
```

Force-overwrite an existing skill:

```bash
./bin/skill-hub skill import --root ~/.skill-hub --source /path/to/skill-dir --force
```

Remove a skill from the vault (also rebuilds registry and removes from all profiles):

```bash
./bin/skill-hub skill remove --root ~/.skill-hub --name web-access
```

Remove and also purge the source record:

```bash
./bin/skill-hub skill remove --root ~/.skill-hub --name web-access --purge-source
```

Update a skill from its cached remote source:

```bash
./bin/skill-hub skill update --root ~/.skill-hub --name web-access
```

Inspect source records:

```bash
./bin/skill-hub skill source list --root ~/.skill-hub
./bin/skill-hub skill source show --root ~/.skill-hub --name web-access --json
```

## 3. Create or edit a profile

Prefer generating the profile through CLI so the file format stays consistent:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile add --root ~/.skill-hub \
  --name default \
  --agent codex \
  --skill k8s-finder \
  --skill billing-labeler \
  --exclude billing-labeler \
  --exclude experimental-*
```

The command writes `~/.skill-hub/profiles/default.yaml`.

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
PYTHONPATH=src python3 -m skill_hub_manager.cli profile remove --root ~/.skill-hub --name default
```

To incrementally update an existing profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile update --root ~/.skill-hub \
  --name default \
  --agent claude \
  --add-skill release-checker \
  --remove-skill billing-labeler \
  --add-exclude legacy-* \
  --remove-exclude experimental-*
```

To copy or rename a profile:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile clone --root ~/.skill-hub \
  --name default \
  --to staging

PYTHONPATH=src python3 -m skill_hub_manager.cli profile rename --root ~/.skill-hub \
  --name staging \
  --to release
```

These write commands refuse to overwrite an existing target profile file.

To validate one profile or all profiles:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root ~/.skill-hub --name default
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root ~/.skill-hub
```

For machine-readable profile validation:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile validate --root ~/.skill-hub --json
```

## 4. Build the registry

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry build --root ~/.skill-hub
```

This writes `~/.skill-hub/state/registry.yaml` with stable ordering and basic skill metadata from `SKILL.md` frontmatter.

You can inspect or search the generated registry:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root ~/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root ~/.skill-hub --query kubernetes
```

For machine-readable registry entry output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli ls --root ~/.skill-hub --json
PYTHONPATH=src python3 -m skill_hub_manager.cli find --root ~/.skill-hub --query kubernetes --json
```

You can also check whether `state/registry.yaml` has drifted from the current vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root ~/.skill-hub
```

For machine-readable registry diagnostics:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root ~/.skill-hub --json
```

To automatically rewrite the registry when drift is detected:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli registry doctor --root ~/.skill-hub --rebuild-if-drift
```

You can also audit profiles against the current vault:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root ~/.skill-hub
```

For machine-readable audit output:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli audit --root ~/.skill-hub --json
```

## 5. Sync the profile

Use the sync command to materialize symlinks into the target agent directory.

Inspect the profile before syncing if needed:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli profile list --root ~/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli profile show --root ~/.skill-hub --name default
```

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root ~/.skill-hub \
  --target ~/.codex/skills
```

Preview the sync plan first if needed:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root ~/.skill-hub \
  --target ~/.codex/skills \
  --dry-run
```

If you want machine-readable sync results for scripts or future UI integration:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli sync --root ~/.skill-hub \
  --target ~/.codex/skills \
  --json
```

All current JSON output shapes are documented in `docs/schema/json-output.md`.

For OpenCode, use `~/.config/opencode/skills/` for a global profile, or `<project>/.opencode/skills/` for a profile limited to one project. Restart OpenCode after syncing because it loads skills at startup.

This also writes `~/.skill-hub/state/last-sync.json` so later checks can detect drift from the last successful sync.

During sync, stale symlink entries in the target that are no longer part of the current profile are removed automatically. Regular files in the target are not modified.

You can also inspect the current vault contents:

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root ~/.skill-hub
PYTHONPATH=src python3 -m skill_hub_manager.cli scan --root ~/.skill-hub --json
```

## 6. Verify

Run the doctor or audit command to confirm all links resolve correctly.

```bash
PYTHONPATH=src python3 -m skill_hub_manager.cli doctor --root ~/.skill-hub
```

`doctor --root` reads the last synced target from `state/last-sync.json`, then checks both broken symlinks and links that were present in the last sync record but are no longer present in that target directory.

## Local development

Run tests without external dependencies:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
