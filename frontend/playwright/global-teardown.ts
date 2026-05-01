import { readFileSync, unlinkSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
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
