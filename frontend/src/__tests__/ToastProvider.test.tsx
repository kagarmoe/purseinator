import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import React from 'react';
import { ToastProvider, useToast } from '../components/ToastProvider';

function TestComponent() {
  const toast = useToast();
  return (
    <div>
      <button onClick={() => toast.success('Test success')}>success</button>
      <button onClick={() => toast.error('Test error')}>error</button>
      <button onClick={() => {
        for (let i = 0; i < 6; i++) {
          toast.success(`Toast ${i}`);
        }
      }}>push6</button>
    </div>
  );
}

describe('ToastProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('toast.success() pushes a toast that auto-dismisses after 4s', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    act(() => {
      screen.getByText('success').click();
    });

    expect(screen.getByText('Test success')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(screen.queryByText('Test success')).not.toBeInTheDocument();
  });

  it('pushing a 6th toast evicts the oldest', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    act(() => {
      screen.getByText('push6').click();
    });

    // Should only show 5 toasts — Toast 0 evicted
    expect(screen.queryByText('Toast 0')).not.toBeInTheDocument();
    expect(screen.getByText('Toast 5')).toBeInTheDocument();
  });

  it('manual dismiss removes immediately', async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    act(() => {
      screen.getByText('success').click();
    });

    expect(screen.getByText('Test success')).toBeInTheDocument();

    const dismissBtn = screen.getByRole('button', { name: /dismiss|×|close/i });
    act(() => {
      fireEvent.click(dismissBtn);
    });

    expect(screen.queryByText('Test success')).not.toBeInTheDocument();
  });
});
