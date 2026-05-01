import { readFileSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const STATE_FILE = `${__dirname}/../.test-state.json`;
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
    if (!item_a || !item_b) break;
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
