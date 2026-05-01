# Purseinator Docker Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clone the gastown source, configure env vars for the purseinator workspace, and get a running Docker container with Gas Town mounted.

**Architecture:** The official gastown Dockerfile builds `gt` from source inside `docker/sandbox-templates:claude-code`. The docker-compose.yml mounts `~/gt` into `/gt` in the container and keeps Dolt on a named Docker volume to avoid macOS VirtioFS corruption. Steps 1-4 are fully automated; steps 5-8 require the user to exec into the container interactively.

**Tech Stack:** Docker Compose, gastown source (Go + make), docker/sandbox-templates:claude-code base image

---

### Task 1: Clone gastown source at v1.0.1

**Files:**
- Create: `~/gastown-docker/` (clone target)

**Step 1: Clone at the matching tag**

```bash
git clone --branch v1.0.1 --depth 1 https://github.com/steveyegge/gastown.git ~/gastown-docker
```

Expected: `Cloning into '/Users/kimberlygarmoe/gastown-docker'...`

**Step 2: Verify the key Docker files are present**

```bash
ls ~/gastown-docker/Dockerfile ~/gastown-docker/docker-compose.yml ~/gastown-docker/docker-entrypoint.sh
```

Expected: all three paths printed, no errors.

---

### Task 2: Write the .env file

**Files:**
- Create: `~/gastown-docker/.env`

**Step 1: Write the .env file**

```
FOLDER=/Users/kimberlygarmoe/gt
GIT_USER=Kimberly Garmoe
GIT_EMAIL=kagarmoe@gmail.com
DASHBOARD_PORT=8080
```

Write this to `~/gastown-docker/.env`.

**Step 2: Verify the values**

```bash
cat ~/gastown-docker/.env
```

Expected: all four lines printed correctly.

---

### Task 3: Build the Docker image

**Files:** (none — Docker build artifacts)

**Step 1: Build from the gastown source directory**

```bash
cd ~/gastown-docker && docker compose build
```

This step takes several minutes on first run. It pulls `docker/sandbox-templates:claude-code`, installs apt packages (git, tmux, gh, etc.), downloads Go 1.25.8, installs beads and dolt, and compiles `gt` via `make build`.

Expected: ends with `=> exporting to image` and `FINISHED`.

**Step 2: Verify the image exists**

```bash
docker images | grep gastown-sandbox
```

Expected: a line showing `gastown-sandbox` (or the image built from the compose file).

---

### Task 4: Start the container

**Files:** (none)

**Step 1: Start detached**

```bash
cd ~/gastown-docker && docker compose up -d
```

Expected: `Container gastown-sandbox  Started`

**Step 2: Verify the container is running**

```bash
docker compose ps
```

Expected: `gastown-sandbox` shows `running` status.

---

### Task 5: Post-start steps (interactive — user does these)

These steps require an interactive terminal inside the container. The Mayor should provide the commands but the user must run them.

**Step 1: Exec into the container**

```bash
docker compose exec gastown zsh
```

**Step 2: Start Gas Town services**

```bash
gt up
```

**Step 3: Authenticate GitHub CLI (interactive)**

```bash
gh auth login
```

Follow the prompts. Choose HTTPS + browser auth.

**Step 4: Authenticate Claude Code (interactive)**

```bash
claude login
```

Follow the prompts to authenticate.

**Step 5: Attach the Mayor**

```bash
gt mayor attach
```

---

## Notes

- The `dolt-data` Docker volume stores Dolt's data separately from the macOS bind-mount — this avoids known VirtioFS fsync corruption on Apple Silicon.
- The purseinator rig will be at `/gt/purseinator/` inside the container since `~/gt` is mounted at `/gt`.
- To stop: `cd ~/gastown-docker && docker compose down` (preserves volumes).
- To fully reset including Dolt data: `docker compose down -v` (destroys `dolt-data` and `agent-home` volumes).
- The `.env` file contains your email — do not commit it to git.
