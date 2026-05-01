import { test, expect } from '../fixtures/auth';
import { purseFixturePath } from '../fixtures/purse-fixtures';

const BACKEND = 'http://localhost:8000';

/** Clear all staging photos for the current user using Playwright's request context (which has the session cookie). */
async function clearStagingViaPage(request: Parameters<Parameters<typeof test.beforeEach>[0]>[0]['request']) {
  // eslint-disable-next-line no-constant-condition
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
  // Navigate to upload page to ensure the session is active
  await clearStagingViaPage(authedPage.request);
});

test('inbox upload + group flow', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/upload');
  await expect(authedPage.getByRole('heading', { name: /upload/i })).toBeVisible();

  // Upload 3 fixture PNGs
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([
    purseFixturePath('tan-tote'),
    purseFixturePath('black-tote'),
    purseFixturePath('red-tote'),
  ]);

  // Wait for 3 tiles to appear
  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(3, { timeout: 15000 });

  // Select all 3
  for (const tile of await authedPage.locator('[role="checkbox"]').all()) {
    await tile.click();
  }

  // Click Group
  await authedPage.getByRole('button', { name: /group as one purse/i }).click();

  // Modal opens — pick existing collection by its radio
  await expect(authedPage.getByRole('dialog')).toBeVisible({ timeout: 5000 });
  const radios = authedPage.locator('[role="radiogroup"] input[type="radio"]');
  await radios.first().click();

  await authedPage.getByRole('button', { name: /group \d+ photos/i }).click();

  // Assert success toast
  await expect(authedPage.getByText(/grouped 3 photos/i)).toBeVisible({ timeout: 10000 });

  // Grid should be empty
  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(0, { timeout: 10000 });
});

test('discard one photo via icon button', async ({ authedPage }) => {
  await authedPage.goto('/upload');

  // Upload 2 photos
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([
    purseFixturePath('tan-tote'),
    purseFixturePath('black-tote'),
  ]);

  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(2, { timeout: 15000 });

  // Discard one via the × button
  await authedPage.getByRole('button', { name: 'Discard photo' }).first().click();

  // Wait for only 1 remaining
  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(1, { timeout: 10000 });
});

test('?suggest=<cid> preselects the modal', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/upload?suggest=${collectionId}`);

  // Upload 1 photo
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([purseFixturePath('tan-tote')]);

  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(1, { timeout: 15000 });

  // Select it
  await authedPage.locator('[role="checkbox"]').first().click();

  // Open group modal
  await authedPage.getByRole('button', { name: /group as one purse/i }).click();
  await expect(authedPage.getByRole('dialog')).toBeVisible({ timeout: 5000 });

  // The collection matching collectionId should be pre-selected
  const radio = authedPage.locator(`input[type="radio"][value="${collectionId}"]`);
  await expect(radio).toBeChecked({ timeout: 5000 });

  // Group it
  await authedPage.getByRole('button', { name: /group \d+ photos/i }).click();

  // After success, URL should strip param
  await expect(authedPage).toHaveURL('/upload', { timeout: 10000 });
});

test('inbox upload + group via inline new collection', async ({ authedPage }) => {
  await authedPage.goto('/upload');

  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([
    purseFixturePath('tan-satchel'),
    purseFixturePath('black-satchel'),
  ]);

  await expect(authedPage.locator('[role="checkbox"]')).toHaveCount(2, { timeout: 15000 });

  // Select both
  for (const tile of await authedPage.locator('[role="checkbox"]').all()) {
    await tile.click();
  }

  await authedPage.getByRole('button', { name: /group as one purse/i }).click();
  await expect(authedPage.getByRole('dialog')).toBeVisible({ timeout: 5000 });

  // Expand new collection form
  await authedPage.getByText(/\+ new collection/i).click();
  await authedPage.getByPlaceholder(/collection name/i).fill('Playwright Test Collection');

  await authedPage.getByRole('button', { name: /^create$/i }).click();

  // Should succeed and show toast
  await expect(authedPage.getByText(/grouped 2 photos/i)).toBeVisible({ timeout: 15000 });
});
