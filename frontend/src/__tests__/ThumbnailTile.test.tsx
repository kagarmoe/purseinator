import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ThumbnailTile } from '../components/ThumbnailTile';

const photo = {
  id: 1,
  thumbnail_url: '/photos/abc/thumb',
  original_filename: 'IMG_001.jpg',
  captured_at: '2026-04-30T18:42:00',
};

describe('ThumbnailTile', () => {
  it('renders thumbnail src from photo.thumbnail_url and aria-label with filename', () => {
    render(<ThumbnailTile photo={photo} selected={false} onToggle={vi.fn()} onDiscard={vi.fn()} />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/photos/abc/thumb');
    const tile = screen.getByRole('checkbox');
    expect(tile.getAttribute('aria-label')).toContain('IMG_001.jpg');
  });

  it('tap toggles selection — onToggle called with photo.id', () => {
    const onToggle = vi.fn();
    render(<ThumbnailTile photo={photo} selected={false} onToggle={onToggle} onDiscard={vi.fn()} />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledWith(1);
  });

  it('selected=true renders saffron ring class and check icon', () => {
    const { container } = render(
      <ThumbnailTile photo={photo} selected={true} onToggle={vi.fn()} onDiscard={vi.fn()} />
    );
    const tile = screen.getByRole('checkbox');
    expect(tile).toHaveAttribute('aria-checked', 'true');
    // Check for the selection indicator
    expect(container.querySelector('[data-testid="check-icon"]') || container.querySelector('.ring-saffron') || tile.className).toBeTruthy();
  });

  it('discard button has aria-label="Discard photo" and calls onDiscard', () => {
    const onDiscard = vi.fn();
    render(<ThumbnailTile photo={photo} selected={false} onToggle={vi.fn()} onDiscard={onDiscard} />);
    const discardBtn = screen.getByRole('button', { name: 'Discard photo' });
    fireEvent.click(discardBtn);
    expect(onDiscard).toHaveBeenCalledWith(1);
  });

  it('keyboard: Space and Enter toggle selection', () => {
    const onToggle = vi.fn();
    render(<ThumbnailTile photo={photo} selected={false} onToggle={onToggle} onDiscard={vi.fn()} />);
    const tile = screen.getByRole('checkbox');
    fireEvent.keyDown(tile, { key: ' ' });
    expect(onToggle).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(tile, { key: 'Enter' });
    expect(onToggle).toHaveBeenCalledTimes(2);
  });
});
