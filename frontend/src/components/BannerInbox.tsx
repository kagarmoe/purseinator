import React from 'react';
import { Link } from 'react-router-dom';

interface BannerInboxProps {
  count: number;
  hasMore?: boolean;
}

export function BannerInbox({ count, hasMore }: BannerInboxProps) {
  if (count === 0 && !hasMore) return null;

  const displayCount = hasMore ? `${count}+` : count;
  const noun = (count === 1 && !hasMore) ? 'photo' : 'photos';

  return (
    <Link
      to="/upload"
      className="flex items-center justify-between gap-4
                 bg-saffron/15 border border-saffron border-l-4 border-l-terracotta
                 px-5 py-4 mb-6
                 hover:bg-saffron/25 transition-colors"
    >
      <div>
        <p className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-1">
          Your Inbox
        </p>
        <p className="font-serif text-lg text-near-black">
          {displayCount} {noun} waiting to be grouped
        </p>
      </div>
      <span className="text-terracotta font-sans text-sm" aria-hidden="true">→</span>
    </Link>
  );
}
