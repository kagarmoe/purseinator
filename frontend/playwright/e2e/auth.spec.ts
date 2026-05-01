import { test, expect } from '@playwright/test';

// --- Unauthenticated access ---

test('unauthenticated user visiting /dashboard is redirected to /', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL('/');
});

// --- Magic-link form ---

test('home page shows email input and Send Link button', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.getByRole('button', { name: /send link/i })).toBeVisible();
});

test('submitting email shows check-your-email confirmation', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type="email"]').fill('playwright@test.com');
  await page.getByRole('button', { name: /send link/i }).click();
  await expect(page.getByText(/check your email/i)).toBeVisible();
});

test('verify token route sets session and redirects to dashboard', async ({ page }) => {
  // The backend always returns the token in dev mode
  const resp = await page.request.post('/auth/magic-link', {
    data: { email: 'playwright@test.com' },
  });
  expect(resp.ok()).toBe(true);
  const { token } = await resp.json();

  await page.goto(`/verify?token=${encodeURIComponent(token)}`);

  // After verify, Verify.tsx navigates to /dashboard
  await expect(page).toHaveURL('/dashboard');
  await expect(page.getByText('Dashboard')).toBeVisible();
});

test('verify route with invalid token shows error message', async ({ page }) => {
  await page.goto('/verify?token=invalid-token-xyz');
  await expect(page.getByText(/invalid or expired/i)).toBeVisible();
});

// --- Dev Login (dev mode only) ---

test('Dev Login button creates session and navigates to dashboard', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: /dev login/i }).click();
  await expect(page).toHaveURL('/dashboard');
  await expect(page.getByText('Dashboard')).toBeVisible();
});
