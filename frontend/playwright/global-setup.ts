import { execSync, spawn } from 'child_process';
import { writeFileSync, existsSync, unlinkSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
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
