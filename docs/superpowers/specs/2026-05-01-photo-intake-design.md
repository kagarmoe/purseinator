# Photo Intake Design

**Goal:** Let users add photos to a collection from a phone (iPhone/iPad) or any device with a file system (Linux SD card via web upload), with a smooth flow for both "one purse at a time" and "I just shot 50 bags, sort them out."

**Status:** Design complete + reviewed. Ready for plan generation.

---

## Constraints & assumptions

- One photo per item is common today; multi-photo per item is the future state.
- No physical delimiter cards in use; grouping is purely UI-driven.
- iPhone photos are HEIC by default; browsers can't render HEIC natively.
- Both operators (Kimberly) and curators (Rachel) can upload to their own collections.
- All authenticated owners of a collection can add photos to that collection's items.
- **Deployment target:** long-running container (e.g., Fly/Railway/Render/EC2). `pillow-heif` requires `libheif`, which is non-trivial to bundle for Vercel serverless functions. If serverless deploy is ever needed, the photo pipeline becomes a separate worker; v1 assumes a single container.

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

**Migration:** Alembic migration adds the columns to `items` table; backfills `secondary_colors` with `[]` literal for existing rows. **Caveat:** Alembic autogenerate on SQLite for JSON columns sometimes emits `sa.Text()`. Verify the generated migration uses `sa.JSON()` (or equivalent); fix manually if needed.

**Pricing — coexistence with `PriceEstimateTable`:** `asking_price` (operator's number, integer dollars) is conceptually separate from `PriceEstimateTable.estimated_value` (model's comp-driven estimate, float). They live in different tables. The review UI shows both side-by-side; **display rule:** always render as whole dollars (round the model's float to the nearest dollar before display) so the formats match.

**Multi-color form rule:** Selecting `primary_color = "multi"` is mutually exclusive with `secondary_colors`. The UI enforces this by disabling the secondary-colors picker when `multi` is selected, and clearing any previously-set secondary colors. Server-side: Pydantic validator rejects requests where `primary_color == "multi"` and `secondary_colors != []`.

**Enum stability:** color/style/material values are stored as their string literals (`"red"`, `"satchel"`, etc.). Wrap them as Python `Enum` constants in `app/models.py` so display strings can be localized later without DB migration. v1 ships English labels; i18n is out of scope.

---

## Photo storage extension

`ItemPhotoTable` gains:

| Field | Type | Notes |
|-------|------|-------|
| `captured_at` | `Optional[datetime]` | Naive datetime extracted from EXIF `DateTimeOriginal`. EXIF has no timezone; if `OffsetTimeOriginal` is present we apply it and store UTC, otherwise we store the naive value as-is and document the convention. |

EXIF is otherwise stripped at upload; only `captured_at` survives into our DB.

A new `StagingPhotoTable` holds photos uploaded but not yet assigned to an item. **Inbox model:** staging photos are tied to the user only — not to any collection. The destination collection is chosen at group time, per-group, so one upload session can produce items in multiple collections.

| Field | Type | Notes |
|-------|------|-------|
| `id` | int PK | |
| `user_id` | FK users `ondelete=CASCADE` | Who uploaded; only owner can see/group these. CASCADE on user delete. |
| `storage_key` | str | Server-generated UUID-based path under `photo_storage_root/staging/{user_id}/{uuid}.jpg` |
| `thumbnail_key` | str | 600×600 JPEG thumbnail (retina-friendly) |
| `original_filename` | `Optional[str]` | Preserved for UI display only; never used as a path |
| `captured_at` | datetime nullable | EXIF |
| `created_at` | datetime | Server upload time |

Staging photos auto-delete 7 days after `created_at`. Cleanup runs as a background task on a 1-hour cadence (in-process scheduler) and on app startup. The cleanup task deletes both DB rows AND the corresponding files on disk; orphan files left from a crashed transition are also reaped (any file under `staging/{user_id}/` whose name doesn't match a current `StagingPhotoTable.storage_key`).

**Cascade behavior:**
- `StagingPhotoTable.user_id` → `users.id` with `ondelete=CASCADE`. A post-delete hook removes `staging/{user_id}/` from disk.
- `ItemPhotoTable.item_id` → `items.id` with `ondelete=CASCADE`. A post-delete hook removes the file at `storage_key`.
- `ItemTable.collection_id` → `collections.id` with `ondelete=CASCADE` (cascade through to photos via the above).
- v1 may not have admin user-deletion UX, but the migration adds the cascade rules now so the data model is correct from day one.

**Filename collisions are impossible** because the server generates a UUID for each staged or stored photo. The user's original filename (e.g., `IMG_0001.HEIC`) is preserved only in `original_filename` for display.

**Storage layout:**
```
photo_storage_root/
  staging/
    {user_id}/
      {uuid}.jpg          # full-res
      {uuid}.thumb.jpg    # 600×600 thumbnail
  collections/
    {cid}/
      items/
        {iid}/
          {uuid}.jpg
          {uuid}.thumb.jpg
```

---

## Atomicity & failure handling

Operations that touch both disk and DB use this discipline:

**Upload (single-item or staging):**
1. Pillow pipeline runs in memory (no disk write yet).
2. Generate UUIDs for full-res and thumbnail filenames.
3. Write both files to disk (full-res first, then thumbnail).
4. INSERT DB row with the storage keys.
5. COMMIT.
- If step 3 fails: nothing in DB, no orphan to reap (write failed, file may be partial — reaper covers it).
- If step 4 or 5 fails: files exist on disk but no DB row. The hourly reaper sweeps any file under `staging/{user_id}/` not referenced by a `StagingPhotoTable` row.

**Group (staging → item):**
1. Validate ownership of every `photo_id` (see Authorization below).
2. Validate ownership of `collection_id`.
3. Begin transaction.
4. INSERT new `ItemTable` row with placeholder metadata.
5. For each staging photo: INSERT `ItemPhotoTable` row pointing at the **current staging path** (`storage_key` unchanged); set `is_hero=true` for the first one, `sort_order` from 0 onward.
6. DELETE the corresponding `StagingPhotoTable` rows.
7. COMMIT.
8. **After commit:** attempt to rename each file from `staging/{user_id}/{uuid}.jpg` to `collections/{cid}/items/{iid}/{uuid}.jpg`. On success, UPDATE `ItemPhotoTable.storage_key` to the new path.
9. If any rename fails: the file stays at the staging path. The DB row still points at it. The photo is fully functional (no data lost) — it just lives in the staging dir. A periodic reconciliation task can move misplaced files later, or the orphan-reaper leaves files referenced by an `ItemPhotoTable` row untouched.

This way the user-visible operation succeeds atomically at step 7 even if the post-commit moves fail. **No orphan files; no DB rows pointing at missing files.**

**Add-photos-to-existing-item:** runs the upload pipeline directly to the item's directory (skips staging). Same step 1-5 sequence as upload, but writes to `collections/{cid}/items/{iid}/`.

---

## Limits & quotas

**Per-file:**
- Max upload size: 25 MB. Files larger are rejected with HTTP 413.
- Allowed MIME types (sniffed by file extension AND magic bytes, NOT trusting `Content-Type` header — iOS Safari sometimes sends `application/octet-stream` for HEIC): JPEG, PNG, HEIC, HEIF, WebP. Anything else rejected with 415.

**Per-request:**
- Max request body: 200 MB (allows ~50 photos per upload).
- Max files per `POST /upload/photos`: 50.

**Per-user:**
- Max staging photos at any time: 500. Beyond that, `POST /upload/photos` rejects with 429 and a message to group or discard existing staging first.
- No hard byte-quota in v1. If misuse happens we add one. Document this gap explicitly: a single user can fill the disk.

**Photo deduplication:** not implemented in v1. A user re-syncing iCloud will produce duplicate staging rows. Acceptable foot-gun for v1; revisit if it becomes annoying. (Easy add later: SHA-256 hash file bytes; if hash already exists in this user's staging or items, skip.)

---

## Backend processing pipeline

On every photo upload (single-item, batch, or add-to-existing-item), the server:

1. Read file bytes (streaming, capped at per-file size limit).
2. Sniff format by extension + magic bytes. Reject unsupported.
3. If HEIC/HEIF: convert to JPEG via `pillow-heif`. (Source HEIC is **not retained** — accepting lossy re-encode in exchange for half the storage. If users ever need to reprocess from originals, that's a v2 with `original_storage_key` column added.)
4. Read EXIF; capture `DateTimeOriginal` (and `OffsetTimeOriginal` if present) into `captured_at`.
5. Apply EXIF rotation, then strip ALL EXIF.
6. Save full-resolution JPEG to disk under a UUID filename.
7. Generate 600×600 max-fit thumbnail JPEG (retina-friendly; displayed at ≤300 CSS px on 2x screens, ≤200 CSS px on 3x screens).
8. INSERT DB row (either `ItemPhotoTable` for direct flows or `StagingPhotoTable` for batch flow).

New backend dependency: `pillow-heif` (small native lib, requires `libheif`; ARM64/x86_64 Linux wheels ship with it pre-built, macOS via Homebrew).

Thumbnail format: JPEG for v1. WebP/AVIF is a stretch optimization (saves bandwidth) — flagged but not in v1.

**Concurrent uploads:** the API does not hold a global lock. SQLite serializes writes (existing `workers: 1` from the test config; production runs Postgres). Two devices uploading 50 files each in parallel works; UUID filenames eliminate filesystem collisions.

---

## API endpoints

### Single-item upload (existing, extended)

`POST /collections/{cid}/items/{iid}/photos` — already exists. Behavior unchanged from outside; internally now runs through the new pipeline (HEIC, rotate, thumbnail, captured_at). Existing `_require_collection_owner` enforces ownership.

`GET /photos/{storage_key}` — already exists, serves full-resolution image.
`GET /photos/{storage_key}/thumb` — new sub-route, serves the 600×600 thumbnail. (We chose the path-segment style over `?thumb=1` for consistency with REST norms.)

### Batch staging (user-scoped, inbox model)

`POST /upload/photos` — multipart upload, accepts up to 50 files. Response is **per-file**, not all-or-nothing:
```json
{
  "succeeded": [
    {"id": 12, "thumbnail_url": "/photos/abc-123.thumb.jpg/thumb", "original_filename": "IMG_0001.HEIC", "captured_at": "2026-04-30T18:42:00"}
  ],
  "failed": [
    {"original_filename": "broken.jpg", "reason": "unsupported format"}
  ]
}
```
Hostile-network friendly — one bad file doesn't sink the batch.

`GET /upload/staging?limit=200&before=<id>` — list current user's un-grouped staging photos. Default and max limit: 200. Cursor pagination via `before=<staging_id>` returns photos with `id < before`. Response includes a `has_more: bool` flag.

`POST /upload/group` — body: `{collection_id: int, photo_ids: [int]}`.
- **MUST validate** that every `photo_id` in the request belongs to `current_user`. Reject with HTTP 404 (not 403) if any do not — avoids existence oracle.
- **MUST validate** that `collection_id` is owned by current user (existing pattern).
- Creates a new Item with placeholder metadata: `brand="unknown"`, `description=""`, `status="undecided"`, all new metadata fields `NULL`.
- Attaches the staged photos in the order they appear in `photo_ids` (first → `is_hero=true`, then `sort_order` 0..N).
- Returns the new item with photos.

`DELETE /upload/staging/{id}` — discard a staging photo. Validates ownership; 404 if not owned (existence oracle protection).

### Add photos to existing item

`POST /collections/{cid}/items/{iid}/photos` — already exists; same pipeline as the inbox upload but writes directly to the item's directory (no staging).

### Authorization summary

- `/upload/*` endpoints: must be authenticated; staging photos are scoped strictly to `user_id`. Cross-user `photo_ids` in `POST /upload/group` body return 404 (not 403).
- `/upload/group`: also validates `collection_id` ownership.
- `/collections/{cid}/items/{iid}/photos`: existing `_require_collection_owner` pattern.
- `/photos/{key}` and `/photos/{key}/thumb`: open if served as static files (existing behavior). Storage keys are UUIDs, so they're unguessable. **Note:** this is "security through obscurity" for photos — acceptable for v1, but document. Hardening = signed URLs with expiry; out of scope for v1.

---

## Frontend routes

### `/upload` — new top-level route (inbox model)

Discoverable from anywhere; not nested inside a collection.

**Header:**
- File picker: `<input type="file" accept="image/*,image/heic,image/heif" multiple>`. Optional secondary "Take photo now" using `capture="environment"`.
- Status: "X photos staged, Y grouped today, Z waiting."
- Polling: every 30 seconds re-fetches `GET /upload/staging` so a phone-then-desktop flow shows freshly uploaded photos without manual refresh. Uses the `If-None-Match`/etag pattern if implementable; otherwise plain polling.

**Staging grid:**
- Loads via `GET /upload/staging` with pagination (200 per page).
- Each photo: thumbnail (600×600 served, displayed at 150–200 CSS px), tap to multi-select (visual checkmark + colored border).
- ARIA `role="checkbox" aria-checked="true|false"` on each tile; keyboard navigable (arrow keys move focus across the grid, space/enter toggle selection).
- No localStorage caching of photo metadata — each `/upload` page load fetches fresh, so a user logging out and a different user logging in on the same browser sees only their own photos.

**Group action:**
- "Group as one purse" button — enabled when ≥1 selected.
- Modal: "Which collection?" with a dropdown of the user's collections (fetched fresh from `GET /collections` on modal open) + "+ New collection" inline option.
- Confirm → `POST /upload/group`. Grouped photos disappear from the grid. Toast: "Grouped 3 photos into a new purse in Rachel's Collection — Review now?" (links to the new item's review page).

**Discard:**
- Per-photo "discard" or per-multi-select "discard selected" button → `DELETE /upload/staging/{id}`.

**Single-photo flow:**
- Degenerate case of multi: upload one photo → tap → group → done.

### `/review/:cid` — existing route, extended

Per-item card gains:
- Form fields for all the new metadata (color dropdowns with the multi-exclusive rule, style/material selects, dimension number inputs, serial_number, asking_price).
- Display of all photos (thumbnail grid).
- "+ Add photos" button → file picker → uploads to `POST /collections/{cid}/items/{iid}/photos` (skips staging).

### `/dashboard` — existing route

A persistent "Upload" button in the dashboard header → `/upload`. Visible regardless of selected collection.

### `/` (Home) — minor addition

Banner when staging is non-empty: "X photos waiting in your inbox — finish grouping →" linking to `/upload`. Banner is present for both operators and curators.

### `/session/:cid` — minor addition (curator discoverability)

Curators primarily live on `/` and `/session/:cid`. To make uploads discoverable from there, add a "+ Add photos to this collection" link in the page header that routes to `/upload?suggest=<cid>`. The `suggest` query param pre-selects that collection in the group modal but doesn't constrain it.

### Mobile UX

- All routes responsive; tap-to-group designed for one-handed phone use.
- File pickers use `<input type="file" accept="image/*,image/heic,image/heif" multiple>`. iOS will offer Photos library and camera.
- Format detection is server-side (magic bytes); the `accept` attribute is a UX hint only.

---

## CLI's place

Keep `purseinator push` for power users with bulk SD-card workflows on Linux. The push client uploads through the existing `/photos` endpoint, so it benefits from the new pipeline (HEIC, thumbnail, etc.) automatically.

Deprecate the neon-green delimiter card detection in `purseinator ingest` (`app/ingest/card_detector.py`). File a follow-up beads issue to remove it cleanly in a future cleanup pass — keep the code in place for now to avoid scope creep.

---

## Stretch goals (not v1)

- **Auto-grouping** — server clusters staging photos by timestamp + visual similarity, proposes groups. Heaviest item; revisit when v1 ships.
- **WebP/AVIF thumbnails** — saves ~30% bandwidth.
- **Drag-to-reorder photos** within an item (existing `is_hero` and `sort_order` columns support it).
- **Photo deduplication** — SHA-256 file hash per user.
- **Per-user storage byte quota.**
- **Signed photo URLs with expiry** — hardens the "UUID = obscurity" v1 model.
- **HEIC original retention** — keep both HEIC and JPEG (2x storage) for future reprocessing.
- **Accessibility audit** — full keyboard + screen reader pass beyond the v1 baseline.
- **i18n** — color/style/material display strings.

---

## Implementation plan structure

**6 plans.** Plan 1 split into backend (1) and review-page UI (now part of 4) per code review. Plans 3 → 4 → 5 → 6 serialized to avoid frontend merge conflicts.

1. **Item schema (backend only)** — Alembic migration for new `ItemTable` columns (color/style/material/dimensions/serial/asking_price), `secondary_colors` JSON, Pydantic schemas, server-side validators (multi-color rule). No UI in this plan. **Test target:** ~6 new backend tests (migration verification, validator rejections, round-trip serialization).

2. **Photo pipeline (backend only)** — `pillow-heif` dependency, full pipeline (sniff → HEIC convert → EXIF rotate + strip → captured_at extract → thumbnail). New `/photos/{key}/thumb` endpoint. Apply to existing `POST /collections/{cid}/items/{iid}/photos`. **Test target:** ~8 new backend tests (HEIC conversion, EXIF rotation, captured_at extraction, oversize rejection, format sniffing, thumbnail dimensions).

   Plans 1 and 2 are independent and can run in parallel.

3. **Inbox upload + staging + grouping** — `StagingPhotoTable` migration, `/upload/*` endpoints (with all the authorization, pagination, IDOR checks, response shapes from this spec), `/upload` route, tap-to-group UI, group-into-collection modal with inline new-collection creation, discard, 30-sec polling, ARIA + keyboard nav. Atomic group operation per the Atomicity section. Cleanup task (7-day TTL + orphan reaper). **Test target:** ~12 new backend tests, ~4 new Playwright tests.

4. **Review page extensions + Add photos to existing item** — `/review/:cid` form fields for new metadata + "+ Add photos" button. **Test target:** ~3 new backend tests (already covered by plans 1-2 mostly), ~2 new Playwright tests.

5. **Home banner + curator discoverability** — banner on `/` when staging non-empty, "+ Add photos" link on `/session/:cid` with `?suggest=cid` param. **Test target:** ~2 new Playwright tests.

6. **Cascade hardening + cleanup task verification** — explicit tests for `ondelete=CASCADE` and post-delete file cleanup. May be folded into plan 3 if convenient. **Test target:** ~3 new backend tests.

**Acceptance for the whole feature:** baseline goes from 89 backend / 29 Playwright to ~118 backend / ~37 Playwright.

Each plan follows the existing project workflow: TDD throughout, code review at every stage, single commit per task.

---

## Open questions answered during brainstorm + review

- ✅ Tap-to-group, not drag — works on phones.
- ✅ Persistent staging — survives page reload.
- ✅ Auto-group is v2.
- ✅ `multi` is a sentinel + `secondary_colors` list (set up properly now). UI rule: mutually exclusive.
- ✅ Float dimensions, integer dollars (display rule: round both to whole dollars).
- ✅ Operator-entered `asking_price` separate from ML `PriceEstimateTable`.
- ✅ Both roles can upload.
- ✅ EXIF stripped except `captured_at`.
- ✅ True inbox model: `/upload` is top-level, staging is user-scoped, collection chosen per-group.
- ✅ Atomicity: write DB → commit → attempt rename. No orphan files, no dangling DB rows.
- ✅ Cascade: `ondelete=CASCADE` on user FK and item FK; post-delete hooks remove disk files.
- ✅ IDOR on group endpoint: validate every `photo_id` belongs to current user, return 404.
- ✅ Per-file 25 MB limit, per-request 200 MB, max 50 files/request, max 500 staging photos per user.
- ✅ Filename collisions impossible (UUIDs).
- ✅ Format sniffing via magic bytes, not trusting `Content-Type`.
- ✅ Thumbnail size 600×600 (retina-friendly).
- ✅ Pagination on `GET /upload/staging`: 200/page, cursor `before=<id>`.
- ✅ `/photos/{key}/thumb` path-segment style (consistent REST).
- ✅ Placeholder metadata at group: `brand="unknown"`, `description=""`, `status="undecided"`, others NULL.
- ✅ HEIC originals NOT retained (lossy re-encode accepted).
- ✅ Cross-device polling: 30s on `/upload`.
- ✅ Plans re-sequenced: 1+2 parallel, then 3 → 4 → 5 → 6 serial. Review-page UI moved out of plan 1 into plan 4.
- ✅ Test targets explicit per plan; total ~118 backend / ~37 Playwright at completion.
- ✅ Photo dedup deferred to v2 (documented foot-gun).
- ✅ i18n deferred (enums stable as Python constants now).
- ✅ Storage byte quota deferred (documented gap; per-file/per-request/per-user-count limits give first line of defense).
- ✅ Deployment target: long-running container; serverless requires extracting the pipeline to a worker (out of scope).
