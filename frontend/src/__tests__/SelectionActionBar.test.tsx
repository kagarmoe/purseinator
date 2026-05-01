import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { SelectionActionBar } from '../components/SelectionActionBar';

describe('SelectionActionBar', () => {
  it('bar is hidden when count === 0', () => {
    const { container } = render(
      <SelectionActionBar count={0} onGroup={vi.fn()} onDiscard={vi.fn()} />
    );
    // Should render null or hidden element
    expect(container.firstChild).toBeNull();
  });

  it('renders "{count} selected" copy when count > 0', () => {
    render(<SelectionActionBar count={3} onGroup={vi.fn()} onDiscard={vi.fn()} />);
    expect(screen.getByText(/3 selected/i)).toBeInTheDocument();
  });

  it('Group button calls onGroup; Discard button calls onDiscard', () => {
    const onGroup = vi.fn();
    const onDiscard = vi.fn();
    render(<SelectionActionBar count={2} onGroup={onGroup} onDiscard={onDiscard} />);

    fireEvent.click(screen.getByRole('button', { name: /group/i }));
    expect(onGroup).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: /discard/i }));
    expect(onDiscard).toHaveBeenCalledTimes(1);
  });
});
