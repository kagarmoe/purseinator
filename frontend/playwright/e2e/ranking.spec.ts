import { test, expect } from '../fixtures/auth';

test.describe('ranking session', () => {
  test('shows a comparison pair on load', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    const cards = authedPage.locator('button[class*="flex-1"]');
    await expect(cards).toHaveCount(2);
  });

  test('picking an item increments the counter', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);
    await expect(authedPage.getByText('0 compared')).toBeVisible();

    const cards = authedPage.locator('button[class*="flex-1"]');
    await expect(cards).toHaveCount(2);
    await cards.first().click();

    await expect(authedPage.getByText('1 compared')).toBeVisible();
  });

  test('a new pair loads after each pick', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    const cards = authedPage.locator('button[class*="flex-1"]');
    await expect(cards).toHaveCount(2);
    await cards.first().click();

    await expect(authedPage.getByText('1 compared')).toBeVisible();
    await expect(authedPage.locator('button[class*="flex-1"]')).toHaveCount(2);
  });

  test('Done button shows completion screen with correct count', async ({ authedPage, collectionId }) => {
    await authedPage.goto(`/rank/${collectionId}?minutes=2`);

    const cards = authedPage.locator('button[class*="flex-1"]');
    await expect(cards).toHaveCount(2);
    await cards.first().click();
    await expect(authedPage.getByText('1 compared')).toBeVisible();

    await expect(cards).toHaveCount(2);
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
