# Installer Skill Design

## Goal

Add a dedicated installer skill that can set up `skill-hub-manager` for users who prefer to install and operate tooling through an agent skill rather than by manually following documentation.

The installer skill must:

- detect the current agent when possible
- infer a likely skills target directory for known agents
- always ask the user to confirm the detected target before syncing
- degrade gracefully to manual target selection when detection fails
- reuse the existing `skill-hub` CLI instead of reimplementing sync logic

## Non-goals

- replacing the `skill-hub` CLI with skill-only behavior
- silently syncing into guessed directories without confirmation
- managing remote distribution or multi-machine sync
- building a GUI installer
- supporting arbitrary unknown agents without either built-in mapping or user confirmation

## Problem

Today the manager is usable, but the user still needs to:

1. understand what the manager does
2. know which target directory an agent reads
3. run the right installation and sync commands manually

That is acceptable for power users, but not ideal for users who primarily work through skills and want the agent to perform the setup for them.

## Design principles

1. The installer skill is an orchestrator, not a second implementation.
2. Detection is advisory only. Confirmation is mandatory.
3. The flow must work for known agents first, then degrade to user-provided targets.
4. The user should see the planned actions before any sync occurs.
5. The resulting system state should remain inspectable through existing manager commands.

## Proposed architecture

### 1. Installer skill

The top-level skill handles:

- user entrypoint
- environment inspection
- agent detection
- target directory suggestion
- plan presentation
- confirmation gate
- execution handoff
- result summary

The skill should not embed the full manager logic in prose or shell snippets beyond orchestration.

### 2. Agent detection helper

A small helper script or command should return structured detection output.

Suggested output shape:

```json
{
  "agent": "codex",
  "detected": true,
  "confidence": "high",
  "target_dir": "/Users/yup/.codex/skills",
  "reason": "known directory mapping"
}
```

Detection sources, in order:

1. explicit agent context if available from runtime
2. previous install records
3. known built-in agent mappings
4. known local directories already present on disk
5. fallback to unknown

### 3. Execution helper

Execution should call the existing manager commands:

- `./bin/skill-hub init`
- `./bin/skill-hub registry build`
- `./bin/skill-hub profile add` or `profile update`
- `./bin/skill-hub sync`
- `./bin/skill-hub profile validate`
- `./bin/skill-hub registry doctor`
- `./bin/skill-hub doctor`

This keeps the installer skill thin and avoids logic drift.

## Agent mapping model

The first version should support a fixed built-in mapping table.

Suggested initial mappings:

- `codex` -> `~/.codex/skills`
- `claude` -> `~/.claude/skills`

This mapping should live in a small data file or helper module so it can be updated without changing the skill body significantly.

If the agent is detected and mapped:

- present the detected target
- explain why it was chosen
- require user confirmation before sync

If the agent is not detected or not mapped:

- explain that no reliable target could be inferred
- ask the user to provide the target directory manually

## Interaction flow

### Phase 1: Detect

The skill inspects the environment and produces:

- detected agent name if available
- confidence level
- suggested target directory if available
- existing manager install state
- existing local vault state

### Phase 2: Present plan

Before any write action, show a plan in plain language.

Example:

```text
Detected agent: codex
Suggested target: ~/.codex/skills
Manager path: ~/skill-hub-manager
Vault path: ~/.skill-hub

Planned actions:
1. Verify or initialize ~/.skill-hub
2. Create or update a profile for codex
3. Build the registry
4. Validate the profile
5. Sync to ~/.codex/skills
6. Run doctor checks
```

### Phase 3: Confirm

Confirmation is mandatory even for high-confidence detection.

Required questions:

- continue with detected target?
- if not, what target should be used instead?

### Phase 4: Execute

After confirmation, run the orchestration steps in order.

Suggested minimum sequence:

1. ensure manager checkout or install path exists
2. ensure local vault root exists
3. resolve the initial skill set for the selected profile
4. ensure profile exists for the detected or selected agent
5. build registry
6. validate profile
7. sync to target
8. run post-sync diagnostics

### Phase 4A: Resolve initial skill set

The installer must define where the initial profile contents come from.

First-version behavior:

- if the target profile already exists, do not replace its existing skills list
- if the target profile does not exist, the installer asks the user to choose the initial skill set

Suggested choices:

1. `all` — include every currently discovered skill in the local vault
2. `selected` — let the user specify a subset of skill names
3. `empty` — create the profile with no skills and stop before sync

Recommended default:

- if the vault already contains skills, default to `all`
- if the vault is empty, default to `empty`

Rationale:

- this makes first install usable without guessing hidden policy
- it avoids silently creating a profile that references unknown skills
- it avoids overwriting an existing curated profile

If `empty` is chosen:

- create the profile
- skip sync
- instruct the user to add skills and rerun the installer or `sync`

### Phase 4B: Ensure manager availability

The installer must also define how `skill-hub-manager` itself is obtained.

First-version behavior:

1. if the current repository already contains `./bin/skill-hub`, reuse it
2. else if a previously configured manager path exists in local install state, reuse it
3. else require the user to provide a local checkout path manually

The first version does not attempt to clone or update the manager repository automatically.

Rationale:

- repository acquisition has network and trust implications
- local checkout reuse is enough for the first guided installer workflow
- this keeps the installer skill focused on setup and sync, not source acquisition

Future versions may add optional repository bootstrap or update flows.

### Phase 5: Summarize

Return a short result summary:

- which agent was installed
- which profile was used
- which target directory was synced
- whether diagnostics passed
- what to do next if any issue remains

## Profile strategy

The installer skill should not try to infer a complex access policy on first install.

Recommended first-version behavior:

- default profile name: same as detected agent, for example `codex`
- if no agent is detected, default profile name: `default`
- create the profile if missing
- if the profile exists, update it rather than replacing it blindly
- never replace an existing profile's skill list without explicit user confirmation

This keeps the initial install path simple and non-destructive.

## State recording

The installer flow should write or update a local record for traceability.

Suggested file:

```text
~/.skill-hub/state/install-targets.json
```

Suggested fields:

- `agent`
- `profile`
- `target_dir`
- `manager_path`
- `installed_at`
- `detection_confidence`
- `detection_reason`

This enables future installer runs to distinguish:

- first install
- reinstall
- repair after drift

## Error handling

### Detection failures

If no agent can be detected:

- do not abort immediately
- ask for a manual target directory
- continue once the user confirms

### Existing target content

If the target directory already exists:

- show that it exists
- continue through `sync` only after user confirmation

### Missing or invalid profile

If the selected profile fails validation:

- show the specific validation issues
- stop before sync

### Empty profile after install choice

If the user chooses to create an empty profile:

- do not call `sync`
- explain that no target projection was created yet
- provide the next command to add skills or update the profile

### Manager not available locally

If no local manager checkout or executable path can be found:

- stop before any setup write
- ask the user to provide a local manager path
- once provided, verify that `bin/skill-hub` exists there before continuing

### Registry drift

If registry drift is detected:

- rebuild registry before sync
- surface the action in the final summary

## Security and safety

- no silent writes into inferred directories
- no deletion beyond existing `sync` symlink cleanup behavior
- all destructive or high-impact steps remain behind the user confirmation gate
- private skill content remains outside the public repository

## Documentation changes

The repository should add:

- an installer skill README or SKILL.md
- a short section in README describing the installer skill workflow
- a quick-start entry for users who prefer installation through skills

## Testing strategy

The first implementation should test:

1. known agent detection
2. install-record precedence over built-in mapping
3. fallback when detection fails
4. confirmation-required flow
5. initial skill set selection
6. manager path reuse and manual manager path fallback
7. profile creation or update
8. sync to chosen target
9. post-sync doctor and validation behavior
10. install record persistence

Prefer testing the helper scripts and orchestration boundaries separately, rather than one large end-to-end shell-only test.

## Recommended implementation order

1. Add agent mapping and detection helper
2. Add install record format and persistence helper
3. Add manager path resolution helper
4. Add initial skill set selection flow
5. Add installer orchestration script
6. Create installer skill wrapper around the script
7. Add docs and examples
8. Add tests

## Recommendation

Implement the installer as a guided orchestration skill with:

- built-in mappings for known agents
- mandatory confirmation before sync
- fallback to manual target input
- reuse of the existing `skill-hub` CLI for all substantive operations

This gives the right balance of automation, safety, and maintainability.
