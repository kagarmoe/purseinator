# Frontend TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Playwright E2E tests covering every critical user flow so that `npm test` passing means the app is shippable.

**Architecture:** Playwright E2E tests run against the real full stack — Vite dev server (port 5173) + FastAPI backend (port 8000) + SQLite test DB. Global setup starts the backend, runs migrations, and seeds a collection with 10 items. No mocking. Tests surface real app bugs; fix the app until every test passes.

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
      seed-comparisons.ts                  ← seeds comparisons for collection-view tests
    e2e/
      auth.spec.ts
      collections.spec.ts
      ranking.spec.ts
      timer.spec.ts
      collection-view.spec.ts
      item-review.spec.ts

frontend/src/
  pages/Verify.tsx                         ← NEW: magic-link token verification page
  pages/Home.tsx                           ← MODIFY: add magic-link form
  pages/Dashboard.tsx                      ← MODIFY: auth redirect + View Rankings button
  App.tsx                                  ← MODIFY: add /verify route
```

Modify:
- `frontend/package.json` — add `test` script and Playwright devDependency
- `frontend/.gitignore` — ignore test artifacts

---

### Task 1: Fix app bugs surfaced by test design

These are real bugs the E2E tests will expose. Fix them before writing tests so the tests can be written to match correct behavior.

**Files:**
- Modify: `frontend/src/pages/Home.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Verify.tsx`

- [ ] **Step 1: Add magic-link form and fix dev-login navigation in Home.tsx**

Replace the entire `Home.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { devLogin, getCollections, getMe, requestMagicLink } from "../api";

interface Collection {
  id: number;
  name: string;
  description: string;
}

const IS_DEV = import.meta.env.DEV;

export default function Home() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  useEffect(() => {
    Promise.all([getMe(), getCollections()])
      .then(([me, colls]) => {
        setUser(me);
        setCollections(colls);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await requestMagicLink(email);
      setMagicLinkSent(true);
    } catch {
      alert("Could not send magic link — is the server running?");
    }
  };

  const handleDevLogin = async () => {
    try {
      const result = await devLogin();
      document.cookie = `session_id=${result.session_id}; path=/`;
      navigate("/dashboard");
    } catch {
      alert("Dev login failed — is the server running?");
    }
  };

  if (loading) {
    return (
      <div className="min-h-svh bg-cream flex items-center justify-center">
        <div className="space-y-3 w-full max-w-sm px-6">
          <div className="h-8 bg-dusty-rose/30 rounded animate-pulse" />
          <div className="h-4 bg-dusty-rose/20 rounded w-3/4 animate-pulse" />
          <div className="h-24 bg-dusty-rose/30 rounded animate-pulse" />
          <div className="h-24 bg-dusty-rose/30 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-svh bg-cream flex flex-col items-center justify-center px-6">
        <div className="text-center max-w-xs w-full">
          <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-4">
            The Collection Edit
          </p>
          <h1 className="font-serif text-5xl text-near-black mb-6 leading-none">
            PURSEINATOR
          </h1>
          <p className="text-muted text-sm mb-10 font-sans">
            Sign in to start curating your collection.
          </p>

          {magicLinkSent ? (
            <p className="text-muted text-sm font-sans">
              Check your email for a sign-in link.
            </p>
          ) : (
            <form onSubmit={handleMagicLink} className="space-y-4 w-full">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="w-full border-b border-muted bg-transparent text-near-black font-sans text-sm px-0 py-2 outline-none focus:border-terracotta transition-colors placeholder:text-muted/50"
              />
              <button
                type="submit"
                className="w-full bg-terracotta text-white font-sans text-sm font-medium py-3 hover:bg-terracotta/80 transition-colors cursor-pointer"
              >
                Send Link
              </button>
            </form>
          )}

          {IS_DEV && (
            <button
              onClick={handleDevLogin}
              className="mt-6 px-8 py-3 border-2 border-dashed border-terracotta text-terracotta text-sm font-sans font-medium rounded-full hover:bg-terracotta hover:text-white transition-colors cursor-pointer"
            >
              Dev Login
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-cream">
      <header className="px-6 pt-12 pb-8 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-2">
          The Collection Edit
        </p>
        <h1 className="font-serif text-4xl text-near-black leading-tight">
          PURSEINATOR
        </h1>
        <p className="text-muted text-sm mt-2 font-sans">
          Welcome back, {user.name}.
        </p>
      </header>

      <main className="px-6 py-8 max-w-lg mx-auto">
        <h2 className="text-xs uppercase tracking-[0.2em] text-muted font-sans mb-6">
          Your Collections
        </h2>

        {collections.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">
            No collections yet. Ask your operator to set one up.
          </p>
        ) : (
          <div className="space-y-3">
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/session/${c.id}`)}
                className="group w-full text-left bg-dusty-rose/20 border-l-4 border-l-terracotta border border-dusty-rose px-6 py-5 hover:bg-dusty-rose/40 transition-colors cursor-pointer"
              >
                <div className="font-serif text-lg text-near-black group-hover:text-terracotta transition-colors">{c.name}</div>
                {c.description && (
                  <div className="text-muted text-xs font-sans mt-1">{c.description}</div>
                )}
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Fix Dashboard.tsx — add auth redirect and View Rankings button**

Replace the entire `Dashboard.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCollections, getMe } from "../api";

interface Collection {
  id: number;
  name: string;
  description: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);

  useEffect(() => {
    Promise.all([getMe(), getCollections()])
      .then(([me, colls]) => {
        setUser(me);
        setCollections(colls);
      })
      .catch(() => navigate("/"));
  }, []);

  if (!user) {
    return (
      <div className="min-h-svh bg-cream flex items-center justify-center">
        <p className="text-muted text-sm font-sans">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
          Operator
        </p>
        <h1 className="font-serif text-3xl text-near-black leading-tight">Dashboard</h1>
      </header>

      <main className="px-6 py-8 max-w-2xl mx-auto">
        <h2 className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-6">
          Collections
        </h2>

        {collections.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">
            No collections yet. Use the CLI to create one.
          </p>
        ) : (
          <div className="divide-y divide-cream">
            {collections.map((c) => (
              <div
                key={c.id}
                className="py-4 flex items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="font-serif text-base text-near-black">{c.name}</div>
                  {c.description && (
                    <div className="text-muted text-xs font-sans mt-0.5">{c.description}</div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => navigate(`/collection/${c.id}`)}
                    className="text-xs font-sans uppercase tracking-[0.1em] border border-cobalt text-cobalt px-4 py-2 hover:bg-cobalt hover:text-white transition-colors cursor-pointer"
                  >
                    View Rankings
                  </button>
                  <button
                    onClick={() => navigate(`/review/${c.id}`)}
                    className="text-xs font-sans uppercase tracking-[0.1em] bg-terracotta text-white px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer"
                  >
                    Review Items
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Create Verify.tsx — magic-link token verification page**

Create `frontend/src/pages/Verify.tsx`:

```typescript
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { verifyToken } from "../api";

export default function Verify() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      navigate("/");
      return;
    }
    verifyToken(token)
      .then((data) => {
        document.cookie = `session_id=${data.session_id}; path=/`;
        navigate("/");
      })
      .catch(() =>
        setError("Invalid or expired link. Please request a new one.")
      );
  }, []);

  if (error) {
    return (
      <div className="min-h-svh bg-cream flex items-center justify-center px-6">
        <div className="text-center max-w-xs">
          <p className="text-terracotta text-sm font-sans">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 text-muted text-xs font-sans underline cursor-pointer"
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-cream flex items-center justify-center">
      <p className="text-muted text-sm font-sans">Signing you in…</p>
    </div>
  );
}
```

- [ ] **Step 4: Add /verify route to App.tsx**

Replace `App.tsx` with:

```typescript
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import SessionPicker from "./pages/SessionPicker";
import RankingSession from "./pages/RankingSession";
import CollectionView from "./pages/CollectionView";
import Dashboard from "./pages/Dashboard";
import ItemReview from "./pages/ItemReview";
import Verify from "./pages/Verify";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/verify" element={<Verify />} />
        <Route path="/session/:collectionId" element={<SessionPicker />} />
        <Route path="/rank/:collectionId" element={<RankingSession />} />
        <Route path="/collection/:collectionId" element={<CollectionView />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/review/:collectionId" element={<ItemReview />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 5: Build to verify no TypeScript errors**

```bash
cd /gt/purseinator/purseinator/frontend
npm run build
```

Expected: exits 0 with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/src/
git commit -m "fix: auth redirect, magic-link form, verify page, dashboard view rankings"
```

---

### Task 2: Install Playwright and write config

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

Expected: `@playwright/test` in `package.json` devDependencies, chromium downloaded.

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

- [ ] **Step 3: Add test scripts to package.json**

In `frontend/package.json`, add to `"scripts"`:

```json
"test": "playwright test",
"test:ui": "playwright test --ui"
```

- [ ] **Step 4: Update .gitignore**

Append to `frontend/.gitignore` (create if missing):

```
test-results/
playwright-report/
playwright/.test-state.json
playwright/.backend.pid
```

- [ ] **Step 5: Verify config parses**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- --list
```

Expected: exits 0, "No tests found" (config parsed, no specs yet).

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/package.json frontend/package-lock.json frontend/playwright.config.ts frontend/.gitignore
git commit -m "test: install Playwright and configure E2E runner"
```

---

### Task 3: Global setup — start backend and seed test data

**Files:**
- Create: `frontend/playwright/global-setup.ts`
- Create: `frontend/playwright/global-teardown.ts`

- [ ] **Step 1: Create directories**

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
  if (existsSync(TEST_DB_PATH)) unlinkSync(TEST_DB_PATH);

  execSync('alembic upgrade head', {
    cwd: APP_DIR,
    env: { ...process.env, PURSEINATOR_DATABASE_URL: `sqlite+aiosqlite:///${TEST_DB_PATH}` },
    stdio: 'inherit',
  });

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
    try { process.kill(-pid, 'SIGTERM'); } catch {}
    unlinkSync(PID_FILE);
  }
  if (existsSync(STATE_FILE)) unlinkSync(STATE_FILE);
  if (existsSync(TEST_DB_PATH)) unlinkSync(TEST_DB_PATH);
}
```

- [ ] **Step 4: Verify setup runs**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- --list
```

Expected: "✓ Backend seeded. Collection ID: 1" prints, exits 0.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/global-setup.ts frontend/playwright/global-teardown.ts
git commit -m "test: global setup starts backend and seeds test data"
```

---

### Task 4: Auth fixtures

**Files:**
- Create: `frontend/playwright/fixtures/auth.ts`

- [ ] **Step 1: Write auth fixture**

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
    await context.addCookies([{
      name: 'session_id',
      value: state.sessionId,
      domain: 'localhost',
      path: '/',
      sameSite: 'Lax',
    }]);
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

### Task 5: Auth flow tests

Covers dev-login flow AND magic-link flow (both must work).

**Files:**
- Create: `frontend/playwright/e2e/auth.spec.ts`

- [ ] **Step 1: Write auth tests**

Create `frontend/playwright/e2e/auth.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

// --- Unauthenticated access ---

test('unauthenticated user visiting /dashboard is redirected to /', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL('/');
});

// --- Magic-link form ---

test('home page shows email input and Send Link button', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.getByRole('button', { name: /send link/i })).toBeVisible();
});

test('submitting email shows check-your-email confirmation', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type="email"]').fill('playwright@test.com');
  await page.getByRole('button', { name: /send link/i }).click();
  await expect(page.getByText(/check your email/i)).toBeVisible();
});

test('verify token route sets session and redirects to home logged in', async ({ page }) => {
  // The backend always returns the token (no email delivery in test env)
  const resp = await page.request.post('/auth/magic-link', {
    data: { email: 'playwright@test.com' },
  });
  expect(resp.ok()).toBe(true);
  const { token } = await resp.json();

  await page.goto(`/verify?token=${token}`);

  // After verify, lands on home and shows logged-in state (welcome message)
  await expect(page.getByText(/welcome back/i)).toBeVisible();
});

test('verify route with invalid token shows error message', async ({ page }) => {
  await page.goto('/verify?token=invalid-token-xyz');
  await expect(page.getByText(/invalid or expired/i)).toBeVisible();
});

// --- Dev Login (dev mode only) ---

test('Dev Login button creates session and navigates to dashboard', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /dev login/i }).click();
  await expect(page).toHaveURL('/dashboard');
  await expect(page.getByText('Dashboard')).toBeVisible();
});
```

- [ ] **Step 2: Run auth tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/auth.spec.ts
```

Expected: all 6 tests pass. If any fail, read the error message carefully.

- [ ] **Step 3: Fix failures**

**"redirected to /" fails:** `Dashboard.tsx` catch navigates to `/` but the component renders "Loading…" before the catch fires. If the URL shows `/dashboard` when you check, the `navigate('/')` in `catch` is not running. Verify the `useEffect` catch block calls `navigate('/')` as implemented in Task 1.

**"verify token" fails with network error:** The Vite proxy must forward `/auth/magic-link`. Check `vite.config.ts` — it should already proxy `/auth`. If Vite dev server isn't running, start it first.

**"Dev Login" button not visible:** The button only renders when `import.meta.env.DEV` is true. In `npm run dev`, `DEV` is true. In a production build it won't appear. Verify you're running `npm run dev`, not a built file.

- [ ] **Step 4: Run auth tests (expect all pass)**

```bash
npm test -- playwright/e2e/auth.spec.ts
```

Expected: 6/6 PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/auth.spec.ts
git commit -m "test: auth flow tests passing — magic-link and dev-login"
```

---

### Task 6: Collection listing tests

**Files:**
- Create: `frontend/playwright/e2e/collections.spec.ts`

- [ ] **Step 1: Write collection listing tests**

Create `frontend/playwright/e2e/collections.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('dashboard shows seeded collection by name', async ({ authedPage }) => {
  await authedPage.goto('/dashboard');
  await expect(authedPage.getByText('Test Collection')).toBeVisible();
});

test('View Rankings button navigates to /collection/:id', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await authedPage.getByRole('button', { name: /view rankings/i }).click();
  await expect(authedPage).toHaveURL(`/collection/${collectionId}`);
});

test('Review Items button navigates to /review/:id', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await authedPage.getByRole('button', { name: /review items/i }).click();
  await expect(authedPage).toHaveURL(`/review/${collectionId}`);
});

test('empty state shown on dashboard when no collections exist', async ({ page }) => {
  // Log in as a fresh user (magic link creates a new curator account)
  const resp = await page.request.post('/auth/magic-link', {
    data: { email: 'empty@test.com' },
  });
  const { token } = await resp.json();
  const verifyResp = await page.request.get(`/auth/verify?token=${token}`);
  const { session_id } = await verifyResp.json();

  await page.context().addCookies([{
    name: 'session_id',
    value: session_id,
    domain: 'localhost',
    path: '/',
    sameSite: 'Lax',
  }]);

  await page.goto('/');
  await expect(page.getByText(/no collections yet/i)).toBeVisible();
});
```

- [ ] **Step 2: Run collection tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/collections.spec.ts
```

Expected: 4/4 pass.

- [ ] **Step 3: Fix failures**

**"empty state" test: `/` shows loading then empty state but you see logged-in state from the seeded session:** The empty state test creates a fresh user with no collections. If the seeded session cookie leaks between tests, the wrong user's collections show up. Playwright test isolation should prevent this — each test gets a fresh context. If leaking occurs, add `test.use({ storageState: { cookies: [], origins: [] } })` at the top of that test.

- [ ] **Step 4: Run collection tests (all pass)**

```bash
npm test -- playwright/e2e/collections.spec.ts
```

Expected: 4/4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/collections.spec.ts
git commit -m "test: collection listing and navigation tests passing"
```

---

### Task 7: Ranking session tests

**Files:**
- Create: `frontend/playwright/e2e/ranking.spec.ts`

- [ ] **Step 1: Write ranking tests**

Create `frontend/playwright/e2e/ranking.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test.describe('ranking session', () => {
  test('shows a comparison pair on load', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    // Two clickable item cards
    const cards = authedPage.locator('button[class*="flex-1"]');
    await expect(cards).toHaveCount(2);
  });

  test('picking an item increments the counter', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    await expect(authedPage.getByText('0 compared')).toBeVisible();

    const cards = authedPage.locator('button[class*="flex-1"]');
    await cards.first().click();

    await expect(authedPage.getByText('1 compared')).toBeVisible();
  });

  test('a new pair loads after each pick', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    const cards = authedPage.locator('button[class*="flex-1"]');
    await cards.first().click();

    // Counter shows 1, new pair is visible
    await expect(authedPage.getByText('1 compared')).toBeVisible();
    await expect(authedPage.locator('button[class*="flex-1"]')).toHaveCount(2);
  });

  test('Done button shows completion screen with correct count', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    const cards = authedPage.locator('button[class*="flex-1"]');
    await cards.first().click();
    await expect(authedPage.getByText('1 compared')).toBeVisible();

    await cards.first().click();
    await expect(authedPage.getByText('2 compared')).toBeVisible();

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

  test('Another Session navigates to session picker', async ({ authedPage, collectionId }) => {
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

Expected: may fail on `button[class*="flex-1"]` selector if Tailwind generates different class strings.

- [ ] **Step 3: Fix selector if needed**

If `button[class*="flex-1"]` doesn't match, add `data-testid` to `ComparisonCard.tsx`:

```tsx
// In ItemCard button, add:
data-testid="item-card"
```

Then update the selector in ranking.spec.ts:
```typescript
const cards = authedPage.locator('[data-testid="item-card"]');
```

- [ ] **Step 4: Run ranking tests (all pass)**

```bash
npm test -- playwright/e2e/ranking.spec.ts
```

Expected: 6/6 PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/ranking.spec.ts frontend/src/components/ComparisonCard.tsx
git commit -m "test: ranking session flow tests passing"
```

---

### Task 8: Timer tests

**Files:**
- Create: `frontend/playwright/e2e/timer.spec.ts`

- [ ] **Step 1: Write timer tests**

Create `frontend/playwright/e2e/timer.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('session auto-completes when timer hits zero', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  await expect(authedPage.getByText('2:00')).toBeVisible();

  await authedPage.clock.fastForward(121_000);

  await expect(authedPage.getByText(/session complete/i)).toBeVisible();
});

test('timer counts down each second', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  await expect(authedPage.getByText('2:00')).toBeVisible();

  await authedPage.clock.fastForward(10_000);

  await expect(authedPage.getByText('1:50')).toBeVisible();
});

test('completion screen shows zero pairs when no comparisons made before expiry', async ({ authedPage, collectionId }) => {
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

Expected: may fail if `page.clock.install()` must be called before navigation. Read error.

- [ ] **Step 3: Fix clock ordering if needed**

If the timer doesn't respond to `fastForward` because the `setInterval` was set up before the clock was installed, use `pauseAt` to freeze time before navigation:

```typescript
// Replace clock.install() with:
await authedPage.clock.pauseAt(new Date('2024-01-01T00:00:00'));
await authedPage.goto(`/rank/${collectionId}?minutes=2`);
await authedPage.clock.fastForward(121_000);
```

Update all three tests in timer.spec.ts with this pattern if needed.

- [ ] **Step 4: Run timer tests (all pass)**

```bash
npm test -- playwright/e2e/timer.spec.ts
```

Expected: 3/3 PASS.

- [ ] **Step 5: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/timer.spec.ts
git commit -m "test: timer expiry tests passing"
```

---

### Task 9: Collection view tests

**Files:**
- Create: `frontend/playwright/fixtures/seed-comparisons.ts`
- Create: `frontend/playwright/e2e/collection-view.spec.ts`
- Possibly modify: `frontend/src/pages/CollectionView.tsx` (add data-testid)

- [ ] **Step 1: Write seed-comparisons helper**

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
    const pairResp = await fetch(`${BACKEND_URL}/collections/${collectionId}/ranking/next`, { headers });
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

- [ ] **Step 2: Add data-testid to CollectionView rows**

In `frontend/src/pages/CollectionView.tsx`, add `data-testid` to the row div (line ~74):

```tsx
<div
  data-testid={i < (dividerIndex ?? 0) ? 'keeper-row' : 'seller-row'}
  className={`flex items-center gap-4 py-4 border-l-4 pl-4 mb-0.5 ${
    i < (dividerIndex ?? 0)
      ? "border-l-forest bg-forest/5"
      : "border-l-terracotta bg-terracotta/5"
  }`}
>
```

- [ ] **Step 3: Write collection view tests**

Create `frontend/playwright/e2e/collection-view.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';
import { seedComparisons } from '../fixtures/seed-comparisons';

test.beforeAll(async () => {
  await seedComparisons(8);
});

test('shows ranked items with rank numbers', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.locator('text="1"').first()).toBeVisible();
  const rows = authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]');
  expect(await rows.count()).toBeGreaterThan(0);
});

test('keep/sell divider renders', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.getByText(/keep.*sell/i)).toBeVisible();
});

test('moving divider down marks one more item as keeper', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  const keepersBefore = await authedPage.locator('[data-testid="keeper-row"]').count();
  await authedPage.getByRole('button', { name: /move divider down/i }).click();

  await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(keepersBefore + 1);
});

test('moving divider up marks one more item as seller', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  const keepersBefore = await authedPage.locator('[data-testid="keeper-row"]').count();

  // Only move up if there's at least one keeper to move
  if (keepersBefore > 0) {
    await authedPage.getByRole('button', { name: /move divider up/i }).click();
    await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(keepersBefore - 1);
  } else {
    // Divider is already at top — this test is a no-op in this state
    test.skip();
  }
});

test('status changes persist after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);

  await authedPage.getByRole('button', { name: /move divider down/i }).click();
  const keepersAfterMove = await authedPage.locator('[data-testid="keeper-row"]').count();

  await authedPage.reload();
  await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(keepersAfterMove);
});
```

- [ ] **Step 4: Run collection view tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/collection-view.spec.ts
```

Expected: 5/5 pass.

- [ ] **Step 5: Fix failures**

If `toHaveCount(keepersBefore + 1)` is flaky because the divider state mutation persists between tests (tests share DB state): add an explicit wait for the UI to reflect the new count before asserting. Also ensure `beforeAll` rather than `beforeEach` is used so comparisons only seed once.

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/collection-view.spec.ts frontend/playwright/fixtures/seed-comparisons.ts frontend/src/pages/CollectionView.tsx
git commit -m "test: collection view divider tests passing"
```

---

### Task 10: Item review tests

**Files:**
- Create: `frontend/playwright/e2e/item-review.spec.ts`

- [ ] **Step 1: Write item review tests**

Create `frontend/playwright/e2e/item-review.spec.ts`:

```typescript
import { test, expect } from '../fixtures/auth';

test('shows all seeded items', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await expect(authedPage.getByRole('button', { name: 'Chanel' })).toBeVisible();
  await expect(authedPage.getByRole('button', { name: 'Gucci' })).toBeVisible();
  await expect(authedPage.getByRole('button', { name: 'Prada' })).toBeVisible();
});

test('clicking brand opens inline edit input', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Chanel' }).click();
  await expect(authedPage.locator('input')).toBeVisible();
  await expect(authedPage.locator('input')).toHaveValue('Chanel');
});

test('pressing Enter saves the new brand', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Gucci' }).click();
  await authedPage.locator('input').fill('Gucci Edited');
  await authedPage.locator('input').press('Enter');

  await expect(authedPage.getByRole('button', { name: 'Gucci Edited' })).toBeVisible();
  await expect(authedPage.locator('input')).toHaveCount(0);
});

test('edited brand persists after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Prada' }).click();
  await authedPage.locator('input').fill('Prada Edited');
  await authedPage.locator('input').press('Enter');

  await authedPage.reload();
  await expect(authedPage.getByRole('button', { name: 'Prada Edited' })).toBeVisible();
});

test('Save button also submits the edit', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Louis Vuitton' }).click();
  await authedPage.locator('input').fill('LV');
  await authedPage.getByRole('button', { name: /save/i }).click();

  await expect(authedPage.getByRole('button', { name: 'LV' })).toBeVisible();
  await expect(authedPage.locator('input')).toHaveCount(0);
});
```

- [ ] **Step 2: Run item review tests**

```bash
cd /gt/purseinator/purseinator/frontend
npm test -- playwright/e2e/item-review.spec.ts
```

Expected: 5/5 pass. If `getByRole('button', { name: 'Chanel' })` doesn't match (the brand button may include title text), use:

```typescript
await authedPage.locator('button', { hasText: 'Chanel' }).first().click();
```

- [ ] **Step 3: Run item review tests (all pass)**

```bash
npm test -- playwright/e2e/item-review.spec.ts
```

Expected: 5/5 PASS.

- [ ] **Step 4: Commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/playwright/e2e/item-review.spec.ts
git commit -m "test: item review edit flow tests passing"
```

---

### Task 11: Full suite

**Files:** none new

- [ ] **Step 1: Run the complete suite**

```bash
cd /gt/purseinator/purseinator/frontend
npm test
```

Expected: all 29 tests across 6 files pass. Total runtime under 90 seconds.

- [ ] **Step 2: Fix any remaining failures**

Address failures test by test. If tests leave DB in unexpected state for later tests, add explicit state resets or seed fresh data at the start of the affected spec.

- [ ] **Step 3: Verify `npm test` is self-contained**

From a shell with no background processes:

```bash
cd /gt/purseinator/purseinator/frontend
pkill -f "vite\|uvicorn" 2>/dev/null || true
npm test
```

Expected: exits 0. No manual setup needed.

- [ ] **Step 4: Final commit**

```bash
cd /gt/purseinator/purseinator
git add frontend/
git commit -m "test: full Playwright E2E suite — all 29 flows passing"
```

---

## Running the Tests

```bash
cd ~/gt/purseinator/purseinator/frontend
npm test              # run all E2E tests
npm run test:ui       # Playwright UI mode (interactive)
```

The first run downloads the test browser (~100MB, cached after that). No background processes needed — `npm test` handles everything.
