import { test, expect } from '../fixtures/auth';

test('dashboard shows seeded collection by name', async ({ authedPage }) => {
  await authedPage.goto('/dashboard');
  await expect(authedPage.getByText('Test Collection')).toBeVisible();
});

test('View Rankings button navigates to /collection/:id', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await expect(authedPage.getByText('Test Collection')).toBeVisible();
  await authedPage.getByRole('button', { name: /view rankings/i }).first().click();
  await expect(authedPage).toHaveURL(`/collection/${collectionId}`);
});

test('Review Items button navigates to /review/:id', async ({ authedPage, collectionId }) => {
  await authedPage.goto('/dashboard');
  await expect(authedPage.getByText('Test Collection')).toBeVisible();
  await authedPage.getByRole('button', { name: /review items/i }).first().click();
  await expect(authedPage).toHaveURL(`/review/${collectionId}`);
});

test('empty state shown on home page when user has no collections', async ({ page }) => {
  // Log in as a fresh user with no collections via magic link
  const resp = await page.request.post('/auth/magic-link', {
    data: { email: 'empty@test.com' },
  });
  const { token } = await resp.json();
  const verifyResp = await page.request.get(`/auth/verify?token=${encodeURIComponent(token)}`);
  const { session_id } = await verifyResp.json();

  await page.context().addCookies([{
    name: 'session_id',
    value: session_id,
    domain: 'localhost',
    path: '/',
    sameSite: 'Lax',
  }]);

  await page.goto('/');
  await expect(page.getByText('PURSEINATOR')).toBeVisible();
  await expect(page.getByText(/no collections yet/i)).toBeVisible();
});
