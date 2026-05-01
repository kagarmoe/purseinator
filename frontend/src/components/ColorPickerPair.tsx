import React from 'react';

export const COLOR_OPTIONS = [
  'black', 'white', 'tan', 'brown', 'red', 'pink',
  'blue', 'green', 'yellow', 'gray', 'multi',
] as const;

export type ColorOption = typeof COLOR_OPTIONS[number];

interface ColorPickerPairProps {
  primary: string;
  secondary: string[];
  onChange: (value: { primary: string; secondary: string[] }) => void;
}

export function ColorPickerPair({ primary, secondary, onChange }: ColorPickerPairProps) {
  const isMulti = primary === 'multi';

  const handlePrimaryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPrimary = e.target.value;
    if (newPrimary === 'multi') {
      onChange({ primary: 'multi', secondary: [] });
    } else {
      onChange({ primary: newPrimary, secondary });
    }
  };

  const toggleAccent = (color: string) => {
    if (isMulti) return;
    const next = secondary.includes(color)
      ? secondary.filter((c) => c !== color)
      : [...secondary, color];
    onChange({ primary, secondary: next });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="color-primary"
          className="text-[10px] uppercase tracking-[0.25em] text-muted font-sans"
        >
          Primary Color
        </label>
        <select
          id="color-primary"
          value={primary}
          onChange={handlePrimaryChange}
          className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm focus:border-terracotta outline-none"
        >
          <option value="">— select —</option>
          {COLOR_OPTIONS.filter((c) => c !== 'multi').map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
          <optgroup label="────────">
            <option value="multi">multi</option>
          </optgroup>
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <span
          id="accents-label"
          className="text-[10px] uppercase tracking-[0.25em] text-muted font-sans"
        >
          Accent Colors
        </span>
        <div
          role="group"
          aria-labelledby="accents-label"
          aria-label="Accent Colors"
          aria-disabled={isMulti ? 'true' : 'false'}
          className={`flex flex-wrap gap-2 ${isMulti ? 'opacity-50 pointer-events-none' : ''}`}
        >
          {COLOR_OPTIONS.filter((c) => c !== 'multi').map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => toggleAccent(c)}
              disabled={isMulti}
              className={`
                px-3 py-1 text-xs font-sans border transition-colors
                ${secondary.includes(c)
                  ? 'bg-near-black text-cream border-near-black'
                  : 'border-muted text-muted hover:border-near-black hover:text-near-black'}
              `}
            >
              {c}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
