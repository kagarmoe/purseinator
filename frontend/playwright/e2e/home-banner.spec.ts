import { test, expect } from '../fixtures/auth';
import { purseFixturePath } from '../fixtures/purse-fixtures';

const BACKEND = 'http://localhost:8000';

async function clearStaging(request: ReturnType<typeof test.info>['annotations'] extends never ? never : Parameters<Parameters<typeof test.beforeEach>[0]>[0]['request']) {
  while (true) {
    const resp = await request.get(`${BACKEND}/upload/staging?limit=200`);
    if (!resp.ok()) break;
    const { photos, has_more } = await resp.json();
    if (photos.length === 0) break;
    for (const p of photos) {
      await request.delete(`${BACKEND}/upload/staging/${p.id}`);
    }
    if (!has_more) break;
  }
}

test.beforeEach(async ({ authedPage }) => {
  await clearStaging(authedPage.request);
});

test('banner appears when staging non-empty', async ({ authedPage }) => {
  // Upload a photo to staging
  await authedPage.goto('/upload');
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([purseFixturePath('tan-tote')]);
  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(1, { timeout: 15000 });

  // Navigate to home
  await authedPage.goto('/');
  await expect(authedPage.getByText(/photo.*waiting to be grouped/i)).toBeVisible({ timeout: 5000 });
});

test('banner clears when staging empty', async ({ authedPage }) => {
  // Staging is already cleared by beforeEach
  await authedPage.goto('/');
  await expect(authedPage.getByText(/waiting to be grouped/i)).not.toBeVisible({ timeout: 5000 });
});

test('banner shows count correctly', async ({ authedPage }) => {
  // Upload 2 photos
  await authedPage.goto('/upload');
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([
    purseFixturePath('tan-tote'),
    purseFixturePath('black-tote'),
  ]);
  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(2, { timeout: 15000 });

  // Navigate to home and verify banner count
  await authedPage.goto('/');
  await expect(authedPage.getByText(/2 photos waiting to be grouped/i)).toBeVisible({ timeout: 5000 });
});
