# Purseinator — Design Document

## Problem

A handbag collector needs to downsize a large collection (200+ items) to free up space and raise money. The emotional difficulty of deciding what to let go is the core barrier. Existing tools (eBay, Poshmark) focus on selling, not on the decision process itself.

## Solution

A web app that frames downsizing as **curation**. The user never clicks "sell" — they identify their favorites through short, fun comparison sessions, and the sell list emerges as a natural byproduct. Everything about the app should feel **cozy** — comfort, not friction.

## Users

| Role | Person | Experience Level | Primary Interface |
|------|--------|-----------------|-------------------|
| Operator | Kimberly | Technical, CLI-comfortable | CLI + web dashboard |
| Curator | Rachel | Non-technical, theater director, phone user | Touch-friendly web UI on phone/tablet |

**Rachel's UX constraints:** Non-technical, dealing with life stress, cold/dry hands. The UI must have large tap targets, high contrast, forgiving touch interactions. If it's more complicated than tapping a photo, it's wrong.

## Core Workflow

1. **Operator photographs items** — Dedicated camera, neon green card placed between each item as a delimiter. 2-3 angles per bag.
2. **Operator ingests photos** — SD card dump → CLI command splits photo stream on card delimiter, creates item records with grouped photos.
3. **Enrichment (async)** — GPU condition estimation on operator's machine. eBay API image + brand search for identification and informal comps.
4. **Operator reviews enrichment** — Web dashboard to approve/edit data (brand, condition score). Enters brand manually when needed ("unknown" is valid).
5. **Curator ranks in short sessions** — Touch-friendly "this or that" pairwise comparisons. 2-5 minute sessions, quit anytime. Elo rating system with adaptive pairing.
6. **Keepers emerge** — Collection displayed sorted by ranking with a movable dividing line. Everything above = keeper, everything below = consider selling. Rachel drags the line wherever she wants.

## Architecture

### System Split

```
Operator's Machine (Linux + GPU)        Deployed Server (single service)
├── CLI (Typer/Click)                    ├── FastAPI backend
├── Photo ingest pipeline               ├── React frontend
├── GPU enrichment pipeline              ├── PostgreSQL
│   └── Condition estimation             ├── Photo storage (filesystem)
└── Pushes data via REST API ──────────► ├── Rachel's ranking UI
                                         ├── Operator dashboard
                                         └── OpenTelemetry → Grafana Cloud
```

### Tech Stack

- **Backend:** FastAPI (Python) — functional style, pure functions for business logic, Pydantic models for data, OOP only where frameworks demand it
- **Frontend:** React — responsive, touch-optimized for phone/tablet
- **Database:** PostgreSQL
- **CLI:** Typer or Click
- **ML/Vision:** PyTorch + OpenCV (local GPU) — condition estimation
- **Auth:** Magic link (email-based, no passwords) + long-lived persistent sessions
- **Photo storage:** Filesystem on the deployed server
- **Monitoring:** OpenTelemetry SDK + Grafana Cloud free tier
- **Deployment:** Single service (backend + frontend + photos), hosting TBD

### API Design

Full API contract designed up front (including V2 endpoints). V2 endpoints are defined but not implemented until needed — avoids rearchitecting later.

**CLI → Server communication:** The operator CLI is a REST client calling the same FastAPI endpoints as the frontend, authenticated with operator role.

**Photo upload:** Multipart batch upload via CLI command `purseinator push <collection_id>`. Uploads all new/changed photos for a collection with progress feedback. Photos stored on the server filesystem using storage keys (e.g., `collections/123/items/456/photo_001.jpg`) — relative keys that work whether serving from filesystem today or object storage later.

### Data Model

Full schema from day one, including V2 fields. Empty columns/tables are cheaper than migrations later.

| Table | Key Fields | Purpose |
|-------|-----------|---------|
| `users` | id, email, name, role (operator/curator) | Auth + role separation |
| `collections` | id, owner_id, name, description, dollar_goal (nullable, V2) | Groups items, powers killer feature |
| `items` | id, collection_id, brand, description, condition_score, status (undecided/keeper/seller) | Core entity |
| `item_photos` | id, item_id, storage_key, is_hero, sort_order | Multiple photos per item |
| `comparisons` | id, collection_id, user_id, item_a_id, item_b_id, winner_id, info_level_shown, timestamp | Every ranking choice logged |
| `elo_ratings` | id, item_id, collection_id, user_id, rating (default 1500), comparison_count | Separate from items for reset/replay. Scoped per user — MVP is single curator per collection, but schema supports multiple. |
| `price_estimates` | id, item_id, source, estimated_value, comps_data, fetched_at | Market data from APIs (V2) |

## Photo Ingest Pipeline

1. Operator shoots with dedicated camera, placing a **neon green card** between each item
2. SD card dumped to local machine
3. `purseinator ingest ./photos/` — OpenCV color thresholding detects the neon green card, splits photo stream into item groups
4. First photo after each card = hero/thumbnail
5. Each group → one `item` record with linked `item_photos`
6. Operator does a quick review pass in the web dashboard: fix any mis-groupings (split/merge), enter brand names ("unknown" is valid)

**Fallback:** When card detection fails (lighting, occlusion), the review UI provides manual split/merge controls for item groups.

**Future:** Phone camera upload, timestamp-gap heuristic as secondary grouping signal.

## Enrichment Pipeline

### MVP

- **Condition estimation:** GPU vision model on operator's machine. Scores wear, scratches, staining. This is the one ML task worth automating — neither the operator nor Rachel are handbag condition experts.
- **Brand/identification:** Manual entry by operator. eBay API image + brand search helps identify unknown items and pulls informal comps.
- **Description:** Deferred to V2.

### Research Track: eBay Dataset

Curate a dataset of completed eBay handbag listings (via eBay Browse API — legal access only) to power future improvements:

- Photos + seller-assigned condition grades + brand/model + descriptions + sold prices
- One dataset could train/improve all four tasks: condition estimation, brand detection, description generation, pricing
- Approach TBD: fine-tuning vs. RAG (retrieve similar listings as context for a local LLM)

This is a significant undertaking. Flagged for research, does not block MVP.

## Ranking System

### Algorithm: Elo with Adaptive Pairing

- All items start at 1500 rating
- K-factor starts at 32, decreases as comparison count grows per item
- Adaptive pairing prioritizes matchups between similarly-rated items

### Convergence: Open Risk

For a 200-item collection (19,900 possible pairs), the number of comparisons needed for a usable full ranking is uncertain. The extremes (clear favorites, clear sellers) will sort quickly, but the middle — where the keeper/seller line lives — requires adequate coverage.

**Required:** Run an Elo simulation with synthetic preferences before launch to determine realistic session counts. Do not promise Rachel a number until this is done.

### Info Escalation

As decisions get harder (Elo gap shrinks), the UI progressively reveals more data. All four tiers are coded from day one; the price tier activates automatically when pricing data exists.

| Elo Gap | Displayed Info | MVP Status |
|---------|---------------|------------|
| > 200 | Photos only | Active |
| 100–200 | + Brand | Active |
| < 100 | + Condition | Active |
| < 50 | + Estimated price | Activates when V2 pricing data exists |

Rachel never configures this — it happens automatically based on the algorithm.

### Session Design

- Session picker: "Quick (2 min)" or "Full (5 min)"
- Can quit anytime within a session
- No session longer than 5 minutes
- Simple UI: two big photos, tap your favorite, next pair
- Progress indicator within session
- "Nice work!" at session end — no data overload
- **Offline resilience:** Comparisons queued locally in the browser, synced when connection returns. Rachel never notices a blip. Sync uses timestamp-ordered replay — for single-curator MVP, conflicts are effectively impossible. Multi-device conflict resolution revisited with multi-curator in V2.

### MVP Actionable Output

After ranking sessions, Rachel sees her collection sorted by Elo rating with a **movable dividing line**. She drags the line to decide where keepers end and potential sellers begin. No dollar amounts, no goal — just "here are your favorites at the top."

## Killer Feature: "Keep the Most, Hit Your Target" (V2)

Available after ranking stabilizes and pricing is populated:

1. Set a dollar goal on the collection
2. App sorts non-keeper items by Elo rating (lowest attachment first), cumulates estimated sale value
3. Draws a line: "Sell these N items → $X"
4. Interactive — drag the line to see tradeoffs
5. Pricing visibility controlled by operator — revealed to curator only when ready

## Lot Optimization (V2)

- **Thematic bundles:** Group by color, size, style, season ("Summer purses")
- **Anchor bundling:** Pair a desirable bag with lower-value items to move inventory
- **Lot pricing:** Bundle value > sum of individual low-value items

Solves the real problem that low-value items aren't worth listing individually.

## Auth & Sessions

- **Magic link:** Rachel receives an email, clicks, she's in. No password to remember.
- **Persistent sessions:** Long-lived cookie per device. Rachel logs in once per device, stays logged in for weeks.
- **Multi-device:** Each device maintains its own session independently. Progress syncs through the database, not the session. She can rank on her phone, then switch to her iPad — both stay logged in.

## Observability

- **OpenTelemetry SDK** in FastAPI
- **Grafana Cloud** free tier (10k metrics, 50GB logs, 50GB traces)
- Key metrics:
  - API response times (is Rachel waiting?)
  - Failed comparisons (did her choice get lost?)
  - Session completion rates (is she finishing or bailing?)
  - Enrichment pipeline status (did GPU jobs finish?)
  - Error rates

## Data Durability

- **Automated PostgreSQL backups.** This is sentimental data — rankings represent emotional decisions that cannot be recreated. Backup frequency and strategy TBD with hosting choice, but this is non-negotiable.

## Interface Boundaries

| Operation | CLI | Web Dashboard |
|-----------|-----|--------------|
| Photo ingest | ✓ | — |
| GPU enrichment | ✓ | — |
| Review/edit items | ✓ | ✓ |
| View progress | ✓ | ✓ |
| Rachel's ranking | — | ✓ |
| Rachel's collection view | — | ✓ |

## MVP Scope

**MVP (v1):**
- CLI: `purseinator ingest` — SD card photo dump, neon green card splitting, manual split/merge fallback
- CLI: `purseinator enrich` — GPU condition estimation
- CLI → Server: REST API (operator-authenticated)
- Web: Rachel's ranking UI — touch-friendly, info escalation (3 tiers), short sessions, Elo, offline resilience
- Web: Movable keeper/seller dividing line on ranked collection
- Web: Operator review dashboard — approve/edit enriched items, split/merge photo groups
- Auth: Magic link + persistent sessions, multi-device
- Database: PostgreSQL with full schema (including nullable V2 fields)
- Photos: Filesystem on deployed server
- Monitoring: OpenTelemetry + Grafana Cloud
- Backups: Automated PostgreSQL backups
- Pre-launch: Elo convergence simulation with synthetic data

**V2:**
- Pre-filter (mark obvious keepers/sellers before ranking)
- eBay API pricing lookup (batch, operator-triggered)
- Info escalation tier 4 (estimated price — activates automatically with data)
- Killer feature (dollar goal + sell line)
- Lot optimization (thematic bundles, anchor bundling)
- Phone camera upload
- Listing export (eBay/Poshmark ready templates)
- Description generation
- eBay dataset research track (condition, identification, description, pricing)

**V3:**
- Multi-curator support (multiple people ranking same collection with negotiation — round-robin, averaged scores, or dispute rounds)

## Design Principles

- **Cozy, not clinical** — everything about the app should feel like comfort, not friction.
- **Curation framing** — never "liquidation." Rachel curates her favorites; the sell list is a byproduct.
- **Separate capture from data entry** — photographer mode and editor mode are different sessions.
- **Operator controls the journey** — pricing, sell suggestions, and features are revealed when the operator decides Rachel is ready.
- **Functional style** — pure functions for business logic, Pydantic models as immutable data, OOP only where frameworks demand it.
- **Dead simple for Rachel** — large tap targets, high contrast, forgiving interactions. Designed for cold, dry hands and a tired mind.
- **Full design, incremental implementation** — schema, API contract, and escalation logic designed complete from day one. V2 features activate when data appears, no rearchitecting.
