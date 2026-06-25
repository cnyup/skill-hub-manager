# Migration

## Goal

Move from duplicated skills across multiple projects to a single local vault with profile-driven sync.

## Steps

1. Collect all existing skill copies.
2. Consolidate them into a single private vault.
3. Generate the registry from the vault.
4. Create a default profile for existing agents.
5. Sync the default profile into each target directory.
6. Remove stale duplicate copies once verification passes.

## Safety checks

- Ensure every skill exists in the vault before syncing.
- Verify symlink targets after sync.
- Run audit commands before deleting old copies.

