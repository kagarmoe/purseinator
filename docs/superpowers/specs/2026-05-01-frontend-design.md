# Frontend Design Plan — Photo Intake

**Goal:** Give Kimberly (operator) and Rachel (curator) a one-handed-on-iPhone way to push photos into the inbox, group them into purses, and finish the metadata, without ever leaving the Cabana-magazine feel of the rest of Purseinator.

**Aesthetic:** A continuation of the existing Mediterranean / Cabana editorial palette already declared in `frontend/src/index.css` — `cream` `#FAF3E0` ground, `near-black` `#1A1208` ink, `terracotta` `#C4622D` for primary action, `cobalt` `#1B3F8B` for secondary action, `saffron` `#E8A838` for highlights and selection rings, `dusty-rose` `#D4A5A5` for soft borders/skeletons, `forest` `#3D6B4F` for success states, `muted` `#7a6a58` for subdued copy. Typography is unchanged: Playfair Display (`font-serif`) for titles, Inter (`font-sans`) for body and labels, with the established uppercase `tracking-[0.25em]`/`tracking-[0.2em]` micro-labels on header eyebrows.

**Status:** Design plan ready for first review. No new tech, no new color tokens, additive only.

---

## 1. Aesthetic & Visual Language

### Continuity rules
- **No new color tokens.** Every new surface uses the seven `@theme` colors in `index.css`. If a state needs an "alert red" we instead use `terracotta` at full saturation (it already reads as caution against `cream`); if we need a "warning amber" we use `saffron`; if we need success we use `forest`. We are intentionally not introducing a generic red/green palette — the editorial restraint is the brand.
- **No new fonts and no new font weights** beyond what existing pages use (`font-serif` regular for titles, `font-sans` regular and `font-medium` for body/CTAs).
- **No drop shadows on cards.** Existing pages use `border border-cream` (a near-invisible hairline on `bg-cream`) or `border border-dusty-rose` for soft separation; we preserve that. The Cabana feel is flat, paper-like.
- **No rounded buttons except for the existing pill-shaped dev-login affordance.** All other buttons stay square (no `rounded-*`), matching `Dashboard` and `Home`.
- **Whitespace is the gesture.** New pages keep the `px-6 pt-10 pb-6` header rhythm and `max-w-2xl mx-auto` (or `max-w-lg` on Home) main-column constraint, so `/upload` does not feel like a different application.

### Class palette to use (canonical bindings)
| Role | Tailwind classes |
|---|---|
| Page ground | `bg-cream` |
| Page ink | `text-near-black` |
| Eyebrow micro-label | `text-xs uppercase tracking-[0.25em] text-muted font-sans` |
| H1 title | `font-serif text-3xl text-near-black leading-tight` (page) / `text-4xl`/`text-5xl` (hero) |
| H2 section label | `text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-6` |
| Subdued body | `text-muted text-sm font-sans` |
| Italic empty state | `text-muted text-sm font-sans italic` |
| Card surface (white) | `bg-white border border-cream p-5` |
| Card surface (rose-tinted, clickable) | `bg-dusty-rose/20 border-l-4 border-l-terracotta border border-dusty-rose px-6 py-5 hover:bg-dusty-rose/40 transition-colors` |
| Primary CTA (filled) | `bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer` |
| Secondary CTA (outline cobalt) | `border border-cobalt text-cobalt text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-cobalt hover:text-white transition-colors cursor-pointer` |
| Tertiary / inline link | `text-cobalt underline-offset-4 hover:underline text-sm font-sans` |
| Destructive button | `border border-terracotta text-terracotta text-xs font-sans uppercase tracking-[0.1em] px-3 py-1.5 hover:bg-terracotta hover:text-white transition-colors` (terracotta-as-warning, never solid red) |
| Selected state (thumbnail) | ring + checkmark, see §3 |
| Skeleton block | `bg-dusty-rose/30 animate-pulse` (matches existing Home skeleton) |
| Hairline divider | `border-cream` (or `divide-cream`) |
| Focus ring (keyboard) | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cobalt focus-visible:ring-offset-2 focus-visible:ring-offset-cream` |
| Disabled state | `opacity-50 cursor-not-allowed` |

We bake these as Tailwind class strings; no new components library, no new design tokens.

---

## 2. Routes & Page Structure

### Route table

| Route | New? | Component | Role gating | URL params |
|---|---|---|---|---|
| `/upload` | NEW | `pages/Upload.tsx` | Authenticated; both `operator` and `curator` | optional `?suggest=<cid>` to pre-select a collection in the group modal |
| `/review/:collectionId` | extended | `pages/ItemReview.tsx` | unchanged (operator + curator owners) | `:collectionId` |
| `/` (Home) | extended | `pages/Home.tsx` | unchanged | none |
| `/dashboard` | extended | `pages/Dashboard.tsx` | unchanged | none |
| `/session/:cid` | extended | `pages/RankingSession.tsx` | unchanged (curator-primary) | `:cid` |

### Role gating
- The spec says both operators and curators may upload to collections they own. We do **not** add a `role` check on `/upload`; the existing `_require_collection_owner` server pattern already gates writes. Frontend trusts the API: if `getMe()` returns no user, `/upload` redirects to `/`. If a user opens `/upload?suggest=<cid>` for a collection they don't own, the modal's collection list (fetched fresh from `GET /collections`) simply won't include it, and the `suggest` param falls through to "no preselection." No special UI for the unauthorized case beyond the existing patterns.

### Wiring in `App.tsx`
Add one new route entry: `<Route path="/upload" element={<Upload />} />`. No layout component, no provider, no router refactor.

### Loading / empty / error contract (applies to every new page)
- **Loading:** dusty-rose pulse skeleton in the same shape as the eventual content (eyebrow bar + title bar + grid of square placeholders).
- **Empty:** italic muted copy in the same voice as `Dashboard` ("No photos in your inbox. Tap upload to get started.").
- **Error:** inline muted message under the header — we do not throw users to a separate error route. Network failure on the staging fetch shows "Couldn't reach the server. Retrying…" with auto-retry.

---

## 3. /upload — Inbox + Staging + Grouping

### Layout

**Mobile (default, ≤640 px — primary target):**
```
┌────────────────────────────────────┐
│ eyebrow:  YOUR INBOX               │
│ H1:       Upload                   │
│ subhead:  12 staged · 3 grouped    │
│           today                    │
├────────────────────────────────────┤
│  [ Choose photos ]  [ Take photo ] │  <- file pickers
├────────────────────────────────────┤
│ ▢▢▢                                │  <- staging grid, 3 cols
│ ▢▢▢                                │
│ ▢▢▢                                │
│  …                                 │
├────────────────────────────────────┤
│ STICKY ACTION BAR (only when ≥1    │
│ selected):                         │
│   "3 selected"   [Discard selected][Group]  │
└────────────────────────────────────┘
```

**Tablet (640–1024 px):** 4-column grid; CTAs inline in the header rather than stacked.
**Desktop (≥1024 px):** 5-column grid, `max-w-4xl mx-auto`, file pickers sit to the right of the title in a single header row. Sticky action bar becomes a centered floating bar `bottom-6 left-1/2 -translate-x-1/2` with `bg-near-black/95 text-cream` (the only place we invert the palette — used because the bar floats over content and needs contrast).

### Component tree
```
<Upload>
  <UploadHeader>
    <Eyebrow>YOUR INBOX</Eyebrow>
    <h1>Upload</h1>
    <StatusCounter staged={n} groupedToday={m} />
    <FilePickerButtons>
      <FilePickerButton label="Choose photos" multiple />
      <FilePickerButton label="Take photo"  capture="environment" />
    </FilePickerButtons>
  </UploadHeader>

  <StagingGrid>
    {photos.map(p => (
      <ThumbnailTile photo={p} selected={...} onToggle={...} onDiscard={...} />
    ))}
  </StagingGrid>

  <SelectionActionBar visible={selected.length > 0}>
    <span>{selected.length} selected</span>
    <button onClick={discardSelected}>Discard selected</button>
    <button onClick={openGroupModal}>Group as one purse</button>
  </SelectionActionBar>

  <CollectionPickerModal open={...} preselect={suggestCid} onConfirm={...}>
    <CollectionDropdown collections={...} />
    <NewCollectionInline />
  </CollectionPickerModal>

  {/* Toast surface rendered by <ToastProvider> at app root — consumed via useToast() */}
</Upload>
```

### Header
- File picker is a real `<input type="file" accept="image/*,image/heic,image/heif,image/webp" multiple>` hidden behind a styled label/button (terracotta primary CTA classes from §1).
- "Take photo" is a second input with `capture="environment"` (mobile-only — hidden on `md:` and up via `sm:hidden md:inline-flex` reversed).
- Status counter line: `text-muted text-sm font-sans` — example: `12 in your inbox · 3 grouped today (in this session)`. Numbers come from `GET /upload/staging` length and a small in-memory counter incremented on every successful group (no backend "grouped today" needed in v1; the counter resets when the tab closes).

### Staging grid
- CSS grid: `grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 sm:gap-3`.
- Each tile is a square (`aspect-square`) showing the 600×600 thumbnail from `/photos/{thumbnail_key}/thumb`, displayed at ~120 CSS px on phone (3-up in a 360-px viewport).
- Tile element is a `<button role="checkbox" aria-checked={selected} aria-label="Photo IMG_0001.HEIC, captured 2026-04-30 18:42, tap to toggle selection">`.
- Default state: full-bleed image, no border, subtle `bg-dusty-rose/10` letterbox under it before image loads (object-cover).
- **Selected state:** `ring-4 ring-saffron ring-offset-2 ring-offset-cream` plus a checkmark icon (lucide `Check`) at top-right inside a `bg-saffron text-near-black w-7 h-7 rounded-full grid place-items-center`. The ring is the load-bearing signal; the checkmark is the redundant-affordance for color-blind users.
- **Discard affordance (per-tile):** small `×` icon button (`aria-label="Discard photo"`) at top-left of every tile, visible always on touch (no hover gating because phones), `bg-near-black/60 text-cream w-7 h-7 rounded-full` with an `X` icon. No "Discard" text label — icon only, disambiguated from the batch action bar. We chose **explicit icon button** over swipe or long-press: swipe collides with the page's vertical scroll on iOS; long-press fights the iOS "save image" menu. An always-visible discard icon is the lowest-friction choice and matches Pinterest/Instagram's editor patterns.
- **Capture date stamp** (subtle, optional): `text-[10px] text-cream font-sans tracking-wider` at bottom-left of the tile inside a `bg-gradient-to-t from-near-black/60 to-transparent` strip — only shown if `captured_at` is present. Matches editorial-magazine caption restraint.

### Selection state (logic)
- `selected: Set<number>` in component state.
- Tap a tile → toggle membership.
- The selection bar appears (slides up from bottom on mobile; fades in on desktop) when size > 0.
- "Group" button on the bar is the primary terracotta CTA. "Discard selected" is the destructive labeled button (terracotta outline) — the label distinguishes it from the per-tile `×` icon (`aria-label="Discard photo"`).
- Tap "Group" → opens `<CollectionPickerModal>`.

### Collection picker modal
- Fetches `GET /collections` on open (always fresh, no cache).
- Layout: full-screen sheet on mobile (`fixed inset-0 bg-cream`); centered card on desktop (`max-w-md`). Slide-up entrance on mobile (`translate-y-full → translate-y-0` over 200 ms).
- Heading: eyebrow `WHERE IS THIS PURSE GOING?`, title `Pick a collection`.
- Body:
  - A vertical list of the user's collections (same `bg-dusty-rose/20 border-l-4 border-l-terracotta` style as Home) with a radio control on the left (`role="radio"`).
  - Below the list: a permanently visible "**+ New collection**" affordance that, when activated, expands an inline form with two fields (name, description) and an inline "Create" button. This avoids the awful nested-modal pattern.
- Footer: secondary `Cancel` (cobalt outline) + primary `Group N photos` (terracotta filled). Disabled when no selection.
- On confirm:
  - If "new collection" is chosen, first `POST /collections`, then `POST /upload/group` with the new id.
  - If existing collection chosen, `POST /upload/group` directly.
  - On success: close modal, remove the grouped tiles from the grid (with a 200 ms fade-out animation, see §9), show a toast: "Grouped 3 photos into Rachel's Collection — `Review now ↗`" where the link goes to `/review/<cid>` and is the cobalt tertiary-link style.
- `?suggest=<cid>` URL param: pre-selects the matching collection's radio when the modal opens, but does not constrain it. After a successful `POST /upload/group`, the route programmatically navigates to `/upload` (no query params), stripping the suggestion. This is the default — sticky URL state surprises users who return later expecting a fresh start. Users who want to rapid-fire batch into the same collection can bookmark the URL with the param. See §13 decision #5 for the rationale and override option.

### Polling for cross-device sync
- 30-second `setInterval` re-fetching `GET /upload/staging?limit=200`.
- Only runs while the document is visible (`document.visibilityState === "visible"`) — pause polling when tab is hidden, resume on visibility change. This matters for phone battery.
- Dedupe by `id`: new photos animate in (fade + slight scale) at the top of the grid; existing photos do not re-render.
- No SWR/React-Query; a `useEffect` with `setInterval` and an abortable fetch is enough.

### Empty state
- Shown when `staging.length === 0` and we are not loading.
- Centered in the main column: a small lucide `Inbox` icon (`w-10 h-10 text-dusty-rose`) above an italic muted line `Your inbox is empty.` and a non-italic line `Tap "Choose photos" to get started.` No illustration, no animation — Cabana-restraint.

### Skeleton loading
- During the first fetch only (subsequent polls do NOT re-skeleton). Renders a 9-tile grid of `aspect-square bg-dusty-rose/30 animate-pulse rounded-none` placeholders, plus a faint header bar.

### Pagination
- Default 200/page. We render an `IntersectionObserver` sentinel at the bottom of the grid; when it enters viewport and `has_more` is true, fetch the next page with `before=<lastId>` and append. No "Load more" button — phone users expect infinite scroll.

---

## 4. /review/:cid — Metadata Extensions + Add-Photos

### Per-item card structure (extended)

The current card (in `ItemReview.tsx`) has brand + status + condition bar. We additively wrap it into a vertically expanding "spread":

```
┌──────────────────────────────────────────┐
│ [Brand inline-edit]            [Status]  │
│ ─────────── condition bar ───────────    │
│                                          │
│ PHOTOS                                   │
│ ▢ ▢ ▢ ▢ [+ Add photos]                   │
│                                          │
│ DETAILS                                  │
│ Color (primary)   [ select ]             │
│ Color (accents)   [ multi-select  ]      │
│ Style             [ select ]             │
│ Material          [ select ]             │
│ Dimensions (in)   W [ ]  H [ ]  D [ ]    │
│ Serial            [ text ]               │
│ Asking price      $ [ number ]           │
└──────────────────────────────────────────┘
```

- Each section header is the `text-[10px] uppercase tracking-[0.3em] text-muted` micro-label.
- Each form row: label (uppercase tracked, ~120 px wide on desktop, stacked on mobile) + control. On mobile the label sits above the control (`flex flex-col gap-1`).

### Photo gallery (within each item card)
- Inline grid of thumbnails identical to the staging grid styling at smaller scale (`grid grid-cols-4 sm:grid-cols-6 gap-1.5`, ~64 px tiles).
- Trailing tile is the "**+ Add photos**" affordance — same square shape, dashed cobalt border (`border border-dashed border-cobalt text-cobalt`), with a `Plus` icon centered. Tap → opens a per-item file picker (`accept="image/*,image/heic,image/heif,image/webp" multiple`) → `POST /collections/{cid}/items/{iid}/photos` (skips staging entirely, per spec).
- Newly uploaded photos appear in the gallery on success; failed uploads surface in a per-item toast.
- Hero photo (the `is_hero=true` one) is rendered with a subtle saffron underline (`border-b-2 border-saffron`). v1 is read-only on hero/order; drag-to-reorder is in the spec's stretch goals.

### Form controls
- **Color (primary):** native `<select>` styled to match (Tailwind: `bg-cream border-b border-muted px-0 py-2 font-sans text-sm focus:border-terracotta`). Options are the 11 enum values from the spec; "multi" is the last option, separated visually with an `<optgroup>`.
- **Color (accents):** custom multi-select chip picker (`<EnumMultiSelect>`). Each color renders as a pill: unselected = `border border-muted text-muted`; selected = `bg-near-black text-cream`. On phone this is a horizontally scrollable row of chips. **Disabled** (visually muted + `aria-disabled="true"`) when primary is `multi`.
- **Style / Material:** native `<select>` with the spec's enums.
- **Dimensions:** three `<input type="number" step="0.1" min="0">` inputs in a 3-col grid; the unit "in" is suffixed as a static label.
- **Serial:** `<input type="text">`.
- **Asking price:** `<input type="number" min="0" step="1" inputMode="numeric" pattern="[0-9]*">` with a `$` prefix sibling. Whole dollars per spec. (`pattern="[0-9]*"` is an iOS keyboard hint — triggers the numeric keypad on Safari.)

### Save semantics
- **Explicit Save button + Enter** (matching the existing pattern). The brand inline-editor in `ItemReview.tsx` uses click-to-edit with an explicit "Save" button (`saveBrand` function, called via `onClick` or `onKeyDown Enter`). There is no `onBlur` handler in the existing code. We extend this same pattern to the new metadata fields: each field enters an editing state on click/tap, and saves via an explicit "Save" button or Enter. Save-on-blur was considered but is **not** what the existing code does; aligning here avoids inconsistency.
- A small saving indicator (`text-[10px] text-muted` "Saved" with a checkmark, fading after 1.5 s) appears next to the field that just saved. On error, the field border turns terracotta and an inline message shows the reason.
- **Multi-color rule (client):** when primary is set to `multi`, we (a) clear `secondary_colors` locally, (b) PATCH both fields together in one request, and (c) disable the accents picker. Server-side validator is the source of truth; the client guard is for UX.
- Why explicit Save vs save-on-blur: the existing `ItemReview.tsx` brand field uses `saveBrand` (explicit Save button + Enter), not blur. We match that rather than mixing patterns. For `asking_price` in particular, the explicit Save is a safety feature — money fields should not silently commit on a stray blur. Listed in §13 as decision #1 (overridable).

### Loading / empty / error
- Loading: the existing skeleton pattern; each new field renders a `h-8 bg-dusty-rose/30 animate-pulse` placeholder.
- Empty (no items): unchanged from current.
- Per-field error: terracotta border + inline `text-[11px] text-terracotta`.

---

## 5. / and /dashboard — Banner + Upload Button

### Home banner
- Rendered at the top of the authenticated Home `<main>`, above `Your Collections`.
- Visibility: only when `GET /upload/staging` returns `length > 0`. Fetched alongside the existing `Promise.all([getMe, getCollections])`.
- Markup:
  ```
  <a href="/upload"
     className="flex items-center justify-between gap-4
                bg-saffron/15 border border-saffron border-l-4 border-l-terracotta
                px-5 py-4 mb-6
                hover:bg-saffron/25 transition-colors">
    <div>
      <p className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-1">
        Your Inbox
      </p>
      <p className="font-serif text-lg text-near-black">
        {n} {n === 1 ? "photo" : "photos"} waiting to be grouped
      </p>
    </div>
    <span className="text-terracotta font-sans text-sm" aria-hidden="true">→</span>
  </a>
  ```
- **Dismissibility:** **NOT dismissible.** The banner exists because there is real work to do; hiding it just makes work disappear into a forgotten corner. It auto-disappears the moment staging hits zero. Listed in §13 as overridable.

### Dashboard "Upload" button
- Added to the header on `Dashboard.tsx`, top-right of the title row. Becomes a flex header: title on left, button on right.
- Style: primary terracotta CTA classes (consistent with "Review Items").
- Mobile: button drops below the title in the header.
- Always visible regardless of which collection is selected (per spec).

---

## 6. /session/:cid — Curator Discoverability

- A subtle tertiary link added to the page header of `RankingSession.tsx`, right-aligned: `+ Add photos to this collection`.
- Style: tertiary cobalt-link style from §1.
- On click: navigate to `/upload?suggest=<cid>`.
- Curators thus never have to leave their primary surface to add photos — the inbox grouping just shows their collection pre-selected.

---

## 7. Component Inventory

New components extracted to `frontend/src/components/`. All are presentational (props + callbacks); state lives in pages.

| Component | Purpose | Key props |
|---|---|---|
| `ThumbnailTile` | Square photo tile with selection + discard, used in staging grid and item gallery | `photo`, `selected`, `onToggle`, `onDiscard`, `size` ("md" / "sm") |
| `SelectionActionBar` | Sticky bottom bar with selection count and grouped actions | `count`, `onDiscard`, `onGroup` |
| `FilePickerButton` | Styled button wrapping a hidden `<input type="file">` | `label`, `multiple`, `capture?`, `accept`, `onFiles` |
| `CollectionPickerModal` | The group-into-collection flow | `open`, `collections`, `preselectId?`, `onConfirm({collectionId})`, `onClose` |
| `NewCollectionInline` | Inline name+description form inside the modal | `onCreate(name, desc)` |
| `BannerInbox` | Home banner | `count` |
| `EnumMultiSelect` | Chip-picker for accent colors | `value: string[]`, `options`, `onChange`, `disabled?` |
| `ColorPickerPair` | The combined primary + accents control with the multi-exclusive rule baked in | `primary`, `secondary`, `onChange({primary, secondary})` |
| `MetadataField` | Label + control + saving indicator wrapper (used for every per-item field); handles the styled label/input including native `<select>` for fixed enums (subsumes what would have been a separate `EnumSelect` — it's a 6-line wrapper not worth its own component) | `label`, `status` ("idle"/"saving"/"saved"/"error"), `error?`, `children` |
| `Toast` / `ToastQueue` | Small toast surface (cream-on-near-black, bottom-center) | context-based — see §11 |
| `Modal` | Generic accessible modal shell (focus trap, esc-to-close, slide-up on mobile) | `open`, `onClose`, `title`, `children` |
| `IconButton` | Square icon-only tap target ≥44×44 with aria-label | `icon`, `label`, `onClick` |

Total: 12 new components (`EnumSelect` dropped — subsumed into `MetadataField`). We do not pull in any new component library; all of these compose the existing `frontend/src/components/ui` shadcn primitives where applicable, and are otherwise plain divs/buttons with Tailwind classes.

---

## 8. State Management

Three layers, no new libraries:

### Server state
- `GET /upload/staging` — fetched on mount and every 30 s on `/upload`. Stored in component state (`useState<StagingPhoto[]>`).
- `GET /collections` — fetched fresh when modal opens.
- `getItems(cid)` — already used on `ItemReview`, extended to return new metadata fields.
- All fetches are plain `fetch` via the existing `frontend/src/api.ts` patterns. No SWR, no React Query.

### URL state (react-router)
- `?suggest=<cid>` on `/upload` — read with `useSearchParams`. Drives modal preselection.
- `:cid`, `:collectionId` — already wired in router.
- We deliberately **do not** put selection state, modal-open state, or polling state in the URL — it would cause the browser back button to feel wrong.

### React state (component-local, `useState` / `useReducer`)
- `selected: Set<number>` on `Upload`.
- `modalOpen: boolean`.
- `staging: StagingPhoto[]`, `loading: boolean`, `hasMore: boolean`, `cursor: number|null`.
- Per-field saving status on `ItemReview` items: a `Map<itemId, Map<fieldName, "saving"|"saved"|"error">>`. Small enough to keep in a single `useReducer`.

### Cross-page state
- The Home banner needs to know staging count without `/upload` being mounted. Home calls `GET /upload/staging?limit=1` and reads the array `length` plus `has_more` to display the banner. No backend change needed; this is fully additive on the frontend.
- No global store. No Context for staging count — Home re-fetches on mount.

---

## 9. Accessibility

### Tap-to-group grid
- Each tile: `role="checkbox"`, `aria-checked={selected ? "true" : "false"}`, `aria-label="Photo {original_filename}, {captured_at_human}"`, `tabIndex={0}`.
- The grid container: `role="group" aria-label="Staging photos"`.
- Keyboard model:
  - Arrow keys move focus across grid (with row/column awareness — left/right within a row, up/down across rows). The grid uses fixed Tailwind breakpoint columns (`grid-cols-3 sm:grid-cols-4 md:grid-cols-5`) — NOT `auto-fill`. This is load-bearing for keyboard accessibility: we statically know column counts per breakpoint (3 / 4 / 5) without runtime measurement via `getComputedStyle`.
  - `Space` or `Enter` toggles the focused tile's selection.
  - `Shift+Space` extends selection to a range (nice-to-have; deferred if it becomes a slog — listed in §13).
  - `Esc` clears the current selection.
- Selected state's load-bearing affordance is the **ring + checkmark** combination, never color alone. The saffron ring is supplementary; the checkmark icon (semantic `Check` glyph) is the primary signal for color-blind users and high-contrast mode.

### Modals
- `<CollectionPickerModal>` traps focus on open, restores focus to the trigger on close. Implementation via a small focus-trap util (or `inert` on the rest of the document — both fine; we'll pick when implementing).
- `Esc` closes without grouping.
- The modal heading is `aria-labelledby`'d to its `<h2>`; body content is `aria-describedby`'d.

### Buttons & icons
- Every icon-only button (discard, close, "+ Add photos") has an `aria-label`. The `IconButton` wrapper enforces this — it throws in dev if `label` prop is missing.

### Live regions
- After grouping, a polite live region (`<div role="status" aria-live="polite" className="sr-only">`) announces "Grouped 3 photos into Rachel's Collection." This pairs with the visible toast.
- After polling adds new staging photos, a second polite live region announces "2 new photos in your inbox." Throttled to one batched announcement per polling tick — if N photos arrive in a single poll response, a single announcement is made ("N new photos in your inbox") rather than N individual announcements.

### Forms
- All `MetadataField` rows: `<label htmlFor>` linked to the control's `id`.
- Saving status: changes are announced via `aria-live="polite"` on the per-field saving indicator.
- Error messages: `aria-describedby` on the failing field.

### Color contrast
- All seven palette tokens already pass WCAG AA against `cream` for body and `near-black` for headings. We re-check `saffron` text on `cream` (it's borderline — we use it as a background or ring, never as body copy). Selected-pill `bg-near-black text-cream` is AAA.

### Focus visibility
- We add `focus-visible:ring-2 focus-visible:ring-cobalt focus-visible:ring-offset-2 focus-visible:ring-offset-cream` to every interactive element. Existing pages don't have this consistently — adding it across new components and quietly to the existing buttons we touch is a small wins-along-the-way move.

---

## 10. Mobile / Touch

- **Tap targets:** every interactive element ≥ 44×44 CSS px. The thumbnail tiles already exceed this at 120 px+; the discard icon button is `w-9 h-9` (36 px) but its hit-target is padded via `before:` pseudo-element to 44 px. Documented as part of `IconButton`.
- **iOS file picker:** `<input type="file" accept="image/*,image/heic,image/heif,image/webp" multiple>` triggers iOS's native sheet (Photos / Camera / Files). `image/*` is first so it acts as the broad wildcard; the explicit MIME types that follow (`heic`, `heif`, `webp`) are informational hints — iOS already allows them; the server is the source of truth for format support.
- **iOS camera:** the secondary "Take photo" button uses `capture="environment"` to skip straight to the back camera. Hidden on `md:` and up via `md:hidden` (no use case for it on desktop).
- **HEIC handling:** client uploads as-is. Server converts. UI shows the original HEIC's filename (`IMG_0001.HEIC`) in the tile's aria-label and capture-date strip; the rendered image is the JPEG thumbnail the server generated.
- **Sticky action bar:** uses `position: sticky; bottom: 0` with `bg-cream/95 backdrop-blur-md border-t border-cream`. Respects iOS safe-area via `pb-[env(safe-area-inset-bottom)]`.
- **Pull-to-refresh:** we do **not** override iOS native pull-to-refresh; users get a free hard-refresh that hits our route loader. Polling continues to handle the soft case.
- **One-handed reachability:** primary CTAs (Group, Upload) are at the **bottom** of the viewport on mobile via the sticky bar. Header file picker is up top — a deliberate trade-off because file picking is a less-frequent action than grouping.
- **Scroll lock during modal:** `body { overflow: hidden }` while modal is open, restored on close.

---

## 11. Failure & Edge Cases

### Toast system
- **Provider:** `<ToastProvider>` mounted at app root (in `App.tsx`), renders the toast stack.
- **Hook:** `useToast()` returns `{ show, success, error }` methods. Pages and components call e.g. `toast.success("Grouped 3 photos…")` — no prop-drilling.
- **Capacity:** max 5 toasts visible at once; oldest is evicted (FIFO) when the 6th arrives.
- **Auto-dismiss:** each toast auto-dismisses after 4 seconds.
- **Manual dismiss:** each toast has a `×` button; clicking it removes it immediately.
- **Styling:** cream-on-near-black (`bg-near-black/95 text-cream`), bottom-center, stacked. `success` variant gets a `forest` left border; `error` gets `terracotta` left border.

### Upload failure modes (per spec response shape)
- The `POST /upload/photos` response is `{succeeded: [...], failed: [{original_filename, reason}]}`. Frontend handling:
  - All-success: silent. New photos appear at the top of the grid with a fade-in.
  - Partial success: toast `"5 photos uploaded · 2 skipped"` with an inline "View details" affordance that expands the toast into a list of `{filename}: {reason}`.
  - All-fail: toast `"None of those uploaded — see details"` in terracotta-warning treatment.
- Reasons are humanized client-side from the server message:
  - `"unsupported format"` → `"This file type isn't supported. Try JPEG, PNG, or HEIC."`
  - `"too large"` → `"This photo is over 25 MB and was skipped."`
  - default → server message verbatim.

### HTTP-level errors
- **413 (request body too large):** `"Some photos were too big. Try uploading in smaller batches."` — the request never reaches per-file handling, so we don't know which file. Surface as a single toast.
- **415 (unsupported overall):** same humanization as above.
- **429 staging cap (>500):** toast `"Inbox full — group or discard photos before uploading more."` Plus we render a thin terracotta strip above the grid that persists while staging length > 480 (warning state) reading `Inbox is nearly full — N of 500.`
- **404 on group (IDOR):** "Couldn't find one of those photos. Refreshing your inbox…" + auto-refetch.
- **5xx:** generic toast "Something went wrong on our end. Try again in a moment."

### Network offline
- We **block** new uploads when `navigator.onLine === false` rather than queueing. A queue requires durable client storage (IndexedDB) and a service worker; out of scope for v1, and the alternative — "your photos seemed to upload but actually didn't" — is much worse than an explicit "You're offline." toast. Selecting / grouping continues to work against the cached staging list; the group call will fail and retry on reconnect.
- Listed in §13 as overridable (PWA-style queue is a real future option).

### Polling under failure
- 30-s poll fails → exponential back off to 60 s, 120 s, max 300 s, with a small "Reconnecting…" indicator next to the status counter. Resumes 30-s cadence on success.

### Race: photo discarded on phone, just-grouped on desktop
- Server returns 404 on group; client refreshes staging. We do not pre-empt this with optimistic locking — the race window is small.

### Modal closed mid-flight
- If the user closes the modal while `POST /upload/group` is in flight, we let it finish in the background. On success the toast still fires; on failure we re-open the modal with the previous selection preserved.

### Focus loss
- After grouping, focus goes to the toast's "Review now" link (it's the natural next action). If toast dismissed without focus capture, focus returns to the page's main heading.

---

## 12. Testing Strategy Preview

(Per spec target: ~4 new Playwright tests for plan 3, ~2 for plan 4, ~2 for plan 5. We outline coverage; we do **not** write the tests here.)

### Playwright E2E (must cover)
1. **Inbox upload + group, single user:** Upload 3 fixture PNGs from `tests/fixtures/purses/`, see them in the grid, multi-select all 3, open modal, pick an existing collection, group, assert the toast and assert the grid is empty.
2. **Inbox upload + group into new collection (inline create):** Upload 2 photos, open modal, expand "+ New collection", create with a name, group; assert the new collection exists via the next page.
3. **Discard:** Upload 2 photos, discard one via the icon button, assert it's gone.
4. **Suggest param:** Open `/upload?suggest=<cid>`, verify the modal preselects that collection.
5. **`/review/:cid` adds photos:** Open review page for a collection, click "+ Add photos" on an item, upload a fixture, assert the new thumbnail appears.
6. **`/review/:cid` metadata save (explicit Save button):** Set primary color to `multi`, assert accents picker disabled. Set primary to `red`, type accents, click Save, assert PATCH fired and success indicator showed.
7. **Home banner appears when staging non-empty, disappears at zero:** Seed 1 staging photo via API, navigate to `/`, assert banner present; group it, return to `/`, assert banner absent.
8. **Curator discoverability link:** From `/session/:cid`, click "+ Add photos to this collection", assert URL is `/upload?suggest=<cid>`.

### Unit tests (must cover)
- `ColorPickerPair`: setting primary to `multi` clears secondary AND emits a single `onChange` with both fields.
- `EnumMultiSelect`: toggle on/off chips, respect `disabled`.
- `MetadataField`: status transitions (idle → saving → saved → idle after 1.5 s).
- File-input accept-attribute generation: HEIC, HEIF, JPEG, PNG all in the accept string.
- Selection grid keyboard navigation: arrow keys move focus, space toggles, esc clears (jsdom test of the `useGridSelection` hook).
- Humanizer for upload-failure reasons: input strings → expected user-facing strings.

### Visual regression
- Out of scope for v1. Documented as a future addition in §13.

---

## 13. Open Questions for User Review

These are decisions I made one way; the user might prefer the other. Ordered by priority — highest-stakes choices first.

1. **Explicit Save button vs save-on-blur for `/review/:cid` metadata fields.** Current plan matches the existing `saveBrand` pattern (explicit Save button + Enter). Save-on-blur would feel more frictionless for most fields, but `asking_price` is a money field where a stray blur silently committing a wrong value is a real safety issue. Recommend: explicit Save for v1, revisit save-on-blur for non-money fields after user testing.
2. **Banner on `/` is non-dismissible.** I argued the banner is the user's to-do list; making it dismissible per session might just hide it. But Rachel might rather grind on rankings without a "you have homework" reminder. Easy to flip to a dismissed-this-session toggle stored in `sessionStorage`.
3. **`?suggest=<cid>` URL stickiness — default is now "strip after first successful group."** After `POST /upload/group` succeeds, we navigate to `/upload` (no query params). Users wanting to rapid-fire batch into the same collection can keep the URL bookmarked. If you want the old "sticky" behavior (don't strip), easy to restore by removing the programmatic navigation.
4. **Network offline blocks uploads** rather than queueing. PWA-style background upload is feasible but expensive to do well. Confirm this is the right v1 trade.
5. **Discard affordance is an always-visible icon button** rather than long-press, swipe, or hover-to-reveal. The trade-off is visual noise on the grid. We could mitigate by showing the icon only when `selected` is true OR on hover/focus on desktop. (Recommend: keep always-visible for v1, revisit if visually noisy in user testing.)
6. **Selected ring color is saffron.** Saffron pops against cream and isn't already used for action — cobalt would conflict with the secondary CTA, terracotta with primary CTA. But terracotta is the brand's "yes" color and might feel more correct. Easy swap.
7. **No drag-to-reorder** on the per-item gallery on `/review/:cid` in v1; hero is the first photo at group time. Spec lists drag-to-reorder as stretch, so this is conservative. User might want it sooner.
8. **30-s polling vs server-sent events.** Polling is simpler and was the spec's choice; SSE / WebSockets would feel snappier on the phone-then-desktop hand-off but adds infra. Confirm 30 s is fine.
9. **Home banner threshold is `> 0`.** Some teams prefer `≥ 5` so the banner doesn't nag for one stray photo. Easy to make a constant.
10. **"Take photo" button hidden on desktop.** Desktops with webcams could still use `capture="user"`. We hide it because it's a noisy affordance for SD-card workflows. Easy to expose if desired.

---

## 14. Performance Budget

Explicit numbers so we can make informed trade-offs during implementation:

| Constraint | Value | Notes |
|---|---|---|
| Max staging tiles in DOM | 500 | The per-user server cap; no virtualization in v1. Accept the risk — at 500 tiles × ~600×600 JPEG thumbnails the DOM is large but scrolling is manageable on mid-tier phones. Revisit if scrolling degrades. |
| Max concurrent thumbnail requests | Browser default (~6 per origin) | We do not cap this ourselves; `loading="lazy"` handles it naturally. |
| Decoded image memory budget | ~50 MB on iOS Safari | 500 tiles × 600×600 px ≈ 36 MB raw; headroom for simultaneous decoding and browser overhead keeps us comfortably under iOS's ~150 MB hard limit in practice. |
| Time-to-interactive on `/upload` first paint | < 1.5 s | Target: mid-tier mobile device with a cached app shell. |

### Mitigations included in v1
- `loading="lazy"` on every `<img>` in the staging grid — browser only decodes tiles near the viewport.
- `content-visibility: auto` on each tile container — browser skips layout/paint for off-screen tiles.
- Fixed-aspect-ratio container (`aspect-square`) on every tile — eliminates cumulative layout shift as images load in.

---

## Stretch (explicitly deferred, do not build in v1)

- **Auto-grouping suggestions** on `/upload` (server clusters by timestamp + similarity; the UI would render a "These look like one purse — group?" pill above the grid). Tied to the spec's stretch goal.
- **Drag-to-reorder photos** in the per-item gallery on `/review/:cid`. Backend already supports `is_hero` + `sort_order`.
- **Visual regression tests** with Playwright snapshots for the staging grid, modal, and banner.
- **Range-select with `Shift+Space`** in the staging grid keyboard model.
- **PWA / service worker** with IndexedDB-backed offline upload queue.
- **WebP/AVIF thumbnails** — wired through whenever the backend's stretch goal lands.
- **Server-sent events** for staging-grid live updates instead of 30-s polling.
- **i18n** of color/style/material display strings — the controls already separate stored value from label, so this is a future add.
- **Hero/cover photo selection UI** on `/review/:cid` (manual override of `is_hero`).
- **Visual sort/filter** on the staging grid (by capture date, by similarity).
