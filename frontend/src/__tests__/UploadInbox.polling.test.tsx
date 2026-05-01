import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';
import React from 'react';

// Mock the api module
vi.mock('../api', () => ({
  getStaging: vi.fn().mockResolvedValue({ photos: [], has_more: false }),
  uploadPhotos: vi.fn(),
  groupPhotos: vi.fn(),
  discardStaging: vi.fn(),
  getCollections: vi.fn().mockResolvedValue([]),
  createCollection: vi.fn(),
  ApiError: class ApiError extends Error { status: number; constructor(s: number, m: string) { super(m); this.status = s; } },
}));

// We need to mock react-router-dom
vi.mock('react-router-dom', () => ({
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => <a href={to}>{children}</a>,
}));

// Mock ToastProvider
vi.mock('../components/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), show: vi.fn() }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('UploadInbox polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('does NOT call getStaging when tab is hidden', async () => {
    const { getStaging } = await import('../api');
    const mockGetStaging = vi.mocked(getStaging);
    mockGetStaging.mockClear();

    // Set tab to hidden
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });

    const { UploadInbox } = await import('../pages/UploadInbox');

    await act(async () => {
      render(<UploadInbox />);
    });

    // Initial call happens on mount (visible is not enforced on mount, only polling)
    const callsAfterMount = mockGetStaging.mock.calls.length;

    // Advance by 30 seconds - should NOT trigger more calls (tab is hidden)
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });

    expect(mockGetStaging.mock.calls.length).toBe(callsAfterMount);
  });

  it('DOES call getStaging when tab becomes visible', async () => {
    const { getStaging } = await import('../api');
    const mockGetStaging = vi.mocked(getStaging);
    mockGetStaging.mockClear();

    // Start hidden
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });

    const { UploadInbox } = await import('../pages/UploadInbox');

    await act(async () => {
      render(<UploadInbox />);
    });

    const callsAfterMount = mockGetStaging.mock.calls.length;

    // Tab becomes visible
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    // Advance timer
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });

    expect(mockGetStaging.mock.calls.length).toBeGreaterThan(callsAfterMount);
  });
});
