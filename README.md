# skill-hub-manager

[中文版本](README.zh-CN.md)

Private skills manager for multi-agent, multi-project workflows.

This repository is intentionally public and does **not** contain the user's actual skills.
The real skill content lives in a local vault outside the repo, and this project only manages:

- discovery
- registry generation
- profile-based access control
- symlink-based syncing
- audit and documentation

## Prerequisites

Before installing, ensure you have:

| Requirement | Check | Notes |
|---|---|---|
| **Python 3.11+** | `python3 --version` | Required for the CLI and installer scripts |
| **Git** | `git --version` | Required for cloning the manager and remote skills |
| **macOS or Linux** | — | Windows is not yet tested (symlink support needs special setup) |
| **pip + setuptools** (optional) | `python3 -m pip --version` | Only needed if you want `skill-hub` on `PATH` instead of the bundled wrapper |

## Platform Support

- **macOS**: Fully tested and recommended.
- **Linux**: Should work out of the box. The project relies on standard Python 3.11+ and POSIX symlinks.
- **Windows**: Not yet tested. Symlink creation requires administrator privileges or Developer Mode enabled. If you try it, please report results.

## Why Use It

1. **One source of truth** — Keep a single real copy of each skill instead of duplicating across agents and projects.
2. **Per-agent access control** — Give Codex, Claude Code, or OpenCode separate subsets via profiles.
3. **Local + remote** — Import skills from local directories or remote Git repos.
4. **Agent-driven** — Operate the entire manager through conversation, not terminal commands.

## How It Works

The real skill content stays in one private vault. Profiles decide which skills each agent can see. Sync projects the allowed subset into each agent's target directory via symlinks — nothing is duplicated.

<details>
<summary>Architecture diagram</summary>

```text
                One private skill vault
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/skills/                              │
│   demo-skill/                                     │
│   k8s-finder/                                     │
│   billing-labeler/                                │
└────────────────────────────────────────────────────┘
                         │
                         │ scan / registry build
                         ▼
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/state/registry.yaml                  │
│   Index of discovered skills and metadata         │
└────────────────────────────────────────────────────┘
                         │
                         │ profile rules decide exposure
                         ▼
┌────────────────────────────────────────────────────┐
│ ~/.skill-hub/profiles/                            │
│   codex.yaml      -> demo-skill, k8s-finder       │
│   claude.yaml     -> billing-labeler              │
│   project-a.yaml  -> demo-skill                   │
└────────────────────────────────────────────────────┘
             │                    │                    │
             │ sync               │ sync               │ sync
             ▼                    ▼                    ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ ~/.codex/skills/    │ │ ~/.claude/skills/   │ │ ~/project-a/.skills/│
│ demo-skill -> ...   │ │ billing-labeler->...│ │ demo-skill -> ...   │
│ k8s-finder -> ...   │ │                     │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
             │                    │                    │
             ▼                    ▼                    ▼
           Codex                Claude             Project agent
```

</details>

## Quick Start (Agent-Driven)

The default design principle is: **you talk to AI, and the AI operates the manager.**

The full flow — from zero to a synced skill — is four steps. All paths below assume `~/skill-hub-manager` as the checkout location.

### Step 1: Install the manager

Give this prompt to your agent (Codex, Claude Code, etc.):

```text
Install this skills manager and initialize it:
https://github.com/cnyup/skill-hub-manager.git

Requirements:
- checkout at ~/skill-hub-manager
- workspace at ~/.skill-hub
- confirm before any clone or initialization
```

The agent clones (or reuses) the checkout and initializes the workspace.

Verify:

```bash
~/skill-hub-manager/bin/skill-hub --version
~/skill-hub-manager/bin/skill-hub registry doctor --root ~/.skill-hub
```

You can also run the CLI directly without an agent. Two options:

```bash
# From checkout (no packaging tools needed)
~/skill-hub-manager/bin/skill-hub --version

# Or install on PATH
python3 -m pip install -e .
skill-hub --version
```

Full installation notes: [docs/installation.md](docs/installation.md).

### Step 2: Expose `skill-installer` to the agent

**Why this step**: The agent needs the `skill-installer` skill visible in its skills directory so it can install *business* skills for you in Step 3. Without it, the agent has no installer capability.

```text
Symlink ~/skill-hub-manager/skills/skill-installer/ into my agent skills directory (~/.codex/skills/ or ~/.claude/skills/).
```

Default targets:
- **Codex**: `~/.codex/skills/`
- **Claude Code**: `~/.claude/skills/`
- **Cursor**: `~/.cursor/skills/`
- **Windsurf**: `~/.codeium/windsurf/skills/`
- **OpenCode global**: `~/.config/opencode/skills/`
- **OpenCode project-only**: `<project>/.opencode/skills/`

Use OpenCode's global target only when the skill should be available in every OpenCode project. For a project-only install, provide the project path and sync to its `.opencode/skills/` directory.

### Step 3: Install a business skill

Now the agent can import skills from local paths or remote repos:

```text
Install this skill into my skill-hub workspace:
https://github.com/example-org/example-repo/tree/main/skills/web-access
```

The agent resolves the source, imports it into `~/.skill-hub/skills/`, rebuilds the registry, and asks before any profile update or sync.

For remote sources on non-default branches, tags, commits, or custom subpaths, prefer an explicit git ref and source subpath.
This is especially important for GitHub tree URLs whose branch names contain `/`, for example `feature/demo`.

### Step 4: Expose the skill via profile + sync

Tell the agent which profile to update and which target directory to sync:

```text
Add web-access to my claude-code profile and sync to ~/.claude/skills/
```

You only need to tell the agent: where the skills come from, which agent should receive them, and whether to show a plan first.

For a project-scoped OpenCode install, use this prompt:

```text
Install this skill into my skill-hub workspace and expose it only to this OpenCode project:
https://github.com/example-org/example-repo/tree/main/skills/web-access

Project directory: /path/to/project
Profile name: opencode-project
Sync target: /path/to/project/.opencode/skills
Show the complete plan and ask for confirmation before any clone, update, profile change, or sync.
```

Restart OpenCode after syncing because it loads skills at startup.

### CLI Fallback

If you are not using an agent, use the CLI directly:

```bash
~/skill-hub-manager/bin/skill-hub init --root ~/.skill-hub
~/skill-hub-manager/bin/skill-hub skill import --root ~/.skill-hub --source /path/to/local-skill
~/skill-hub-manager/bin/skill-hub registry build --root ~/.skill-hub
~/skill-hub-manager/bin/skill-hub sync --root ~/.skill-hub --target ~/.codex/skills
```

For remote skill sources, let `skills/skill-installer/scripts/install_skill.py` resolve and cache first, then import the local directory.

Sync only removes stale links that point into the current vault. Existing regular files, directories, and external symlinks are preserved; a same-name target is reported as a conflict instead of being overwritten.

## Advanced Workflows

### Manage the same skill across multiple agents

```text
I have web-access in my vault. Add it to both the codex and claude-code profiles,
then sync each profile to its respective agent directory.
Show me the plan before syncing.
```

### Bulk-import existing local skills

```text
Scan ~/my-skills/ for skill directories. List what you find,
then import all of them into ~/.skill-hub/skills/ and add them to a profile named codex.
Confirm before importing.
```

### Update a skill from its remote source

```text
Update web-access from its cached remote source. After updating, re-sync the claude-code profile.
```

Profile docs: [docs/profiles.md](docs/profiles.md). Full CLI reference: [docs/quick-start.md](docs/quick-start.md).

## Built-In Skills

- **`skill-installer`** — Imports business skills from local paths, Git repos, or GitHub tree URLs. This is the primary installer skill (exposed in Step 2 above).
- **`self-installer`** *(deprecated)* — Kept for legacy compatibility. For manager installation, give the agent the GitHub URL directly (see Quick Start Step 1).

## CLI Reference

| Group | Commands |
|---|---|
| **Skill** | `import`, `remove`, `update`, `source list/show` |
| **Registry** | `build`, `doctor` |
| **Profile** | `list/show/add/update/clone/rename/validate/remove` |
| **Sync** | `sync --dry-run`, `doctor` |
| **Query** | `scan`, `ls`, `find`, `audit` |
| **Agent** | `agent detect`, `install-state show/record` |

Most commands support `--json` for machine-readable output. Full examples: [docs/quick-start.md](docs/quick-start.md). JSON schemas: [docs/schema/json-output.md](docs/schema/json-output.md).

## Status

**Current**: Local-first CLI MVP with full skill lifecycle (import/remove/update), profile management, sync, and audit.

**Roadmap**:
- [x] Core CLI (init, import, registry, profiles, sync, doctor)
- [x] Agent-driven install flow (skill-installer + self-installer)
- [x] Remote skill caching and source metadata tracking
- [ ] Windows symlink support testing
- [ ] TUI for interactive profile management
- [ ] Web UI for vault browsing

## Contributing

PRs welcome. Fork → branch → run `PYTHONPATH=src python3 -m unittest discover -s tests` → submit.

## License

[Apache License 2.0](LICENSE)
