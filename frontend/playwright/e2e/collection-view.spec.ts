import { test, expect } from '../fixtures/auth';
import { seedComparisons } from '../fixtures/seed-comparisons';

test.beforeAll(async () => {
  await seedComparisons(8);
});

test('shows ranked items with rank numbers', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.getByText('1', { exact: true }).first()).toBeVisible();
  const rows = authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]');
  expect(await rows.count()).toBeGreaterThan(0);
});

test('keep/sell divider renders', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.getByText(/keep.*sell/i)).toBeVisible();
});

test('moving divider down marks one more item as keeper', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]').first()).toBeVisible();

  const keepersBefore = await authedPage.locator('[data-testid="keeper-row"]').count();
  await authedPage.getByRole('button', { name: /move divider down/i }).click();

  await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(keepersBefore + 1);
});

test('moving divider up marks one more item as seller', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]').first()).toBeVisible();

  const keepersBefore = await authedPage.locator('[data-testid="keeper-row"]').count();

  if (keepersBefore === 0) {
    // Move down first to get at least one keeper, then move up
    await authedPage.getByRole('button', { name: /move divider down/i }).click();
    await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(1);
  }

  await authedPage.getByRole('button', { name: /move divider up/i }).click();
  const keepersAfter = await authedPage.locator('[data-testid="keeper-row"]').count();
  expect(keepersAfter).toBe(Math.max(0, keepersBefore - 1));
});

test('status changes persist after reload', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/collection/${collectionId}`);
  await expect(authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]').first()).toBeVisible();

  await authedPage.getByRole('button', { name: /move divider down/i }).click();
  const keepersAfterMove = await authedPage.locator('[data-testid="keeper-row"]').count();

  await authedPage.reload();
  await expect(authedPage.locator('[data-testid="keeper-row"], [data-testid="seller-row"]').first()).toBeVisible();
  await expect(authedPage.locator('[data-testid="keeper-row"]')).toHaveCount(keepersAfterMove);
});
