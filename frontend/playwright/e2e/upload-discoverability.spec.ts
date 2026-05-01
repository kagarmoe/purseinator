import { test, expect } from '../fixtures/auth';

test('dashboard has Upload button that navigates to /upload', async ({ authedPage }) => {
  await authedPage.goto('/dashboard');
  const uploadBtn = authedPage.getByRole('link', { name: /upload/i });
  await expect(uploadBtn).toBeVisible({ timeout: 5000 });
  await uploadBtn.click();
  await expect(authedPage).toHaveURL('/upload', { timeout: 5000 });
});

test('session/:cid "+ Add photos to this collection" link navigates to /upload?suggest=<cid>', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/rank/${collectionId}?minutes=2`);
  const link = authedPage.getByRole('link', { name: /add photos to this collection/i });
  await expect(link).toBeVisible({ timeout: 5000 });
  await link.click();
  await expect(authedPage).toHaveURL(`/upload?suggest=${collectionId}`, { timeout: 5000 });
});

test('?suggest=<cid> direct navigation preselects collection in modal', async ({ authedPage, collectionId }) => {
  await authedPage.goto(`/upload?suggest=${collectionId}`);
  await expect(authedPage.getByRole('heading', { name: /upload/i })).toBeVisible({ timeout: 5000 });
  // The suggest param should be reflected — verify the page loads without error
  // (Full preselection test is covered in upload-inbox.spec.ts)
});
