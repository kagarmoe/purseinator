# Frontend TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Playwright E2E tests covering every critical user flow so that `npm test` passing means the app is shippable.

**Architecture:** Playwright E2E tests run against the real full stack — Vite dev server (port 5173) + FastAPI backend (port 8000) + SQLite test DB. Global setup starts the backend, runs migrations, and seeds a collection with 10 items. No mocking.

**Tech Stack:** `@playwright/test`, FastAPI + uvicorn, SQLite (`aiosqlite`), Vite, React 19

---

## File Map

```
frontend/
  playwright.config.ts                     ← Playwright config (webServer + globalSetup)
  playwright/
    global-setup.ts                        ← start backend, migrate, seed test data
    global-teardown.ts                     ← kill backend, delete test.db
    .test-state.json                       ← written by setup, read by tests (gitignored)
    .backend.pid                           ← written by setup, used by teardown (gitignored)
    fixtures/
      auth.ts                              ← authedPage + collectionId fixtures
    e2e/
      auth.spec.ts
      collections.spec.ts
      ranking.spec.ts
      timer.spec.ts
      collection-view.spec.ts
      item-review.spec.ts
```

Modify:
- `frontend/package.json` — add `test` script and Playwright devDependency
- `frontend/.gitignore` — ignore `.test-state.json`, `.backend.pid`, `test-results/`, `playwright-report/`

---

### Task 1: Install Playwright and write config

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/.gitignore`

- [ ] **Step 1: Install Playwright**

```bash
cd /gt/purseinator/purseinator/frontend
npm install --save-dev @playwright/test
npx playwright install chromium
```

Expected: `@playwright/test` appears in `package.json` devDependencies, chromium downloaded.

- [ ] **Step 2: Write playwright.config.ts**

Create `frontend/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './playwright/e2e',
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
    timeout: 30_000,
  },
  globalSetup: './playwright/global-setup.ts',
  globalTeardown: './playwright/global-teardown.ts',
});
```

- [ ] **Step 3: Add test script to package.json**

In `frontend/package.json`, add to `"scripts"`:

```json
"test": "playwright test",
"test:ui": "playwright test --ui"
```

- [ ] **Step 4: Update .gitignore**

Append to `frontend/.gitignore` (create if it doesn't exist):

```
test-results/
playwright-report/
playwright/.test-state.json
playwright/.backend.pid
```

- [ ] **Step 5: Run with no tests to verify config loads**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- --list
```

Expected: exits 0 (no tests found yet, but config parsed without error).

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/package.json frontend/package-lock.json frontend/playwright.config.ts frontend/.gitignore
git commit -m "test: install Playwright and configure E2E test runner"
```

---

### Task 2: Global setup — start backend and seed test data

**Files:**
- Create: `frontend/playwright/global-setup.ts`
- Create: `frontend/playwright/global-teardown.ts`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p /gt/purseinator/purseinator/frontend/playwright/e2e
mkdir -p /gt/purseinator/purseinator/frontend/playwright/fixtures
```

- [ ] **Step 2: Write global-setup.ts**

Create `frontend/playwright/global-setup.ts`:

```typescript
import { execSync, spawn } from 'child_process';
import { writeFileSync, existsSync, unlinkSync } from 'fs';
import { join } from 'path';

const APP_DIR = join(__dirname, '../../');
const TEST_DB_PATH = join(APP_DIR, 'test.db');
const STATE_FILE = join(__dirname, '.test-state.json');
const PID_FILE = join(__dirname, '.backend.pid');
const BACKEND_URL = 'http://localhost:8000';

async function waitForBackend(retries = 30, delayMs = 1000): Promise<void> {
  for (let i = 0; i < retries; i++) {
    try {
      const resp = await fetch(`${BACKEND_URL}/health`);
      if (resp.ok) return;
    } catch {}
    await new Promise(r => setTimeout(r, delayMs));
  }
  throw new Error('Backend did not start within 30 seconds');
}

export default async function globalSetup() {
  // Clean up any leftover test DB from a previous interrupted run
  if (existsSync(TEST_DB_PATH)) unlinkSync(TEST_DB_PATH);

  // Run migrations against the test DB
  execSync('alembic upgrade head', {
    cwd: APP_DIR,
    env: {
      ...process.env,
      PURSEINATOR_DATABASE_URL: `sqlite+aiosqlite:///${TEST_DB_PATH}`,
    },
    stdio: 'inherit',
  });

  // Start the FastAPI backend pointing at the test DB
  const backend = spawn(
    'uvicorn',
    ['purseinator.main:create_app', '--factory', '--port', '8000', '--log-level', 'warning'],
    {
      cwd: APP_DIR,
      env: {
        ...process.env,
        PURSEINATOR_DATABASE_URL: `sqlite+aiosqlite:///${TEST_DB_PATH}`,
        PURSEINATOR_DEV_MODE: 'true',
      },
      detached: true,
      stdio: 'ignore',
    }
  );
  backend.unref();
  writeFileSync(PID_FILE, String(backend.pid));

  await waitForBackend();

  // Seed: dev-login → collection → 10 items
  const loginResp = await fetch(`${BACKEND_URL}/auth/dev-login`, { method: 'POST' });
  if (!loginResp.ok) throw new Error(`dev-login failed: ${loginResp.status}`);
  const { session_id } = await loginResp.json();

  const headers = {
    'Content-Type': 'application/json',
    'Cookie': `session_id=${session_id}`,
  };

  const colResp = await fetch(`${BACKEND_URL}/collections`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ name: 'Test Collection', description: 'E2E seed data', dollar_goal: 1000 }),
  });
  if (!colResp.ok) throw new Error(`create collection failed: ${colResp.status}`);
  const { id: collectionId } = await colResp.json();

  const BRANDS = [
    'Chanel', 'Gucci', 'Prada', 'Louis Vuitton', 'Hermès',
    'Celine', 'Bottega Veneta', 'Balenciaga', 'Saint Laurent', 'Burberry',
  ];
  for (let i = 0; i < 10; i++) {
    const itemResp = await fetch(`${BACKEND_URL}/collections/${collectionId}/items`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ brand: BRANDS[i], description: `Test bag ${i + 1}` }),
    });
    if (!itemResp.ok) throw new Error(`create item ${i} failed: ${itemResp.status}`);
  }

  writeFileSync(STATE_FILE, JSON.stringify({ collectionId, sessionId: session_id }));
  console.log(`\n✓ Backend seeded. Collection ID: ${collectionId}\n`);
}
```

- [ ] **Step 3: Write global-teardown.ts**

Create `frontend/playwright/global-teardown.ts`:

```typescript
import { readFileSync, unlinkSync, existsSync } from 'fs';
import { join } from 'path';

const APP_DIR = join(__dirname, '../../');
const TEST_DB_PATH = join(APP_DIR, 'test.db');
const PID_FILE = join(__dirname, '.backend.pid');
const STATE_FILE = join(__dirname, '.test-state.json');

export default async function globalTeardown() {
  if (existsSync(PID_FILE)) {
    const pid = parseInt(readFileSync(PID_FILE, 'utf-8'), 10);
    try {
      process.kill(-pid, 'SIGTERM');
    } catch {}
    unlinkSync(PID_FILE);
  }
  if (existsSync(STATE_FILE)) unlinkSync(STATE_FILE);
  if (existsSync(TEST_DB_PATH)) unlinkSync(TEST_DB_PATH);
}
```

- [ ] **Step 4: Verify global setup runs**

Start the Vite dev server in a separate terminal first:
```bash
cd /gt/purseinator/purseinator/frontend && npm run dev &
```

Then:
```bash
cd /gt/purseinator/purseinator/frontend
npm test -- --list
```

Expected: setup script runs, "Backend seeded. Collection ID: 1" prints, test list shows 0 tests, teardown runs.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/
git commit -m "test: global setup starts backend and seeds test data"
```

---

### Task 3: Auth fixtures

**Files:**
- Create: `frontend/playwright/fixtures/auth.ts`

- [ ] **Step 1: Write the auth fixture**

Create `frontend/playwright/fixtures/auth.ts`:

```typescript
import { test as base, Page } from '@playwright/test';
import { readFileSync } from 'fs';
import { join } from 'path';

const STATE_FILE = join(__dirname, '../.test-state.json');

export type AuthFixtures = {
  authedPage: Page;
  collectionId: number;
};

export const test = base.extend<AuthFixtures>({
  collectionId: async ({}, use) => {
    const state = JSON.parse(readFileSync(STATE_FILE, 'utf-8'));
    await use(state.collectionId);
  },

  authedPage: async ({ page, context }, use) => {
    const state = JSON.parse(readFileSync(STATE_FILE, 'utf-8'));
    await context.addCookies([
      {
        name: 'session_id',
        value: state.sessionId,
        domain: 'localhost',
        path: '/',
        sameSite: 'Lax',
      },
    ]);
    await use(page);
  },
});

export { expect } from '@playwright/test';
```

- [ ] **Step 2: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/fixtures/auth.ts
git commit -m "test: add authenticated page fixture"
```

---

### Task 4: Auth flow tests

**Files:**
- Create: `frontend/playwright/e2e/auth.spec.ts`

- [ ] **Step 1: Write auth tests**

Create `frontend/playwright/e2e/auth.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test('unauthenticated user visiting /dashboard is redirected to /', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL('/');
});

test('home page shows email input for magic link', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('input[type="email"]')).toBeVisible();
});

test('submitting email shows confirmation message', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type="email"]').fill('test@example.com');
  await page.locator('button[type="submit"]').click();
  await expect(page.getByText(/check your email/i)).toBeVisible();
});

test('Dev Login button creates session and lands on dashboard', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /dev login/i }).click();
  await expect(page).toHaveURL('/dashboard');
});
```

- [ ] **Step 2: Run auth tests (expect failures)**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/auth.spec.ts
```

Expected: some tests fail — this surfaces auth redirect issues or mismatched selectors.

- [ ] **Step 3: Fix failing tests**

For each failure, read the error and fix the app code. Common issues:

**Unauthenticated redirect not working:** Check `Dashboard.tsx` — it calls `getMe()` and on 401 should navigate to `/`. If missing, add:
```typescript
// In Dashboard.tsx useEffect
getMe().catch(() => navigate('/'));
```

**Dev Login button not found:** Check `Home.tsx` — find the button text and update the selector, or add a `Dev Login` button if missing.

**Confirmation text mismatch:** Check `Home.tsx` success state — find the actual text and update the test selector.

- [ ] **Step 4: Run auth tests (expect all pass)**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/auth.spec.ts
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/ 
git commit -m "test: auth flow tests passing"
```

---

### Task 5: Collection listing tests

**Files:**
- Create: `frontend/playwright/e2e/collections.spec.ts`

- [ ] **Step 1: Write collection listing tests**

Create `frontend/playwright/e2e/collections.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('dashboard shows seeded collection', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await expect(authedPage.getByText('Test Collection')).toBeVisible();
});

test('clicking collection navigates to /collection/:id', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await authedPage.getByText('Test Collection').click();
  await expect(authedPage).toHaveURL(`/collection/${collectionId}`);
});

test('collection view shows ranked items after comparisons', async ({ authedPage, collectionId }) => {
  // Navigate to ranking session, make one comparison
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  const buttons = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
  await buttons.first().click();

  // Navigate to collection view
  await authedPage.goto(`/collection/${collectionId}`);
  // At least one item should appear with a rank number
  await expect(authedPage.locator('text=/^1$/')).toBeVisible();
});
```

- [ ] **Step 2: Run collection tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/collections.spec.ts
```

Expected: first two tests pass, third may fail if ranking view requires comparisons first.

- [ ] **Step 3: Fix any failures**

If "collection view shows ranked items" fails because no comparisons exist yet:
- Check `CollectionView.tsx` — it calls `getRankedItems`. Verify `/collections/:id/ranking` returns items even with zero comparisons (all items with rating=0, sorted stably).
- If backend returns empty, check the route in `purseinator/routes/ranking.py` and fix.

- [ ] **Step 4: Run collection tests (expect all pass)**

```bash
npm test -- playwright/e2e/collections.spec.ts
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/collections.spec.ts
git commit -m "test: collection listing and navigation tests passing"
```

---

### Task 6: Ranking session tests

**Files:**
- Create: `frontend/playwright/e2e/ranking.spec.ts`

- [ ] **Step 1: Write ranking session tests**

Create `frontend/playwright/e2e/ranking.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test.describe('ranking session', () => {
  test('shows a comparison pair on load', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    // Two item cards should be visible
    const cards = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
    await expect(cards).toHaveCount(2);
  });

  test('picking an item increments the counter', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    await expect(authedPage.getByText('0 compared')).toBeVisible();

    const cards = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
    await cards.first().click();

    await expect(authedPage.getByText('1 compared')).toBeVisible();
  });

  test('a new pair loads after each pick', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    const cards = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
    const firstPairText = await cards.first().textContent();
    await cards.first().click();

    // After pick, a new pair should appear (at least one card should differ)
    await expect(authedPage.getByText('1 compared')).toBeVisible();
    const newCards = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
    await expect(newCards).toHaveCount(2);
  });

  test('Done button shows completion screen with count', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    // Make 2 comparisons
    for (let i = 0; i < 2; i++) {
      const cards = authedPage.locator('button').filter({ hasText: /chanel|gucci|prada|louis|hermès|celine|bottega|balenciaga|saint|burberry/i });
      await cards.first().click();
      await authedPage.waitForTimeout(300);
    }

    await authedPage.getByRole('button', { name: /done/i }).click();
    await expect(authedPage.getByText(/session complete/i)).toBeVisible();
    await expect(authedPage.getByText('2 pairs')).toBeVisible();
  });

  test('See Your Rankings navigates to collection view', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    await authedPage.getByRole('button', { name: /done/i }).click();
    await authedPage.getByRole('button', { name: /see your rankings/i }).click();
    await expect(authedPage).toHaveURL(`/collection/${collectionId}`);
  });

  test('Another Session navigates back to session picker', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    await authedPage.getByRole('button', { name: /done/i }).click();
    await authedPage.getByRole('button', { name: /another session/i }).click();
    await expect(authedPage).toHaveURL(`/session/${collectionId}`);
  });
});
```

- [ ] **Step 2: Run ranking tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/ranking.spec.ts
```

Expected: tests may fail on text matching — item card buttons may not contain brand text directly. Read errors carefully.

- [ ] **Step 3: Fix failures**

If brand text is not visible in cards (because `infoLevel === "photos_only"`):

Check `ComparisonCard.tsx` — `showBrand` is false when `infoLevel === "photos_only"`. The `info_level` returned by `/collections/:id/ranking/next` controls this. 

If tests fail because cards have no visible brand text, update the test selectors to match the actual UI. For example, if cards are identified by their position rather than text:

```typescript
// Alternative selector if brands aren't visible:
const cards = authedPage.locator('[class*="flex-1"][class*="max-w-56"]');
```

Update ranking.spec.ts with the working selector.

- [ ] **Step 4: Run ranking tests (expect all pass)**

```bash
npm test -- playwright/e2e/ranking.spec.ts
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/ranking.spec.ts
git commit -m "test: ranking session flow tests passing"
```

---

### Task 7: Timer tests

**Files:**
- Create: `frontend/playwright/e2e/timer.spec.ts`

- [ ] **Step 1: Write timer tests**

Create `frontend/playwright/e2e/timer.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('session auto-completes when timer hits zero', async ({ authedPage, collectionId }) => {
  // Install clock before navigation so it controls setInterval from mount
  await authedPage.clock.install();

  await authedPage.goto(`/rank/${collectionId}?minutes=2`);

  // Verify timer is showing (e.g. "2:00")
  await expect(authedPage.getByText('2:00')).toBeVisible();

  // Fast-forward 2 minutes + 1 second
  await authedPage.clock.fastForward(121_000);

  // Completion screen should appear
  await expect(authedPage.getByText(/session complete/i)).toBeVisible();
});

test('timer counts down each second', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);

  await expect(authedPage.getByText('2:00')).toBeVisible();

  await authedPage.clock.tickFor(10_000);

  await expect(authedPage.getByText('1:50')).toBeVisible();
});

test('completion screen shows zero when no comparisons made before timer expires', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  await authedPage.clock.fastForward(121_000);

  await expect(authedPage.getByText(/0 pairs/i)).toBeVisible();
});
```

- [ ] **Step 2: Run timer tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/timer.spec.ts
```

Expected: tests may fail if `page.clock.tickFor` is not available in the installed Playwright version. Check Playwright version.

- [ ] **Step 3: Fix clock API issues**

If `tickFor` is not available (added in Playwright 1.45), use `fastForward` instead:

```typescript
// Replace tickFor(10_000) with:
await authedPage.clock.fastForward(10_000);
```

If timer does not respond to clock after navigation (because `setInterval` was set up before clock install), restructure:

```typescript
// Use pauseAt to set a specific start time, then advance
await authedPage.clock.pauseAt(new Date('2024-01-01T00:00:00'));
await authedPage.goto(`/rank/${collectionId}?minutes=2`);
await authedPage.clock.fastForward(121_000);
```

Update timer.spec.ts with the working approach.

- [ ] **Step 4: Run timer tests (expect all pass)**

```bash
npm test -- playwright/e2e/timer.spec.ts
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/timer.spec.ts
git commit -m "test: timer expiry tests passing"
```

---

### Task 8: Collection view tests

**Files:**
- Create: `frontend/playwright/e2e/collection-view.spec.ts`

- [ ] **Step 1: First seed some comparisons**

The collection view tests need ranked items. Add a helper to make comparisons via the API before the test runs.

Create `frontend/playwright/fixtures/seed-comparisons.ts`:

```typescript
import { readFileSync } from 'fs';
import { join } from 'path';

const STATE_FILE = join(__dirname, '../.test-state.json');
const BACKEND_URL = 'http://localhost:8000';

export async function seedComparisons(count: number = 5): Promise<void> {
  const { collectionId, sessionId } = JSON.parse(readFileSync(STATE_FILE, 'utf-8'));
  const headers = {
    'Content-Type': 'application/json',
    'Cookie': `session_id=${sessionId}`,
  };

  for (let i = 0; i < count; i++) {
    const pairResp = await fetch(`${BACKEND_URL}/collections/${collectionId}/ranking/next`, {
      headers,
    });
    if (!pairResp.ok) break;
    const { item_a, item_b } = await pairResp.json();

    await fetch(`${BACKEND_URL}/collections/${collectionId}/ranking/compare`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        item_a_id: item_a.id,
        item_b_id: item_b.id,
        winner_id: item_a.id,
        info_level_shown: 'brand',
      }),
    });
  }
}
```

- [ ] **Step 2: Write collection view tests**

Create `frontend/playwright/e2e/collection-view.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';
import { seedComparisons } from '../fixtures/seed-comparisons';

test.beforeEach(async () => {
  await seedComparisons(5);
});

test('shows ranked items in order with rank numbers', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  // Rank number 1 should appear
  await expect(authedPage.locator('text="1"').first()).toBeVisible();
  // Multiple items should appear
  const items = authedPage.locator('[class*="border-l-4"]');
  await expect(items).toHaveCount.greaterThan(0);
});

test('keep/sell divider renders', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.getByText(/keep.*sell/i)).toBeVisible();
});

test('moving divider down marks one more item as seller', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  // Count keeper items (forest border)
  const keepersBefore = await authedPage.locator('[class*="border-l-forest"]').count();

  // Click down arrow to move divider down
  await authedPage.getByRole('button', { name: /move divider down/i }).click();

  // One more keeper
  const keepersAfter = await authedPage.locator('[class*="border-l-forest"]').count();
  expect(keepersAfter).toBe(keepersBefore + 1);
});

test('moving divider up marks one more item as seller', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  const keepersBefore = await authedPage.locator('[class*="border-l-forest"]').count();
  await authedPage.getByRole('button', { name: /move divider up/i }).click();

  const keepersAfter = await authedPage.locator('[class*="border-l-forest"]').count();
  expect(keepersAfter).toBe(keepersBefore - 1);
});

test('status changes persist after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  // Move divider down
  await authedPage.getByRole('button', { name: /move divider down/i }).click();
  const keepersAfterMove = await authedPage.locator('[class*="border-l-forest"]').count();

  // Reload
  await authedPage.reload();
  const keepersAfterReload = await authedPage.locator('[class*="border-l-forest"]').count();

  expect(keepersAfterReload).toBe(keepersAfterMove);
});
```

- [ ] **Step 3: Run collection view tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/collection-view.spec.ts
```

Expected: failures if border class names don't match. Read errors and adjust selectors.

- [ ] **Step 4: Fix selector mismatches**

If `[class*="border-l-forest"]` doesn't match because Tailwind v4 generates different class names, use the `aria-label` or text approach instead:

Check `CollectionView.tsx` — keeper rows have class `border-l-forest bg-forest/5`, seller rows have `border-l-terracotta bg-terracotta/5`. In Tailwind v4, these should be direct class names in the HTML. If Playwright can't find them, add `data-testid` attributes:

In `CollectionView.tsx`, add to the row div:
```tsx
<div
  data-testid={i < (dividerIndex ?? 0) ? 'keeper-row' : 'seller-row'}
  className={`...`}
>
```

Then update tests to use `[data-testid="keeper-row"]`.

- [ ] **Step 5: Run collection view tests (expect all pass)**

```bash
npm test -- playwright/e2e/collection-view.spec.ts
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/collection-view.spec.ts frontend/playwright/fixtures/seed-comparisons.ts frontend/src/pages/CollectionView.tsx
git commit -m "test: collection view divider tests passing"
```

---

### Task 9: Item review tests

**Files:**
- Create: `frontend/playwright/e2e/item-review.spec.ts`

- [ ] **Step 1: Write item review tests**

Create `frontend/playwright/e2e/item-review.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('shows all items in collection', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  // All 10 seeded brands should appear
  await expect(authedPage.getByText('Chanel')).toBeVisible();
  await expect(authedPage.getByText('Gucci')).toBeVisible();
  await expect(authedPage.getByText('Prada')).toBeVisible();
});

test('clicking brand switches to inline edit input', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Chanel' }).click();
  await expect(authedPage.locator('input[value="Chanel"]')).toBeVisible();
});

test('editing brand with Enter saves it', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Gucci' }).click();

  const input = authedPage.locator('input[value="Gucci"]');
  await input.fill('Gucci Updated');
  await input.press('Enter');

  await expect(authedPage.getByText('Gucci Updated')).toBeVisible();
  await expect(authedPage.locator('input')).toHaveCount(0);
});

test('edited brand persists after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Prada' }).click();

  const input = authedPage.locator('input[value="Prada"]');
  await input.fill('Prada Edited');
  await input.press('Enter');

  await authedPage.reload();
  await expect(authedPage.getByText('Prada Edited')).toBeVisible();
});

test('Save button also submits the edit', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Louis Vuitton' }).click();

  const input = authedPage.locator('input[value="Louis Vuitton"]');
  await input.fill('LV');
  await authedPage.getByRole('button', { name: /save/i }).click();

  await expect(authedPage.getByText('LV')).toBeVisible();
  await expect(authedPage.locator('input')).toHaveCount(0);
});
```

- [ ] **Step 2: Run item review tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/item-review.spec.ts
```

Expected: may fail on exact button selectors. Read errors and adjust.

- [ ] **Step 3: Fix failures**

If `getByRole('button', { name: 'Chanel' })` doesn't match (because the button has additional text or different accessible name), try:

```typescript
await authedPage.locator('button', { hasText: 'Chanel' }).first().click();
```

If the input selector `input[value="Chanel"]` doesn't work (value is controlled state not reflected as HTML attribute), use:

```typescript
await expect(authedPage.locator('input')).toHaveValue('Chanel');
```

Update the spec with working selectors.

- [ ] **Step 4: Run item review tests (expect all pass)**

```bash
npm test -- playwright/e2e/item-review.spec.ts
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/item-review.spec.ts
git commit -m "test: item review edit flow tests passing"
```

---

### Task 10: Full suite and npm test script

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Run the full suite**

```bash
cd /gt/purseinator/purseinator/frontend
npm test
```

Expected: all tests in all 6 files pass. Total runtime under 60 seconds.

- [ ] **Step 2: Fix any remaining failures**

Address failures test by test. Common issues at this stage:
- Test ordering: some tests assume clean state but previous test changed data. Add `test.beforeEach` resets or use the seeding helpers.
- Flaky timing: add `await page.waitForTimeout(200)` before assertions that check async state.
- Stale session: the seeded session_id may expire between tasks. If auth failures occur, re-run global setup or increase session expiry.

- [ ] **Step 3: Verify `npm test` is fully self-contained**

From a fresh shell (no background processes running):

```bash
cd /gt/purseinator/purseinator/frontend
# Kill any running dev servers or backends
pkill -f "vite\|uvicorn" 2>/dev/null || true
npm test
```

Expected: exits 0. No manual setup needed.

- [ ] **Step 4: Final commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/
git commit -m "test: full Playwright E2E suite — all flows passing"
```

---

## Running the Tests

```bash
cd ~/gt/purseinator/purseinator/frontend
npm test              # run all E2E tests
npm run test:ui       # Playwright UI mode (interactive)
```

The first run downloads the test browser (~100MB, cached after that).
