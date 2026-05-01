import { test as base, Page } from '@playwright/test';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
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
