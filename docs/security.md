# Security

## Public vs private boundary

The GitHub repository must never contain the user's private skills.

## Recommended private paths

- `~/.skill-hub/skills`
- `~/.skill-hub/profiles`
- `~/.skill-hub/sources`

These are all under the default workspace root and should never be committed.

## Rules

- Do not commit private `SKILL.md` content.
- Do not commit secrets.
- Do not commit generated local vault state.
- Keep private profiles local unless they are purely illustrative.

## Remote Skill Sources

When installing skills from remote repositories:

- Only install skills from sources you trust.
- The installer clones the full repository into the local cache — review the contents before importing.
- Non-`github.com` domains are supported but warrant extra scrutiny.


