import { test, expect } from '../fixtures/auth';

// Tests 3-5 mutate seeded brand names (Gucci, Prada, Louis Vuitton).
// Test 1 must run first (declaration order guaranteed by workers: 1).

test('shows all seeded items', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await expect(authedPage.getByRole('button', { name: 'Chanel' })).toBeVisible();
  await expect(authedPage.getByRole('button', { name: 'Gucci' })).toBeVisible();
  await expect(authedPage.getByRole('button', { name: 'Prada' })).toBeVisible();
});

test('clicking brand opens inline edit input', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Chanel' }).click();
  await expect(authedPage.locator('input').first()).toBeVisible();
  await expect(authedPage.locator('input').first()).toHaveValue('Chanel');
});

test('pressing Enter saves the new brand', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Gucci' }).click();
  // Find the brand input (border-terracotta class) — specifically the brand edit input
  const brandInput = authedPage.locator('input.font-serif').first();
  await brandInput.fill('Gucci Edited');
  await brandInput.press('Enter');

  await expect(authedPage.getByRole('button', { name: 'Gucci Edited' })).toBeVisible();
  // Brand input should be gone (no longer in editing mode)
  await expect(authedPage.locator('input.font-serif')).toHaveCount(0);
});

test('edited brand persists after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Prada' }).click();
  const brandInput = authedPage.locator('input.font-serif').first();
  await brandInput.fill('Prada Edited');
  await brandInput.press('Enter');

  await authedPage.reload();
  await expect(authedPage.getByRole('button', { name: 'Prada Edited' })).toBeVisible();
});

test('Save button also submits the edit', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/review/${collectionId}`);
  await authedPage.getByRole('button', { name: 'Louis Vuitton' }).click();
  const brandInput = authedPage.locator('input.font-serif').first();
  await brandInput.fill('LV');
  // Click the brand-specific Save button (the first one, which is inside the brand editing row)
  const brandCard = authedPage.locator('[data-testid="item-card"]').filter({ has: brandInput });
  await brandCard.locator('.font-serif + button, button.shrink-0').first().click();

  await expect(authedPage.getByRole('button', { name: 'LV' })).toBeVisible();
  await expect(authedPage.locator('input.font-serif')).toHaveCount(0);
});
