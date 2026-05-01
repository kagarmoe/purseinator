# Design: Run Purseinator in Docker via Gas Town Docker Compose

**Date:** 2026-04-30  
**Scope:** Docker Compose setup for the purseinator Gas Town workspace

## Problem

The purseinator rig currently runs on the host macOS machine. Running it in Docker
provides isolation, avoids VirtioFS/Dolt corruption risk, and matches the gastown
reference architecture.

## Architecture

The official gastown Docker Compose setup:
- Builds `gt` from the gastown source repo inside `docker/sandbox-templates:claude-code`
- Mounts the Gas Town HQ (`~/gt`) into `/gt` in the container
- Stores Dolt data on a named Docker volume (not the macOS bind-mount) to avoid fsync corruption
- Exposes the dashboard on port 8080

## Source Location

Clone: `https://github.com/steveyegge/gastown.git` at tag `v1.0.1`  
Target: `~/gastown-docker`

The Dockerfile in that source builds `gt` via `make build`. No pre-built image is published.

## Environment Variables (.env)

```
FOLDER=/Users/kimberlygarmoe/gt
GIT_USER=Kimberly Garmoe
GIT_EMAIL=kagarmoe@gmail.com
DASHBOARD_PORT=8080
```

`FOLDER` mounts the full Gas Town HQ so all rigs (including purseinator) are present at `/gt/`.

## Steps

1. Clone gastown v1.0.1 to `~/gastown-docker`
2. Write `.env` file into the clone directory
3. `docker compose build` (compiles gt, installs beads + dolt in image)
4. `docker compose up -d`
5. User: `docker compose exec gastown zsh`
6. User: `gt up` inside container
7. User: `gh auth login` inside container (interactive)
8. User: `gt mayor attach` inside container

Steps 1-4 are automated. Steps 5-8 require interactive terminal access.

## Volumes

| Volume | Purpose |
|--------|---------|
| `${FOLDER}:/gt` | Gas Town HQ (all rigs, config, hooks) |
| `agent-home:/home/agent` | Agent home (persistent across restarts) |
| `dolt-data:/gt/.dolt-data` | Dolt database (isolated from macOS bind-mount) |

## Post-setup Note

Claude authentication inside the container must be done interactively after
`gh auth login`. The `docker/sandbox-templates:claude-code` base image has
Claude Code pre-installed.
