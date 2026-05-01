# Photo Intake Design

**Goal:** Let users add photos to a collection from a phone (iPhone/iPad) or any device with a file system (Linux SD card via web upload), with a smooth flow for both "one purse at a time" and "I just shot 50 bags, sort them out."

**Status:** Brainstorm complete, ready for plan generation.

---

## Constraints & assumptions

- One photo per item is common today; multi-photo per item is the future state.
- No physical delimiter cards in use; grouping is purely UI-driven.
- iPhone photos are HEIC by default; browsers can't render HEIC natively.
- Both operators (Kimberly) and curators (Rachel) can upload to their own collections.
- All authenticated owners of a collection can add photos to that collection's items.

---

## Item schema extension

`ItemTable` gains fields. All new fields nullable so freshly-grouped items can be saved with placeholder metadata and edited later via the review page.

| Field | Type | Notes |
|-------|------|-------|
| `primary_color` | `Optional[str]` | Enum-validated: `red, yellow, orange, green, blue, violet, white, black, tan, brown, multi` |
| `secondary_colors` | `list[str]` | JSON array; defaults to `[]`; same enum as `primary_color` |
| `style` | `Optional[str]` | Enum: `satchel, saddlebag, duffel, frame, messenger, tote, foldover, barrel, bucket, hobo, baguette, doctor, backpack, clutch, envelope, minaudiere, crossbody, diaper, wristlet, belt-bag` |
| `material` | `Optional[str]` | Enum: `leather, vegan leather, cloth, tapestry, velvet, suede, performance` |
| `width_in` | `Optional[float]` | Inches |
| `height_in` | `Optional[float]` | Inches |
| `depth_in` | `Optional[float]` | Inches; meaningful 0 (e.g., flat clutch) |
| `serial_number` | `Optional[str]` | |
| `asking_price` | `Optional[int]` | USD whole dollars; operator-entered "what I think it'll sell for" |

Existing fields kept as-is: `brand`, `description`, `condition_score` (ML-set), `status` (undecided/keeper/seller).

**Why JSON for `secondary_colors` instead of a join table:** simpler schema, SQLAlchemy 2.0 native support, no second table for a list-of-enums. Querying ("show all bags with tan accents") works in both SQLite and Postgres via JSON operators. If we ever need rich color queries we can migrate to a join table; YAGNI for v1.

**Migration:** Alembic migration adds the columns to `items` table; backfills `secondary_colors` with `[]` literal for existing rows.

**Pricing — coexistence with `PriceEstimateTable`:** `asking_price` (operator's number) is conceptually separate from `PriceEstimateTable` (model's comp-driven estimate). They live in different tables. The review UI shows both side-by-side.

---

## Photo storage extension

`ItemPhotoTable` gains:

| Field | Type | Notes |
|-------|------|-------|
| `captured_at` | `Optional[datetime]` | Extracted from EXIF `DateTimeOriginal` at upload time |

EXIF is otherwise stripped at upload; only `captured_at` survives into our DB.

A new `StagingPhotoTable` holds photos uploaded but not yet assigned to an item. **Inbox model:** staging photos are tied to the user only — not to any collection. The destination collection is chosen at group time, per-group, so one upload session can produce items in multiple collections.

| Field | Type | Notes |
|-------|------|-------|
| `id` | int PK | |
| `user_id` | FK users | Who uploaded; only owner can see/group these |
| `storage_key` | str | Disk path under `photo_storage_root/staging/{user_id}/` |
| `thumbnail_key` | str | 400×400 JPEG thumbnail |
| `captured_at` | datetime nullable | EXIF |
| `created_at` | datetime | Server upload time |

Staging photos auto-delete 7 days after `created_at` (cleanup script run via cron or a startup task).

When a staging photo is grouped into an item, it transitions: a new `ItemPhotoTable` row is created pointing at the same `storage_key`, the `StagingPhotoTable` row is deleted, and the file moves from `staging/{user_id}/` to `collections/{cid}/items/{iid}/` on disk.

---

## Backend processing pipeline

On every photo upload (single-item or batch), the server:

1. Reads file bytes.
2. If HEIC: convert to JPEG via `pillow-heif`.
3. Read EXIF; capture `DateTimeOriginal` if present.
4. Apply EXIF rotation, then strip ALL EXIF.
5. Save full-resolution JPEG to disk.
6. Generate 400×400 max-fit thumbnail JPEG.
7. Insert DB row (either `ItemPhotoTable` for single-item flow, or `StagingPhotoTable` for batch flow).

New backend dependency: `pillow-heif` (small native lib, ARM64/x86_64 wheels available).

Thumbnail format: JPEG for v1. WebP/AVIF is a stretch optimization (saves bandwidth) — flagged but not in v1.

---

## API endpoints

### Single-item upload (existing, extended)

`POST /collections/{cid}/items/{iid}/photos` — already exists. Behavior unchanged from outside; internally now runs through the new pipeline (HEIC, rotate, thumbnail, captured_at).

`GET /photos/{storage_key}` — already exists. Add `GET /photos/{storage_key}?thumb=1` to serve thumbnails. (Or add a separate `/thumbs/{storage_key}` route — implementation detail.)

### Batch staging (user-scoped, inbox model)

`POST /upload/photos` — multipart upload, accepts N files. Stages all of them under the current user. Returns list of staging photo IDs + thumbnail URLs. No collection_id required.

`GET /upload/staging` — list current user's un-grouped staging photos.

`POST /upload/group` — body: `{collection_id: int, photo_ids: [int]}`. Creates a new Item with placeholder metadata in the specified collection (must be owned by current user), attaches the staged photos to it (moves staging → item photos), deletes the staging rows. Returns the new item. Repeat to group remaining staging photos into different items, possibly in different collections.

`DELETE /upload/staging/{id}` — discard a staging photo without grouping.

### Add photos to existing item

`POST /collections/{cid}/items/{iid}/photos` — already exists; same pipeline as above. UI calls it from the item review page.

### Authorization

- `/upload/*` endpoints: must be authenticated; staging photos are scoped to `user_id`.
- `/upload/group`: also verifies the target `collection_id` is owned by the current user.
- `/collections/{cid}/items/{iid}/photos`: existing `_require_collection_owner` pattern.

---

## Frontend routes

### `/upload` — new top-level route (inbox model)

Discoverable from anywhere; not nested inside a collection. Page layout:

**Header section:**
- File picker button: `<input type="file" accept="image/*,image/heic" multiple>` — uploads all selected photos to staging. Optional second button: `capture="environment"` for direct camera capture.
- Status: "X photos staged, Y grouped, Z remaining."

**Staging grid:**
- Loads current user's un-grouped staging photos via `GET /upload/staging`.
- Each photo shows its thumbnail. Tap to multi-select (visual checkmark).
- Photos persist across page reloads — closing the tab and coming back tomorrow shows the same staging grid.

**Group action:**
- "Group as one purse" button — enabled when ≥1 photo selected.
- Tapping it opens a modal: "Which collection?" with a dropdown of the user's collections (and an option to create a new collection inline). Confirm → calls `POST /upload/group` with `collection_id` and selected `photo_ids`. The grouped photos disappear from the staging grid (transitioned to the item).
- Repeat for the next group; can target a different collection each time.

**"Done" / cleanup:**
- No explicit "done" — user navigates away when finished. Un-grouped staging photos persist (auto-deleted at 7-day TTL).
- A "Discard" button per photo (or per multi-selection) calls `DELETE /upload/staging/{id}` to remove unwanted shots without grouping them.

**Single-photo / single-item shortcut:**
- For "I just took one photo of one bag" — same flow: upload one photo → it stages → tap it → "Group as one purse" → pick collection → done. Single-photo case is a degenerate of the multi-photo flow; no special UI needed.

### `/review/:cid` — existing route, extended

Per-item card gains:
- Form fields for all the new metadata (color dropdowns, style/material selects, dimension number inputs, serial_number, asking_price).
- "+ Add photos" button → opens file picker → uploads more photos to this item via the existing `POST /collections/{cid}/items/{iid}/photos` endpoint (bypasses staging — these photos go directly to the existing item).
- Displays existing photos (thumbnails) for the item.

### `/dashboard` — existing route, minor addition

A persistent "Upload" button in the dashboard header → links to `/upload`. The button is visible regardless of which collection is selected, since `/upload` is collection-agnostic.

### `/` (Home) — minor addition

If there are staging photos waiting (`GET /upload/staging` returns >0), show a banner at the top: "X photos waiting in your inbox — finish grouping →" linking to `/upload`. This makes resuming an interrupted batch obvious.

### Mobile UX

- All routes responsive; tap-to-group designed for one-handed phone use.
- File pickers use `<input type="file" accept="image/*,image/heic" multiple>`. iOS will offer Photos library and camera.
- Optionally also expose a "Take photo now" button using `<input ... capture="environment">` to invoke the camera directly.

---

## CLI's place

Keep `purseinator push` for power users with bulk SD-card workflows on Linux. The push client uploads through the same `/photos` endpoint, so it benefits from the new pipeline (HEIC, thumbnail, etc.) automatically.

Deprecate the neon-green delimiter card detection in `purseinator ingest` (`app/ingest/card_detector.py`) — it works, but no one uses it. Leave the code in place for now; remove it in a separate cleanup pass.

---

## Stretch goals (not v1)

- **Auto-grouping** — server clusters staging photos by timestamp + visual similarity, proposes groups, user nudges. Heaviest item; revisit when v1 is shipped.
- **WebP/AVIF thumbnails** — saves ~30% bandwidth. Easy add later.
- **Drag-to-reorder photos** within an item (set hero photo, sort_order). Existing `is_hero` and `sort_order` columns support it; UI work only.
- **Cross-device sync indicator** — show "+3 from your phone" when staging photos arrive from another device on the same account.

---

## Implementation plan structure

This design will produce **5 plans**, sequenced as:

1. **Item schema + review page** — DB migration, Pydantic, review-form fields. No upload UI yet.
2. **Photo pipeline** — backend pillow-heif + rotate + thumbnail + captured_at. Apply to existing `/photos` endpoint.
3. **Inbox upload + staging + grouping** — `StagingPhotoTable` migration, `/upload/*` endpoints, `/upload` route, tap-to-group UI, group-into-collection modal. The single-photo case is a degenerate of this flow (no separate plan needed).
4. **Add-photos-to-existing-item** — `/review/:cid` review-page button + UX.
5. **Home banner / inbox indicator** — small UX nicety: show "X photos waiting" banner on `/` and `/dashboard` when staging is non-empty.

Plans 1 and 2 are independent and can run in parallel. 3 depends on both 1 and 2. 4 depends on 1 and 2 but not 3. 5 depends on 3.

Each plan follows the existing project workflow: TDD throughout, code review at every stage, single-commit per task, verified against the existing 89-test backend baseline + 29-test Playwright baseline.

---

## Open questions answered during brainstorm

- ✅ Tap-to-group, not drag — works on phones.
- ✅ Persistent staging — survives page reload.
- ✅ Auto-group is v2.
- ✅ `multi` is a sentinel + `secondary_colors` list (set up properly now, not later).
- ✅ Float dimensions, integer dollars.
- ✅ Operator-entered `asking_price` separate from ML `PriceEstimateTable`.
- ✅ Both roles can upload.
- ✅ EXIF stripped except `captured_at`.
- ✅ True inbox model: `/upload` is top-level, staging is user-scoped, collection chosen per-group.
