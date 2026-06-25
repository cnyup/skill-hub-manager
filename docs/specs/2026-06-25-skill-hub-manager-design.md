# skill-hub-manager Design

## Goal

Create a public GitHub-hosted management tool for skills that can serve multiple agents and multiple projects without publishing the user's private skill content.

The system must:

- keep private skills outside the GitHub repository
- support a single source of truth for skills
- avoid duplicated skill copies across projects
- make new project onboarding cheap
- make access control explicit through profiles
- provide clear documentation for setup and ongoing use

## Non-goals

- hosting the user's private skills in GitHub
- building a marketplace
- implementing remote sync between machines
- replacing the underlying agent runtimes
- optimizing for team-wide distribution before the local workflow is stable

## Constraints

1. The public repository may be pushed to GitHub.
2. The user's actual skills must remain in a local directory outside the public repo.
3. The design should be inspired by strong open-source projects without copying their repository layout or depending on them.
4. The repository must include clear onboarding and operational documentation.
5. The first implementation should work on a single machine and use symlinks by default.

## Reference patterns

The design borrows the following ideas from established open-source patterns:

- canonical source plus symlink materialization
- profile-driven agent selection
- registry/index separation from raw content
- audit and doctor commands for consistency checks

## Proposed architecture

### 1. Public control plane repository

This is the GitHub repository. It contains:

- CLI source code
- templates
- example profiles
- schema definitions
- docs
- tests

It does not contain private skills.

### 2. Private skill vault

The private vault is a local directory outside the repository, for example:

- `/Users/yup/.skill-hub/skills`

Each skill is stored once in the vault:

- `/Users/yup/.skill-hub/skills/billing-labeler/SKILL.md`
- `/Users/yup/.skill-hub/skills/k8s-finder/SKILL.md`

The vault is the only source of truth for actual skill content.

### 3. Registry

The registry is a generated or maintained index of the private vault.

It records metadata such as:

- skill name
- local path
- tags
- visibility
- compatibility
- version or revision
- last updated time

The registry exists to support search, validation, and auditing.

### 4. Profiles

Profiles define what a specific project or agent may see.

Examples:

- `global`
- `project-a`
- `project-b`
- `codex-default`
- `claude-default`

Profiles are allowlists, not copies.

### 5. Sync engine

The sync engine reads a profile and materializes the allowed skills into the target agent directory using symlinks by default.

Example target directories:

- `~/.codex/skills`
- `~/.claude/skills`
- `./.skills`

The sync engine must:

- validate that every referenced skill exists in the vault
- reject or warn on missing skills
- remove links that are no longer allowed by the profile
- preserve the source of truth in the private vault

## Repository layout

```text
skill-hub-manager/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── quick-start.md
│   ├── profiles.md
│   ├── migration.md
│   └── security.md
├── examples/
│   ├── registry.example.yaml
│   └── profiles/
│       ├── global.example.yaml
│       └── project-a.example.yaml
├── src/
│   └── skill_hub_manager/
├── tests/
└── templates/
```

## Configuration model

### Registry example

```yaml
skills:
  k8s-finder:
    path: /Users/yup/.skill-hub/skills/k8s-finder
    tags: [infra, kubernetes]
    visibility: private
    agents: [codex, claude]
    version: 3
```

### Profile example

```yaml
name: project-a
agent: codex
skills:
  - billing-labeler
  - k8s-finder
exclude:
  - experimental/*
```

The first version can support an explicit `skills` list only. Pattern-based inclusion and exclusion can be added later if needed.

## CLI surface

The first release should support a small set of commands:

- `skill-hub init`
- `skill-hub scan`
- `skill-hub registry build`
- `skill-hub profile list`
- `skill-hub profile add`
- `skill-hub profile remove`
- `skill-hub sync <profile>`
- `skill-hub doctor`
- `skill-hub audit`
- `skill-hub ls`
- `skill-hub find <query>`

Command intent:

- `init` creates local config folders and default templates
- `scan` discovers skills in the vault
- `registry build` updates the index
- `profile` commands manage allowlists
- `sync` materializes symlinks into a target directory
- `doctor` checks broken links, missing skills, and bad config
- `audit` reports which skills are exposed to each profile
- `ls` lists available registry entries
- `find` searches by name or tag

## Access control model

Use profiles to control visibility.

Recommended layers:

- `public`
- `team`
- `private`
- `experimental`

The public repository can contain:

- example profiles
- templates
- schema documentation

The local machine can contain:

- private profiles
- private vault content

## Documentation requirements

The repository must include explicit documentation for:

- what lives in GitHub and what does not
- how to create a new local vault
- how to add a new skill
- how to add a skill to a profile
- how to sync a profile into an agent directory
- how to onboard a new project
- how to onboard a new agent
- how to update a skill safely
- how to audit broken links and missing files
- how to migrate from the current multi-copy setup

Recommended docs:

- `README.md`
- `docs/quick-start.md`
- `docs/architecture.md`
- `docs/profiles.md`
- `docs/migration.md`
- `docs/security.md`

## Migration strategy

### Phase 1: Stand up the public manager repo

- create the control plane repository
- add docs, templates, examples, and tests
- keep all actual skill content outside the repo

### Phase 2: Move existing skills into the private vault

- collect skills into a single local directory
- generate the first registry
- avoid duplicate copies

### Phase 3: Define profiles

- create a default profile for existing agents
- create project-specific profiles where needed
- keep private profiles outside the public repo

### Phase 4: Enable sync

- sync profiles into agent-specific skill directories
- verify symlink targets
- add a doctor command to keep the system clean

## Risks

### 1. Symlink portability

Some environments may not support symlinks well. The sync engine should keep a copy fallback available, but symlink should remain the default.

### 2. Profile drift

Without audit commands, profiles can diverge from reality. The design must include a doctor/audit workflow from the start.

### 3. Naming confusion

If skill names are inconsistent, profiles become hard to manage. The repo should define naming conventions early.

### 4. Private data leakage

The public repository must never include private skill content. The docs should call this out explicitly and show the recommended local paths.

## Why this design

This design keeps the public GitHub repository clean while still solving the operational problems the user described:

- one canonical skill source
- cheap onboarding
- explicit visibility control
- no repeated manual copying
- no dependency on a third-party skill manager repository

## Next implementation artifacts

After this design is approved, the next step is to create:

- the public repository scaffold
- the local vault bootstrap instructions
- the registry/profile schemas
- the sync and audit command skeletons
- the quick-start and migration docs

