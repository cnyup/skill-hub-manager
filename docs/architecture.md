# Architecture

## Overview

`skill-hub-manager` is a local-first skill control plane.

It separates:

- raw skill content
- searchable metadata
- project or agent visibility rules
- materialized target directories

## Components

### Vault

The private vault stores the real skills once.

Example:

- `/Users/yup/.skill-hub/skills/k8s-finder/SKILL.md`

### Registry

The registry indexes the vault for search, validation, and audit.

### Profiles

Profiles are allowlists that decide which skills are visible to a given project or agent.

### Sync engine

The sync engine turns a profile into symlinks at the target agent path.

## Data flow

1. Scan vault
2. Build registry
3. Resolve profile
4. Sync allowed skills
5. Audit the result

