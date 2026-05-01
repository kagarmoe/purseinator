# Frontend TDD Design — Purseinator

**Philosophy:** If the tests pass, the app works. No mocking. Full stack.

## Overview

Playwright E2E tests covering every critical user flow. Tests run against the real app: Vite frontend dev server + FastAPI backend + SQLite test database. If all tests pass, the app is shippable.

## Architecture

```
Test stack:    @playwright/test (E2E only — no experimental CT)
Frontend:      Vite dev server (localhost:5173)
Backend:       FastAPI test instance (localhost:8000)
Database:      SQLite test DB seeded before each suite
Mocking:       None
```

No component isolation. No API stubs. No MSW. The test suite boots the real application and exercises it as a user would.

## Test Flows

Each flow is independently runnable and covers one complete user journey.

### 1. Auth Flow

File: `playwright/e2e/auth.spec.ts`

- Unauthenticated user visiting `/dashboard` is redirected to `/`
- Home page shows magic link form
- Submitting email shows confirmation message
- Dev login (`/auth/dev-login`) sets session cookie and lands on dashboard
- Authenticated user visiting `/` sees dashboard (or is redirected)

### 2. Collection Listing

File: `playwright/e2e/collections.spec.ts`

- Dashboard shows seeded collection by name
- Clicking collection navigates to `/collection/:id`
- Empty state shown when no collections exist

### 3. Ranking Session

File: `playwright/e2e/ranking.spec.ts`

- `/rank/:id` loads with a comparison pair visible
- Clicking one card increments the counter ("1 compared")
- A new pair loads after each pick (different items shown)
- Clicking Done shows completion screen with correct count
- Completion screen "See Your Rankings" navigates to `/collection/:id`
- Completion screen "Another Session" navigates to `/session/:id`

### 4. Timer Expiry

File: `playwright/e2e/timer.spec.ts`

- Session auto-completes when countdown reaches zero
- Completion screen shows correct comparison count
- Uses Playwright's `page.clock` to fast-forward time

### 5. Collection View

File: `playwright/e2e/collection-view.spec.ts`

- Ranked items appear in order after comparisons
- Keep/Sell divider renders between keeper and seller items
- Moving divider up reassigns bottom keeper to seller
- Moving divider down reassigns top seller to keeper
- Status changes persist: reloading the page shows updated statuses

### 6. Item Review

File: `playwright/e2e/item-review.spec.ts`

- All items in collection appear in the list
- Clicking brand name switches to inline edit input
- Typing new brand and pressing Enter saves it
- Updated brand appears immediately (optimistic) and persists on reload
- Save button also submits the edit

## Test Infrastructure

### Directory Structure

```
frontend/
  playwright/
    e2e/
      auth.spec.ts
      collections.spec.ts
      ranking.spec.ts
      timer.spec.ts
      collection-view.spec.ts
      item-review.spec.ts
    fixtures/
      seed.ts          ← creates test collection + items via backend API
      auth.ts          ← dev-login helper, authenticated page fixture
  playwright.config.ts
```

### Global Setup

`playwright.config.ts` uses `globalSetup` to:
1. Start FastAPI backend on port 8000 pointing at `test.db` (SQLite)
2. Seed one collection with 10 items via the API
3. Store collection ID in an env var for tests to reference

`globalTeardown` stops the backend and deletes `test.db`.

### Authenticated Page Fixture

Most tests need an authenticated session. A shared fixture calls `POST /auth/dev-login`, captures the session cookie, and attaches it to every page in the test. Tests that need unauthenticated state use a bare `page` instead.

### Seed Data

10 items with known brands, condition scores, and descriptions. Fixed seed so tests are deterministic. After ranking comparisons, expected order is verifiable.

## What "Done" Looks Like

```bash
npm test
```

- Starts the full stack
- Runs all 6 flow files
- Exits 0
- Output: each flow green, total runtime under 60 seconds

No manual steps. No background servers to start. `npm test` is the complete check.

## Out of Scope

- Visual regression tests
- Performance/load testing
- Backend unit tests (covered in `2026-05-01-backend-tdd-design.md`)
- Accessibility audits
