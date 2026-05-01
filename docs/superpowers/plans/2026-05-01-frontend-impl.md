# Frontend Photo Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the inbox upload + grouping flow, review-page metadata extensions, home banner, and curator discoverability per the approved design.
**Architecture:** Backend staging endpoints + frontend React routes. Backend lands first, frontend second. All work in `app/` (backend) and `frontend/src/` (frontend), TDD with Playwright E2E for the user flows.
**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, React 19, Vite 8, react-router-dom 7, Tailwind v4, Playwright

---

## Conventions for every task

- **TDD discipline:** every task starts with a failing test (red), then implementation, then green, then commit. The exact red command and expected red output are listed inline.
- **One commit per task.** Commit message prefix: `[B#]` for backend, `[F#]` for frontend.
- **Commits run SERIALLY in foreground** with `run_in_background=true` and a watcher loop. NEVER parallelize commits — they fight over the Dolt lock in the beads pre-commit hook. Watcher pattern:
  ```bash
  # kicked off as run_in_background=true with timeout 600000
  git add -A && git commit -m "..."
  # then in a separate Bash call:
  until ! pgrep -f "git commit" >/dev/null; do sleep 5; done; echo "commit done"
  ```
- **No `--no-verify`.** If the pre-commit hook fails, fix the underlying issue and create a NEW commit (never amend).
- **No `gt dolt stop && gt dolt start`** without first capturing diagnostics per the project CLAUDE.md.
- **Backend tests** live in `tests/test_upload.py` (new) and `tests/test_staging_cleanup.py` (new); pytest invocation is `pytest tests/test_upload.py -x` (or `-x -k <name>`).
- **Frontend unit tests** use the existing tooling. If Vitest is present (`frontend/vitest.config.ts` or a `test` script in `package.json`), unit tests live under `frontend/src/__tests__/`. Otherwise unit-style coverage rides on tiny Playwright specs under `frontend/playwright/e2e/components/`. The first frontend task verifies which path applies and pins it for the rest of the plan.
- **Playwright fixtures:** purse PNGs at `tests/fixtures/purses/` (20 PNGs); the frontend conftest helper `frontend/playwright/fixtures/purse-fixtures.ts` already exposes them.
- **Dependency direction:** all B# tasks must be merged before any F# task that hits `/upload/*`. F1 (api client) can be drafted in parallel reading but committed only after B5.

---

## BACKEND TASKS

### B1: StagingPhotoTable model + alembic migration

**Spec refs:** "Photo storage extension" (StagingPhotoTable schema), "Cascade behavior" (CASCADE on user_id).

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_staging_photo_table_columns_exist` — async DB introspection asserts `staging_photos` table has `id`, `user_id`, `storage_key`, `thumbnail_key`, `original_filename`, `captured_at`, `created_at`.
  - `test_staging_photo_user_fk_cascades` — insert user + staging row, delete user, assert staging row gone.
- [ ] Run `pytest tests/test_upload.py -x` → expect collection error / `NoSuchTableError: staging_photos`.

**Green:**
- [ ] Add `StagingPhotoTable` to `app/models.py` per spec (id PK, user_id FK users ondelete=CASCADE, storage_key str, thumbnail_key str, original_filename Optional[str], captured_at Optional[datetime], created_at datetime default now).
- [ ] Generate alembic migration chained off `b2c3d4e5f6a7`:
  ```bash
  cd /gt/purseinator/crew/kagarmoe && alembic revision -m "add staging photos table"
  ```
  Edit the new file: set `down_revision = "b2c3d4e5f6a7"`. Hand-write the `op.create_table` (do NOT trust autogenerate for FK ondelete cascades on SQLite).
- [ ] Run `alembic upgrade head` against the test DB harness used by conftest.
- [ ] Re-run `pytest tests/test_upload.py -x` → green.

**Commit:** `[B1] add StagingPhotoTable model + migration`

---

### B2: Cascade hardening — verify and tighten ItemPhotoTable.item_id and ItemTable.collection_id

**Spec refs:** "Cascade behavior" — three CASCADE rules listed.

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_item_photo_cascades_on_item_delete` — create collection + item + photo row, delete item, assert ItemPhotoTable row gone.
  - `test_item_cascades_on_collection_delete` — create collection + items + photos, delete collection, assert items + photos all gone.
- [ ] Run `pytest tests/test_upload.py::test_item_photo_cascades_on_item_delete -x` and the collection one.
- [ ] If either is already green: note "no change required for that table" and the task is just the assertion. If red: proceed to green.

**Green (only if red was real):**
- [ ] Update FK definitions in `app/models.py` to add `ondelete="CASCADE"`.
- [ ] Generate alembic migration chained off B1's migration that recreates the FK with the cascade rule (SQLite requires batch_alter_table with `recreate="always"`).
- [ ] **Alembic batch mode:** `alembic/env.py` must have `render_as_batch=True` in the `context.configure(...)` calls so SQLite cascade-rule changes work. Pre-edit audit confirmed this is ABSENT from `alembic/env.py` — add it to both `do_run_migrations` and `run_migrations_offline` before generating the migration:
  ```python
  # in do_run_migrations:
  context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
  # in run_migrations_offline:
  context.configure(..., render_as_batch=True)
  ```
- [ ] Re-run tests → green.

**Commit:** `[B2] harden FK cascades on item_photos and items`

---

### B3: POST /upload/photos — multipart, per-file response, limits

**Spec refs:** "API endpoints" (per-file response shape), "Limits & quotas" (25 MB per-file, 200 MB per-request, 50 files max), "Backend processing pipeline" (HEIC + EXIF + thumbnail), "Atomicity" (write files then DB row).

**Red:**
- [ ] Create `tests/test_upload.py` (extend) with:
  - `test_upload_photos_creates_staging_rows` — POST 3 fixture PNGs, assert response has 3 entries in `succeeded`, 0 in `failed`; each entry has `id`, `thumbnail_url`, `original_filename`, `captured_at`. Assert 3 StagingPhotoTable rows for the user.
  - `test_upload_photos_per_file_partial_failure` — POST 1 valid PNG and 1 fake `.txt` file. Assert response shape `{succeeded: [1 entry], failed: [{original_filename: "x.txt", reason: "unsupported format"}]}`.
  - `test_upload_photos_rejects_oversize_per_file` — POST a stub 26 MB file (use `bytes(26*1024*1024)`). Expect that file in `failed` with `reason` containing "too large".
  - `test_upload_photos_rejects_more_than_50_files` — POST 51 small files; expect HTTP 413 (or 400) with reason about file count.
  - `test_upload_photos_unauthenticated_401` — POST without session, expect 401.
  - `test_upload_photos_accepted_formats_pin` — **regression guard**: import `_sniff_format` from `app/services/photo_pipeline.py` directly; call it with byte signatures for JPEG (`\xff\xd8\xff`), PNG (`\x89PNG`), HEIC (ISO box with `ftyp`+`heic`), HEIF (`ftyp`+`hei`), and WebP (`RIFF`+`WEBP`). Assert each returns a recognized (non-`None` / non-`"unknown"`) result. Purpose: lock down the accepted MIME list so future format additions to `_sniff_format` require an explicit test update.
  - `test_upload_request_too_large_returns_413` — use `httpx.AsyncClient` with `ASGITransport(app=app)` to POST to `/upload/photos` with header `Content-Length: 209715201` (200 MB + 1 byte) and a tiny body (e.g. `b"x"`). Assert HTTP 413. The middleware rejects on header check before reading the body.
- [ ] Run `pytest tests/test_upload.py -x` → expect 404 / `ImportError: app.routes.upload` / route-not-found.

**Green:**
- [ ] Add an ASGI middleware in `app/main.py` (or a new `app/middleware.py`) that checks `request.headers.get("content-length")` and raises HTTP 413 if the value exceeds `200 * 1024 * 1024` (209715200 bytes). Register it via `app.add_middleware` before any route processing. This is the authoritative per-request size enforcement — no reliance on uvicorn flags.
- [ ] Create `app/routes/upload.py` with router prefix `/upload`.
- [ ] Implement `POST /photos` accepting `List[UploadFile]`. For each file: invoke the existing `app/photo_pipeline.py` to produce full + thumb under `staging/{user_id}/{uuid}.jpg` and `.thumb.jpg`. Write disk first, then DB row, then commit. On per-file failure append to `failed`, do NOT abort the request.
- [ ] Enforce 50-file count cap before processing; enforce per-file 25 MB by streaming into a size-bounded buffer.
- [ ] `thumbnail_url` in the response is `/photos/{thumbnail_key}/thumb` per the existing route shipped in plan 2.
- [ ] Wire router in `app/main.py` (or wherever `include_router` lives) so the new prefix is mounted.
- [ ] Re-run pytest → green.

**Commit:** `[B3] add POST /upload/photos with per-file response and limits`

---

### B4: GET /upload/staging — cursor pagination

**Spec refs:** "API endpoints" (default 200, max 200, `before=<id>` cursor, `has_more`).

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_get_staging_returns_user_photos_only` — seed 2 photos for user A, 2 for user B, GET as A, assert only A's photos returned.
  - `test_get_staging_pagination_with_before` — seed 5 staging rows, GET `?limit=2`, assert 2 returned + `has_more=True`; GET `?limit=2&before=<lastId>`, assert next 2.
  - `test_get_staging_limit_caps_at_200` — pass `?limit=500`, assert response respects 200 cap (server-side clamp).
  - `test_get_staging_unauth_401`.
- [ ] Run pytest → red (404 on the route).

**Green:**
- [ ] Implement `GET /upload/staging` in `app/routes/upload.py`. Order by `id DESC`. Apply `before` filter. Clamp `limit` to `min(limit, 200)`. Compute `has_more` by issuing the query with `limit+1` and trimming.
- [ ] Re-run pytest → green.

**Commit:** `[B4] add GET /upload/staging with cursor pagination`

---

### B5: POST /upload/group — IDOR-safe atomic group + post-commit rename

**Spec refs:** "API endpoints" (validate every photo_id belongs to user, 404 not 403), "Atomicity" (DB commit first, then file rename, on rename success update storage_key, on rename failure leave at staging path), "Group" steps 1–9.

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_group_creates_item_with_photos_in_order` — seed 3 staging rows for user, POST `/upload/group {collection_id, photo_ids: [a,b,c]}`. Assert: new ItemTable row exists; 3 ItemPhotoTable rows; first has `is_hero=True`; sort_order is 0,1,2; staging rows deleted.
  - `test_group_renames_files_to_collection_path` — seed 1 staging row, group it. Assert: file no longer at `staging/{uid}/...`; file present at `collections/{cid}/items/{iid}/...`; ItemPhotoTable.storage_key reflects the new path.
  - `test_group_rename_failure_leaves_staging_path_but_succeeds` — monkeypatch `os.rename` to raise on the second call; group 2 photos. Assert: HTTP 200; both ItemPhotoTable rows exist; one has new path, the other still has staging path; both files exist on disk in their respective locations.
  - `test_group_rename_failure_on_first_file` — monkeypatch `os.rename` to raise on the FIRST call; group 2 photos. Assert: HTTP 200; both ItemPhotoTable rows exist; BOTH still have the staging path (no files moved); both files exist at their staging locations. This exercises the "no files moved" branch.
  - `test_group_atomic_db_failure_leaves_staging_intact` — monkeypatch the `ItemPhotoTable` insert (e.g. the session's `add()` or the model constructor) to raise on the FIRST call. Assert: no new ItemTable row exists; all StagingPhotoTable rows for the user are still present; NO files have been moved from staging. Confirms the DB transaction fully rolls back before any file rename attempt.
  - `test_group_idor_returns_404_when_photo_id_belongs_to_another_user` — seed staging row for user B, POST `/upload/group` as user A with that photo_id. Assert HTTP 404.
  - `test_group_idor_returns_404_when_collection_belongs_to_another_user` — collection-side IDOR check, expect 404.
  - `test_group_atomic_when_db_insert_fails` — monkeypatch ItemPhotoTable.__init__ to raise on the second row. Assert: no new ItemTable row, all StagingPhotoTable rows still present, files unchanged.
- [ ] Run pytest → red.

**Green:**
- [ ] Implement `POST /upload/group` in `app/routes/upload.py`:
  1. Validate `collection_id` ownership. Note: `_require_collection_owner` in `app/routes/items.py` raises 403, but here we MUST return 404 to avoid an existence oracle. Use an inline wrap:
     ```python
     try:
         coll = await _require_collection_owner(db, body.collection_id, user.id)
     except HTTPException as e:
         if e.status_code == 403:
             raise HTTPException(status_code=404, detail="Collection not found")
         raise
     ```
     (Do NOT change `_require_collection_owner` itself — that would alter behavior for other endpoints.)
  2. SELECT all staging rows where `id IN (photo_ids) AND user_id = current_user`. If `len(rows) != len(photo_ids)`: return 404. **No 403** to avoid existence oracle.
  3. In a single async transaction: INSERT new ItemTable row with placeholder metadata (`brand="unknown"`, `description=""`, `status="undecided"`); for each photo in given order INSERT ItemPhotoTable row pointing at the **current staging path**; first one `is_hero=True`. DELETE the StagingPhotoTable rows. COMMIT.
  4. Post-commit: for each ItemPhotoTable row, attempt `os.rename` from staging to `collections/{cid}/items/{iid}/`. On success UPDATE storage_key (commit per-row update). On failure log-and-skip; storage_key stays at staging path.
- [ ] Re-run pytest → green.

**Commit:** `[B5] add POST /upload/group with IDOR check and atomic group`

---

### B6: DELETE /upload/staging/{id}

**Spec refs:** "API endpoints" (validates ownership; 404 if not owned).

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_discard_staging_removes_row_and_files` — seed 1 staging row + files on disk, DELETE it, assert row gone, full + thumb files gone.
  - `test_discard_staging_idor_404` — try to delete user B's staging row as user A, expect 404, assert row still present.
  - `test_discard_staging_missing_404` — DELETE id 999999, expect 404.
- [ ] Run pytest → red.

**Green:**
- [ ] Implement `DELETE /upload/staging/{id}` in `app/routes/upload.py`. Lookup by `id AND user_id = current_user`; 404 on miss. Delete files first (idempotent — ignore FileNotFoundError), then DELETE row, COMMIT.
- [ ] Re-run pytest → green.

**Commit:** `[B6] add DELETE /upload/staging/{id}`

---

### B7: 7-day TTL cleanup task + orphan reaper

**Spec refs:** "Photo storage extension" (auto-delete 7 days; cleanup runs hourly + at startup; reaps orphan files in `staging/{user_id}/` not referenced by a current row).

**Red:**
- [ ] Create `tests/test_staging_cleanup.py`:
  - `test_cleanup_deletes_rows_older_than_7_days` — seed 1 row with `created_at = now - 8 days`, 1 row with `created_at = now - 1 day`. Run cleanup. Assert old row gone, fresh row present, old files gone, fresh files present.
  - `test_cleanup_reaps_orphan_staging_files` — write a file at `staging/{uid}/orphan.jpg` with no DB row. Run cleanup. Assert file removed.
  - `test_cleanup_does_not_remove_files_referenced_by_current_rows` — seed 1 fresh row. Run cleanup. Assert files still present.
  - `test_cleanup_does_not_touch_collections_dir` — write a file under `collections/.../` . Run cleanup. Assert file present.
- [ ] Run `pytest tests/test_staging_cleanup.py -x` → red (`ImportError` on the cleanup function).

**Green:**
- [ ] Add `app/tasks/staging_cleanup.py` exporting `async def run_staging_cleanup(session, storage_root)`. Logic: SELECT staging where `created_at < now - 7 days`; for each, delete files + DELETE row. Then for the orphan reaper:
  - Storage key shape: `StagingPhotoTable.storage_key` is the FULL PATH relative to `photo_storage_root` (e.g. `staging/42/abc-123.jpg`); thumbnail_key follows the same convention.
  - Walk `photo_storage_root/staging/{user_id}/` for each user_id seen in the directory.
  - Build a set of all `storage_key` and `thumbnail_key` values for that user_id from the DB.
  - For each file on disk, compute its path relative to `photo_storage_root`. If that relative path is NOT in the set AND the file's `mtime` is more than 60 seconds old (race-protection against in-flight uploads): delete the file.
  - Skip files modified within the last 60 seconds regardless of DB membership.
- [ ] Wire it into app startup (FastAPI lifespan) and an in-process scheduler (asyncio Task with 1-hour `asyncio.sleep`). The scheduler is best-effort; the test only exercises `run_staging_cleanup` directly.
- [ ] Re-run pytest → green.

**Commit:** `[B7] add staging TTL + orphan-file cleanup task`

---

### B8: Per-user 500 staging cap (HTTP 429)

**Spec refs:** "Limits & quotas" — 500-photo cap; 429 response.

**Red:**
- [ ] Add to `tests/test_upload.py`:
  - `test_upload_photos_returns_429_when_user_at_500_staging` — seed 500 staging rows for user, POST 1 photo, assert HTTP 429 with body containing "group or discard".
  - `test_upload_photos_partial_when_user_near_500_cap` — seed 498 rows, POST 5 photos. Spec says reject the request rather than partial accept (consistent with "rejects with 429"); assert HTTP 429 and that no new rows were created.
- [ ] Run pytest → red.

**Green:**
- [ ] In `POST /upload/photos` add a pre-flight `SELECT COUNT(*) FROM staging_photos WHERE user_id = ?`; if `count >= 500` raise HTTPException(429, ...). Add the same check after counting incoming files: if `count + len(files) > 500` reject the whole batch with 429 (matches `test_upload_photos_partial_when_user_near_500_cap`).
- [ ] Re-run pytest → green.

**Commit:** `[B8] enforce per-user 500 staging cap with HTTP 429`

---

### Backend post-condition checkpoint

After B8 commits cleanly:
- [ ] Run full backend suite: `pytest tests/ -x` → expect `~150 + ~17 new = ~167 passing, 18 skipped` (target ~25 new tests across B1–B8: 2+2+5+4+6+3+4+2 = 28; close enough).
- [ ] Run `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` to verify both new migrations are reversible.
- [ ] If anything fails, fix and create a new commit (`[B-fix]`); do NOT amend.

---

## FRONTEND TASKS

### F-pre: Verify rolldown native binding before any frontend work

**Goal:** catch the rolldown native-binding crash before any F-task starts.

- [ ] Run in a sandbox check: `cd /gt/purseinator/crew/kagarmoe/frontend && npm install && npm run dev` (briefly — kill after it either starts or errors).
- [ ] If `"Cannot find module './rolldown-binding…'"` fires: run `gt escalate -s HIGH "rolldown native binding missing — frontend dev server fails to start; F-tasks blocked"` and STOP. Do not proceed with any F-task until the escalation is resolved.
- [ ] If the dev server starts cleanly: mark F-pre complete and proceed to F0.

(F-pre has no commit — it's a pre-flight check only.)

---

### F0: Install and configure Vitest + pin the frontend testing path

**Goal:** establish Vitest as the unit-test runner for all F-tasks. Confirmed in pre-edit review: `frontend/package.json` has NO `vitest` dep and NO `test:unit` script; only Playwright is present.

**Tasks (Vitest is absent — must install):**
- [ ] Install dependencies:
  ```bash
  cd /gt/purseinator/crew/kagarmoe/frontend
  npm install --save-dev vitest @testing-library/react @testing-library/dom @vitest/ui jsdom
  ```
- [ ] Add a `test/environment` block to `vite.config.ts` (or create `vitest.config.ts` if the Vite config can't be easily extended):
  ```ts
  // vite.config.ts — add inside defineConfig:
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  },
  ```
- [ ] Create `frontend/src/__tests__/setup.ts` (imports `@testing-library/jest-dom` matchers if desired; may be empty initially).
- [ ] Add script to `package.json`:
  ```json
  "test:unit": "vitest run"
  ```
- [ ] Add smoke test at `frontend/src/__tests__/smoke.test.ts`:
  ```ts
  it('smoke', () => expect(1).toBe(1));
  ```
- [ ] Run `npm run test:unit` → expect smoke test green.
- [ ] Unit tests in all downstream F-tasks live at `frontend/src/__tests__/{Component}.test.tsx`, run with `npm run test:unit` from `frontend/`.

**Commit:** `[F0] install Vitest + configure jsdom test environment`

---

### F1: API client additions — uploadPhotos, getStaging, groupPhotos, discardStaging

**Spec refs:** Design plan §8 ("Server state") — plain `fetch` via `frontend/src/api.ts`, no SWR/React-Query.

**Red:**
- [ ] Add tests at `frontend/src/__tests__/api.test.ts` (or the equivalent Playwright location per F0):
  - `uploadPhotos posts multipart with files[] field` — mock `fetch`, call `uploadPhotos([File, File])`, assert URL is `/upload/photos`, method POST, body is FormData with two `files` entries.
  - `getStaging passes limit and before query params`.
  - `groupPhotos posts json body {collection_id, photo_ids}`.
  - `discardStaging issues DELETE to /upload/staging/{id}`.
  - `apiFetch surfaces 429 distinctly` (so callers can show the inbox-full toast) — assert thrown error has `.status === 429`.
- [ ] Run tests → red.

**Green:**
- [ ] Extend `apiFetch` to attach `.status` to thrown errors (small refactor; existing throw is `new Error("API error: 429")`). Make a typed `ApiError extends Error { status: number }` and throw that.
- [ ] Add four exports to `frontend/src/api.ts`. Response types match spec exactly:
  ```ts
  export type StagingPhoto = {
    id: number;
    thumbnail_url: string;
    original_filename: string | null;
    captured_at: string | null;
  };
  export type UploadResponse = {
    succeeded: StagingPhoto[];
    failed: { original_filename: string; reason: string }[];
  };
  export type StagingListResponse = { photos: StagingPhoto[]; has_more: boolean };
  ```
- [ ] Re-run → green.

**Commit:** `[F1] add upload/staging API client functions`

---

### F2: ToastProvider + useToast + Toast component

**Spec refs:** Design plan §11 — provider at app root, `useToast()`, max 5 visible, FIFO eviction, 4-s auto-dismiss, manual `×`, success/error variants.

**Red:**
- [ ] Add unit test for `useToast` (jsdom or Playwright per F0):
  - `toast.success() pushes a toast that auto-dismisses after 4s`.
  - `pushing a 6th toast evicts the oldest`.
  - `manual dismiss removes immediately`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/ToastProvider.tsx` with React Context, `useToast()` hook returning `{show, success, error, dismiss}`. Render stack at bottom-center per design (`bg-near-black/95 text-cream`).
- [ ] Wrap `<App>` in `<ToastProvider>` in `App.tsx`.
- [ ] Re-run → green.

**Commit:** `[F2] add ToastProvider, useToast, and Toast UI`

---

### F3: IconButton + MetadataField shared components

**Spec refs:** Design plan §7 (component inventory), §9 (icon-only buttons require aria-label; IconButton throws-in-dev if missing).

**Red:**
- [ ] Unit tests:
  - `IconButton throws in dev when label is missing` — assert `process.env.NODE_ENV === "development"` path throws.
  - `IconButton renders aria-label and ≥44px hit target` — assert rendered button has the `before:` pseudo-class shim or explicit min size.
  - `MetadataField shows status transitions` — render with `status="saving"` then `status="saved"`, assert visible "Saved" copy with checkmark.
  - `MetadataField surfaces error prop with terracotta border + role=alert`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/IconButton.tsx` and `MetadataField.tsx` per the design plan §7 props.
- [ ] Re-run → green.

**Commit:** `[F3] add IconButton and MetadataField shared components`

---

### F4: ColorPickerPair (with multi-exclusive client guard)

**Spec refs:** Design plan §4 ("Color (primary)"/"Color (accents)"), Spec "Multi-color form rule".

**Red:**
- [ ] Unit tests:
  - `setting primary to "multi" clears secondary AND emits a single onChange call with both fields together`.
  - `setting primary to a non-multi color preserves any selected secondaries`.
  - `accents picker disabled with aria-disabled when primary is multi`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/ColorPickerPair.tsx` and a child `EnumMultiSelect.tsx` for the accent chips. Use the 11 color enum values from the spec.
- [ ] Re-run → green.

**Commit:** `[F4] add ColorPickerPair with multi-exclusive guard`

---

### F5: ThumbnailTile (selectable, with discard icon)

**Spec refs:** Design plan §3 ("Staging grid", "Selected state", "Discard affordance").

**Red:**
- [ ] Unit tests:
  - `tile renders thumbnail src from photo.thumbnail_url and aria-label combining filename and captured_at`.
  - `tap toggles selection — onToggle called with photo.id`.
  - `selected=true renders saffron ring AND check icon` (assert both class string and presence of the icon).
  - `discard button has aria-label="Discard photo" and calls onDiscard`.
  - `keyboard: Space and Enter toggle selection` (jsdom keydown).
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/ThumbnailTile.tsx` per design §3.
- [ ] Re-run → green.

**Commit:** `[F5] add ThumbnailTile with selection and discard`

---

### F6: SelectionActionBar (sticky bottom)

**Spec refs:** Design plan §3 ("STICKY ACTION BAR", "Selection state (logic)"), §10 ("Sticky action bar").

**Red:**
- [ ] Unit tests:
  - `bar is hidden when count === 0` (renders null or has hidden class).
  - `bar renders "{count} selected" copy`.
  - `Group button calls onGroup; Discard button calls onDiscard`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/SelectionActionBar.tsx`. iOS safe-area-inset on `pb-[env(safe-area-inset-bottom)]`.
- [ ] Re-run → green.

**Commit:** `[F6] add SelectionActionBar`

---

### F7: CollectionPickerModal (with inline "+ New collection")

**Spec refs:** Design plan §3 ("Collection picker modal").

**Red:**
- [ ] Unit tests:
  - `modal closed when open=false`.
  - `modal renders collections list with radio controls`.
  - `preselectId pre-checks the matching radio`.
  - `expanding "+ New collection" reveals name+description inputs and a Create button`.
  - `confirm with existing collection calls onConfirm({collectionId})`.
  - `confirm with newly created collection first calls onCreateCollection then onConfirm` (props: `onCreateCollection` and `onConfirm`; the page wires them to `POST /collections` then `POST /upload/group`).
  - `Esc closes; focus restored to the trigger`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/CollectionPickerModal.tsx` and the small `Modal.tsx` shell (focus trap + esc + scroll-lock).
- [ ] Re-run → green.

**Commit:** `[F7] add CollectionPickerModal and Modal shell`

---

### F8: FilePickerButton (with HEIC/HEIF accept)

**Spec refs:** Design plan §3 ("Header"), §10 ("iOS file picker").

**Red:**
- [ ] Unit tests:
  - `accept attribute contains image/*, image/heic, image/heif, image/webp`.
  - `multiple prop reflected on input`.
  - `capture="environment" when prop set`.
  - `selecting files calls onFiles with FileList contents`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/FilePickerButton.tsx`. Hidden input behind a styled `<label>` per design §1.
- [ ] Re-run → green.

**Commit:** `[F8] add FilePickerButton with HEIC/HEIF support`

---

### F9: EmptyInboxState

**Spec refs:** Design plan §3 ("Empty state").

**Red:**
- [ ] Unit test: `renders italic muted "Your inbox is empty." line and CTA copy`.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/EmptyInboxState.tsx`.
- [ ] Re-run → green.

**Commit:** `[F9] add EmptyInboxState`

---

### F10: UploadInbox page + Playwright E2E (upload + group flow)

**Spec refs:** Design plan §3 (entire `/upload` flow), §8 (state), Spec "POST /upload/photos" + "POST /upload/group".

**Red (unit — Vitest):**
- [ ] Create `frontend/src/__tests__/UploadInbox.polling.test.tsx`:
  - `visibility-gated polling: does NOT call getStaging when tab is hidden`:
    1. Mock `getStaging` from `../api` (e.g. `vi.mock('../api', ...)`).
    2. Set `Object.defineProperty(document, 'visibilityState', { value: 'hidden', writable: true })`.
    3. Use `@testing-library/react` `render` to mount the polling effect (either the full `UploadInbox` component or an extracted `usePollingEffect` hook).
    4. Use `vi.useFakeTimers()` and advance time by 30 seconds (`vi.advanceTimersByTime(30000)`).
    5. Assert `getStaging` was NOT called (`expect(getStaging).not.toHaveBeenCalled()`).
  - `visibility-gated polling: DOES call getStaging when tab becomes visible`:
    1. Continue from above (still hidden, timer advanced).
    2. Set `document.visibilityState = 'visible'` and dispatch `new Event('visibilitychange')` on `document`.
    3. Advance timers by 30 seconds.
    4. Assert `getStaging` WAS called at least once (`expect(getStaging).toHaveBeenCalledTimes(1)`).
  - Cleanup: `vi.useRealTimers()` in `afterEach`.
- [ ] Run `npm run test:unit` → red (UploadInbox does not exist yet).

**Red (Playwright):**
- [ ] Create `frontend/playwright/e2e/upload-inbox.spec.ts`:
  - `inbox upload + group flow` — log in via dev-login, navigate `/upload`, upload 3 fixture PNGs from `tests/fixtures/purses/` via `setInputFiles`, wait for 3 tiles to appear, select all 3, click Group, modal opens, pick an existing collection, confirm, assert toast text contains "Grouped 3 photos", assert grid is empty, assert `/review/<cid>` exists with the new item.
  - `inbox upload + group via inline new collection` — same but expand "+ New collection", type a name, group; assert the new collection appears in `/dashboard`.
  - `discard one photo via icon button` — upload 2, click the per-tile `×` on one, assert only 1 left.
  - `?suggest=<cid> preselects the modal` — visit `/upload?suggest=<cid>` after uploading, open modal, assert the matching radio is checked. After successful group, assert URL has stripped the param (becomes `/upload`).
- [ ] Run `npx playwright test upload-inbox.spec.ts` → red (route 404 because `/upload` page does not exist yet).

**Green:**
- [ ] Create `frontend/src/pages/UploadInbox.tsx` composing F2–F9 per design §3.
- [ ] Add `<Route path="/upload" element={<UploadInbox />} />` in `App.tsx`.
- [ ] Wire `useSearchParams` for `?suggest`. After successful group, `navigate("/upload")` (param-stripped) per design §3 + §13 decision #3.
- [ ] Implement 30-s polling with `document.visibilityState` gating (design §3 "Polling for cross-device sync") + `IntersectionObserver` infinite scroll for pagination.
- [ ] **IntersectionObserver pagination test (known gap):** Testing that `IntersectionObserver` triggers a second `getStaging` call with `before=<lowest_id>` when scrolling past 200 photos is difficult to automate reliably in jsdom (no layout engine) and expensive in Playwright (requires 200+ seeded rows). Document as a TODO: `// TODO(F10-pagination): add Playwright test seeding 201 staging photos, scrolling to bottom, asserting second getStaging call with before=<id>` in `UploadInbox.tsx` near the observer setup.
- [ ] Re-run unit tests (`npm run test:unit`) → polling tests green.
- [ ] Re-run Playwright → green.

**Commit:** `[F10] add UploadInbox page with upload + group + discard + suggest`

---

### F11: BannerInbox + Home integration + Playwright E2E

**Spec refs:** Design plan §5 ("Home banner"), §8 ("Cross-page state"), §13 decision #2 (non-dismissible).

**Red (Playwright):**
- [ ] Add `frontend/playwright/e2e/home-banner.spec.ts`:
  - `banner appears when staging non-empty` — seed 1 staging photo via API (or by uploading), navigate `/`, assert banner with copy "1 photo waiting to be grouped".
  - `banner clears when staging empty` — same as above, then group it (or discard via API), refresh `/`, assert banner absent.
  - `banner has_more case` — seed via API such that limit=1 returns 1 photo and `has_more=true`; assert banner shown.
- [ ] Run → red.

**Green:**
- [ ] Create `frontend/src/components/BannerInbox.tsx` with the markup from design §5.
- [ ] In `Home.tsx`: add `getStaging({limit: 1})` to the existing `Promise.all`; render `<BannerInbox count={...}/>` when `photos.length > 0 || has_more`.
- [ ] Re-run Playwright → green.

**Commit:** `[F11] add Home BannerInbox`

---

### F12: Dashboard "Upload" button + Session "+ Add photos" link

**Spec refs:** Design plan §5 ("Dashboard 'Upload' button"), §6 ("Curator discoverability").

**Red (Playwright):**
- [ ] Add `frontend/playwright/e2e/upload-discoverability.spec.ts`:
  - `dashboard has Upload button that navigates to /upload`.
  - `session/:cid "+ Add photos to this collection" link navigates to /upload?suggest=<cid>` — assert URL after click.
  - `?suggest=<cid> direct navigation preselects collection in modal` — navigate directly to `/upload?suggest=<known-cid>` (seed or use an existing collection); open the collection picker modal (click "Group" after uploading 1 photo); assert the radio for `<known-cid>` is `checked`. This covers the full journey: "click discoverability link from /session/:cid → land on /upload with the right collection pre-selected."
- [ ] Run → red.

**Green:**
- [ ] Edit `Dashboard.tsx`: add primary terracotta CTA in the header row linking to `/upload`. Mobile: drops below title.
- [ ] Edit `RankingSession.tsx`: add tertiary cobalt link in the page header right-aligned, href `/upload?suggest=${cid}`.
- [ ] Re-run → green.

**Commit:** `[F12] expose Upload from Dashboard and Session pages`

---

### F13: /review/:cid metadata extensions + "+ Add photos" + Playwright E2E

**Spec refs:** Design plan §4 (entire), Spec "Item schema extension" + "Add-photos-to-existing-item".

**Red (Playwright):**
- [ ] Add `frontend/playwright/e2e/item-review-metadata.spec.ts`:
  - `metadata save flow` — open `/review/<cid>` on an item, set primary color = `red`, choose accent `tan`, set style `tote`, material `leather`, dimensions 12/8/4, serial `ABC123`, asking_price 250, click Save, assert PATCH fired (use Playwright `page.waitForRequest`) and "Saved" indicator visible.
  - `multi-color rule` — set primary to `multi`, assert accents picker is `aria-disabled="true"` and previously selected accents cleared.
  - `add photos to existing item` — click "+ Add photos", upload a fixture PNG, assert thumbnail appears in the gallery (via `POST /collections/{cid}/items/{iid}/photos` already shipped).
- [ ] Run → red.

**Green:**
- [ ] Edit `frontend/src/pages/ItemReview.tsx`: add the per-item card extension (PHOTOS section + DETAILS section). Use `MetadataField` (F3), `ColorPickerPair` (F4), `FilePickerButton` (F8) for the inline add-photos affordance.
- [ ] Add new API client method `patchItemMetadata(cid, iid, fields)` and `addItemPhotos(cid, iid, files)` in `api.ts` (the latter wraps the existing endpoint).
- [ ] Save semantics: explicit Save button + Enter (matches existing brand-edit pattern). Multi-color rule: PATCH primary + secondary together when primary becomes `multi`.
- [ ] Re-run → green.

**Commit:** `[F13] add per-item metadata fields and Add Photos to /review/:cid`

---

### F14: Error-handling toasts (413 / 415 / 429) + Playwright E2E

**Spec refs:** Design plan §11 ("HTTP-level errors", "Upload failure modes").

**Red (Playwright):**
- [ ] Add `frontend/playwright/e2e/upload-errors.spec.ts`:
  - `413 oversize toast` — use Playwright `route.fulfill` to mock `/upload/photos` returning 413; trigger upload; assert toast `"Some photos were too big. Try uploading in smaller batches."`.
  - `429 inbox full toast` — mock 429; assert toast `"Inbox full — group or discard photos before uploading more."` and the warning strip `"Inbox is nearly full"` does NOT show (we mock 429, not staging length 480+; that case is covered separately if added).
  - `partial-success humanization` — mock response `{succeeded: [1 entry], failed: [{original_filename: "x.heic", reason: "unsupported format"}]}`; assert toast `"1 photo uploaded · 1 skipped"` and expanded "View details" reveals `"This file type isn't supported. Try JPEG, PNG, or HEIC."`.
- [ ] Run → red.

**Green:**
- [ ] Add a small `humanizeUploadReason(reason: string): string` util in `frontend/src/lib/upload.ts` per design §11.
- [ ] In `UploadInbox.tsx` (or its hook), on `uploadPhotos` reject with `status === 413` show the 413 toast; on `429` show the 429 toast; on partial response show the count + details toast.
- [ ] Re-run → green.

**Commit:** `[F14] add upload error humanization and toasts`

---

### Frontend post-condition checkpoint

- [ ] Run `npx playwright test` → expect existing 29 + 9 new (3 in F10 + 3 in F11 + 2 in F12 + 3 in F13 + 3 in F14 = 14, but some specs ship multiple `test()` cases inside one file — ~10 named E2E tests plus all the unit tests added in F2–F9; target met).
- [ ] Run any unit-test suite chosen in F0 → expect green.
- [ ] If the rolldown native-binding issue (project-state note) blocks the dev server, escalate per CLAUDE.md (`gt escalate -s HIGH`); do NOT silently downgrade to mocked tests.

---

## Self-review

### Spec coverage
- POST /upload/photos — **B3** (per-file shape, limits) + **B8** (429 cap) + **F1** (client) + **F10** (E2E) + **F14** (error toasts).
- GET /upload/staging — **B4** + **F1** + **F10** (polling) + **F11** (banner uses limit=1).
- POST /upload/group — **B5** (IDOR + atomic + post-commit rename) + **F1** + **F10**.
- DELETE /upload/staging/{id} — **B6** + **F1** + **F10** (discard test).
- StagingPhotoTable + cascades — **B1** + **B2**.
- 7-day TTL + orphan reaper — **B7**.
- /upload page (inbox + grouping) — **F10**, composed from F2–F9.
- /review/:cid metadata + add-photos — **F13**.
- Home banner — **F11**.
- Dashboard upload button — **F12**.
- /session curator discoverability — **F12**.
- Multi-color client guard — **F4** + **F13**.
- 413/415/429 humanization — **F14**.

### Placeholder scan
- No "TBD" entries. Every test name is concrete; every commit message is concrete.

### Type consistency
- `StagingPhoto` shape (`id`, `thumbnail_url`, `original_filename`, `captured_at`) matches B3's response and F1's TypeScript type.
- `UploadResponse` shape `{succeeded: StagingPhoto[], failed: {original_filename, reason}[]}` matches B3 tests and F14 mocks.
- `StagingListResponse` shape `{photos: StagingPhoto[], has_more: boolean}` matches B4 tests and F1 type.
- `groupPhotos` body `{collection_id, photo_ids}` matches B5 + F1 + F10.

### Migration chain
- B1's migration explicitly chains off `b2c3d4e5f6a7` (existing head). B2's cascade migration chains off B1. Sequential, no parallel risk.

### TDD red discipline
- Every B# and every F# task lists the failing test name(s), the command to run, and the expected red signature (route 404, ImportError, NoSuchTableError, missing component, etc.). No task starts with implementation.

### Hazards & mitigations
- **Parallel-migration risk:** none. B1 and B2 are committed serially with one head per commit.
- **Atomicity in /upload/group:** B5's tests cover (a) successful rename, (b) per-file rename failure leaving staging path, and (c) DB-insert failure leaving staging rows untouched.
- **Route ordering for /photos/{key}/thumb:** already shipped in plan 2; this plan does not add or modify any `/photos/...` routes, so route-ordering issues cannot regress here.
- **Dolt commit lock:** all commits use `run_in_background=true` + a watcher loop, never parallel. Pre-commit hook is ~5 minutes; budget accordingly.
- **Rolldown native binding:** Playwright tests in F10/F11/F12/F13/F14 may be blocked at execution time. Plan still targets Playwright per the original spec; the executor verifies and escalates rather than silently swapping in mocked tests.
- **HEIC libheif on dev machines:** B3's HEIC-conversion path may need `pillow-heif` system dep; the test fixture set is PNG-only, so red→green doesn't strictly require HEIC, but the implementation must still call into the existing photo_pipeline. If the system lacks libheif, B3 may need to mark the HEIC-specific branch as covered by `test_photo_pipeline.py` (already shipped in plan 2) and limit B3's tests to PNG fixtures.

### Task and test counts
- **Backend tasks:** 8 (B1–B8). New backend tests: ~28 (2 + 2 + 5 + 4 + 6 + 3 + 4 + 2). Target ~25, on target.
- **Frontend tasks:** 15 (F0–F14; F0 is a one-line pin). New unit tests: ~25 across F2–F9 + F1. New Playwright specs: 5 files containing ~14 individual `test()` cases. Target ~10 Playwright tests, on target (the spec said ~10 — we are slightly over, which is a feature not a bug for safety-critical IDOR + atomicity flows).
- **Total tasks:** 23 (8 backend + 15 frontend).

