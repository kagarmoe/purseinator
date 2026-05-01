import React from 'react';

interface SelectionActionBarProps {
  count: number;
  onGroup: () => void;
  onDiscard: () => void;
}

export function SelectionActionBar({ count, onGroup, onDiscard }: SelectionActionBarProps) {
  if (count === 0) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-40
        bg-cream/95 backdrop-blur-md border-t border-cream
        pb-[env(safe-area-inset-bottom)]
        lg:bottom-6 lg:left-1/2 lg:-translate-x-1/2 lg:right-auto
        lg:bg-near-black/95 lg:text-cream lg:border-none lg:px-6 lg:py-3 lg:w-auto"
    >
      <div className="flex items-center justify-between gap-4 px-6 py-3">
        <span className="text-sm font-sans text-near-black lg:text-cream">
          {count} selected
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onDiscard}
            className="border border-terracotta text-terracotta text-xs font-sans uppercase tracking-[0.1em] px-3 py-1.5 hover:bg-terracotta hover:text-white transition-colors cursor-pointer"
          >
            Discard selected
          </button>
          <button
            type="button"
            onClick={onGroup}
            className="bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer"
          >
            Group as one purse
          </button>
        </div>
      </div>
    </div>
  );
}
