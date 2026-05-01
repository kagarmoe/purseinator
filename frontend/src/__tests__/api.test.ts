import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

// Helper to create a mock response with headers
function mockResponse(body: unknown, status = 200) {
  return {
    ok: true,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  };
}

function mockErrorResponse(status: number) {
  return {
    ok: false,
    status,
    headers: new Headers(),
  };
}

describe('uploadPhotos', () => {
  it('posts multipart with files[] field', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ succeeded: [], failed: [] }));

    const { uploadPhotos } = await import('../api');
    const file1 = new File(['data1'], 'photo1.jpg', { type: 'image/jpeg' });
    const file2 = new File(['data2'], 'photo2.jpg', { type: 'image/jpeg' });
    await uploadPhotos([file1, file2]);

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/upload/photos');
    expect(options.method).toBe('POST');
    const body = options.body as FormData;
    expect(body instanceof FormData).toBe(true);
    const files = body.getAll('files');
    expect(files).toHaveLength(2);
  });
});

describe('getStaging', () => {
  it('passes limit and before query params', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ photos: [], has_more: false }));

    const { getStaging } = await import('../api');
    await getStaging({ limit: 10, before: 5 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/upload/staging');
    expect(url).toContain('limit=10');
    expect(url).toContain('before=5');
  });

  it('works without optional params', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ photos: [], has_more: false }));

    const { getStaging } = await import('../api');
    await getStaging({});

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/upload/staging');
    expect(url).not.toContain('before=');
  });
});

describe('groupPhotos', () => {
  it('posts json body {collection_id, photo_ids}', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ item_id: 1 }));

    const { groupPhotos } = await import('../api');
    await groupPhotos({ collection_id: 42, photo_ids: [1, 2, 3] });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/upload/group');
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body as string);
    expect(body.collection_id).toBe(42);
    expect(body.photo_ids).toEqual([1, 2, 3]);
  });
});

describe('discardStaging', () => {
  it('issues DELETE to /upload/staging/{id}', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      headers: new Headers(),
    });

    const { discardStaging } = await import('../api');
    await discardStaging(99);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/upload/staging/99');
    expect(options.method).toBe('DELETE');
  });
});

describe('ApiError', () => {
  it('apiFetch surfaces 429 distinctly with .status === 429', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(429));

    const { getStaging } = await import('../api');
    try {
      await getStaging({});
      expect.fail('should have thrown');
    } catch (err: unknown) {
      expect((err as { status: number }).status).toBe(429);
    }
  });

  it('throws ApiError with correct status for 413', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(413));

    const { uploadPhotos } = await import('../api');
    try {
      await uploadPhotos([]);
      expect.fail('should have thrown');
    } catch (err: unknown) {
      expect((err as { status: number }).status).toBe(413);
    }
  });
});
