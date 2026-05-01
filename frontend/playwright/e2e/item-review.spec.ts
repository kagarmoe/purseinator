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
