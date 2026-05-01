import { test, expect } from '../fixtures/auth';

test('413 oversize toast', async ({ authedPage }) => {
  await authedPage.goto('/upload');

  // Mock the upload endpoint to return 413
  await authedPage.route('**/upload/photos', (route) => {
    route.fulfill({
      status: 413,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Request body too large' }),
    });
  });

  // Trigger upload via file input
  const fileInput = authedPage.locator('input[type="file"]').first();
  const dummyFile = {
    name: 'large-photo.jpg',
    mimeType: 'image/jpeg',
    buffer: Buffer.from('x'.repeat(100)),
  };
  await fileInput.setInputFiles([dummyFile]);

  // Assert toast
  await expect(authedPage.getByText(/some photos were too big/i)).toBeVisible({ timeout: 5000 });
});

test('429 inbox full toast', async ({ authedPage }) => {
  await authedPage.goto('/upload');

  // Mock the upload endpoint to return 429
  await authedPage.route('**/upload/photos', (route) => {
    route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Too many staging photos' }),
    });
  });

  const fileInput = authedPage.locator('input[type="file"]').first();
  const dummyFile = {
    name: 'photo.jpg',
    mimeType: 'image/jpeg',
    buffer: Buffer.from('x'.repeat(100)),
  };
  await fileInput.setInputFiles([dummyFile]);

  // Assert inbox full toast
  await expect(authedPage.getByText(/inbox full/i)).toBeVisible({ timeout: 5000 });
});

test('partial-success humanization toast', async ({ authedPage }) => {
  await authedPage.goto('/upload');

  // Mock the upload endpoint to return partial success
  await authedPage.route('**/upload/photos', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        succeeded: [
          {
            id: 1,
            thumbnail_url: '/photos/abc/thumb',
            original_filename: 'good.jpg',
            captured_at: null,
          },
        ],
        failed: [
          {
            original_filename: 'x.heic',
            reason: 'unsupported format',
          },
        ],
      }),
    });
  });

  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles([
    { name: 'good.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('x') },
    { name: 'x.heic', mimeType: 'image/heic', buffer: Buffer.from('y') },
  ]);

  // Assert partial success toast
  await expect(authedPage.getByText(/1 photo.*uploaded.*1 skipped/i)).toBeVisible({ timeout: 5000 });
});
