import { test, expect } from '../fixtures/auth';

test('session auto-completes when timer hits zero', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  // Wait for data to load before controlling time
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible();
  await expect(authedPage.getByText('2:00')).toBeVisible();

  await authedPage.clock.runFor(121_000);

  await expect(authedPage.getByText(/session complete/i)).toBeVisible();
});

test('timer counts down each second', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  // Wait for data to load before controlling time
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible();
  await expect(authedPage.getByText('2:00')).toBeVisible();

  await authedPage.clock.runFor(10_000);

  await expect(authedPage.getByText('1:50')).toBeVisible();
});

test('completion screen shows zero pairs when no comparisons made before expiry', async ({ authedPage, collectionId }) => {
  await authedPage.clock.install();
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  // Wait for data to load before controlling time
  await expect(authedPage.locator('[data-testid="item-card"]').first()).toBeVisible();

  await authedPage.clock.runFor(121_000);

  await expect(authedPage.getByText(/0 pairs/i)).toBeVisible();
});
