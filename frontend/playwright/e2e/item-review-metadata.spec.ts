import { test, expect } from '../fixtures/auth';
import { purseFixturePath } from '../fixtures/purse-fixtures';

test('metadata save flow — color + style + Save button', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await expect(authedPage.getByRole('heading', { name: /item review/i })).toBeVisible({ timeout: 5000 });

  // Wait for items to load
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible({ timeout: 10000 });

  // Click the first item's primary color selector
  const firstCard = authedPage.locator('[data-testid="item-card"]').first();
  const primarySelect = firstCard.getByLabel(/primary color/i);
  await primarySelect.selectOption('red');

  // Click Save
  const saveBtn = firstCard.getByRole('button', { name: /save/i }).last();

  // Listen for the PATCH request
  const patchPromise = authedPage.waitForRequest(
    (req) => req.method() === 'PATCH' && req.url().includes('/items/'),
    { timeout: 10000 }
  );
  await saveBtn.click();

  const patchReq = await patchPromise;
  expect(patchReq.postDataJSON()).toMatchObject({ primary_color: 'red' });

  // Should show "Saved" indicator
  await expect(firstCard.getByText(/saved/i)).toBeVisible({ timeout: 5000 });
});

test('multi-color rule — primary=multi disables accents', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible({ timeout: 10000 });

  const firstCard = authedPage.locator('[data-testid="item-card"]').first();
  const primarySelect = firstCard.getByLabel(/primary color/i);
  await primarySelect.selectOption('multi');

  // Accents picker should be disabled
  const accentsGroup = firstCard.getByRole('group', { name: /accent colors/i });
  await expect(accentsGroup).toHaveAttribute('aria-disabled', 'true', { timeout: 3000 });
});

test('add photos to existing item', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible({ timeout: 10000 });

  const firstCard = authedPage.locator('[data-testid="item-card"]').first();

  // Click "+ Add photos"
  const addPhotosInput = firstCard.locator('input[type="file"]').first();

  // Upload a photo via the file input
  await addPhotosInput.setInputFiles([purseFixturePath('tan-tote')]);

  // Should show a new thumbnail
  await expect(firstCard.locator('img[src*="/photos/"]')).toBeVisible({ timeout: 15000 });
});
