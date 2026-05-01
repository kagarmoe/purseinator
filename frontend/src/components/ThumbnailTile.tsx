import React from 'react';
import type { StagingPhoto } from '../api';

interface ThumbnailTileProps {
  photo: StagingPhoto;
  selected: boolean;
  onToggle: (id: number) => void;
  onDiscard: (id: number) => void;
  size?: 'md' | 'sm';
}

function formatCaptureDate(capturedAt: string | null): string {
  if (!capturedAt) return '';
  try {
    const d = new Date(capturedAt);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export function ThumbnailTile({ photo, selected, onToggle, onDiscard, size = 'md' }: ThumbnailTileProps) {
  const captureLabel = photo.captured_at
    ? `, captured ${formatCaptureDate(photo.captured_at)}`
    : '';

  const ariaLabel = `Photo ${photo.original_filename ?? 'unknown'}${captureLabel}, tap to toggle selection`;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      onToggle(photo.id);
    }
  };

  const handleDiscardClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDiscard(photo.id);
  };

  const tileSize = size === 'sm' ? 'w-16 h-16' : '';

  return (
    <div className={`relative aspect-square ${tileSize} group`}>
      {/* Selectable tile */}
      <button
        role="checkbox"
        aria-checked={selected}
        aria-label={ariaLabel}
        tabIndex={0}
        onClick={() => onToggle(photo.id)}
        onKeyDown={handleKeyDown}
        className={`
          w-full h-full relative overflow-hidden bg-dusty-rose/10
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cobalt
          ${selected ? 'ring-4 ring-saffron ring-offset-2 ring-offset-cream' : ''}
        `}
      >
        <img
          src={photo.thumbnail_url}
          alt={photo.original_filename ?? 'Photo'}
          loading="lazy"
          className="w-full h-full object-cover"
        />

        {/* Capture date strip */}
        {photo.captured_at && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-near-black/60 to-transparent px-1 pb-1 pt-3">
            <span className="text-[10px] text-cream font-sans tracking-wider">
              {formatCaptureDate(photo.captured_at)}
            </span>
          </div>
        )}

        {/* Selected checkmark */}
        {selected && (
          <div
            data-testid="check-icon"
            className="absolute top-1 right-1 bg-saffron text-near-black w-7 h-7 rounded-full grid place-items-center"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
        )}
      </button>

      {/* Discard button */}
      <button
        type="button"
        aria-label="Discard photo"
        onClick={handleDiscardClick}
        className="absolute top-1 left-1 bg-near-black/60 text-cream w-7 h-7 rounded-full flex items-center justify-center z-10 hover:bg-near-black/80 transition-colors cursor-pointer"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
