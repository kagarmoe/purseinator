import React, { useEffect, useState } from 'react';

export type MetadataFieldStatus = 'idle' | 'saving' | 'saved' | 'error';

interface MetadataFieldProps {
  label: string;
  status?: MetadataFieldStatus;
  error?: string;
  children: React.ReactNode;
  id?: string;
}

export function MetadataField({ label, status = 'idle', error, children, id }: MetadataFieldProps) {
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    if (status === 'saved') {
      setShowSaved(true);
      const t = setTimeout(() => setShowSaved(false), 1500);
      return () => clearTimeout(t);
    }
  }, [status]);

  const fieldId = id ?? `field-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={fieldId}
        className="text-[10px] uppercase tracking-[0.25em] text-muted font-sans"
      >
        {label}
      </label>
      <div
        className={`
          border-b transition-colors
          ${status === 'error' ? 'border-terracotta' : 'border-muted/40'}
        `}
      >
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child as React.ReactElement<{ id?: string }>, { id: (child.props as { id?: string }).id ?? fieldId });
          }
          return child;
        })}
      </div>
      {status === 'saving' && (
        <p className="text-[10px] text-muted font-sans" aria-live="polite">
          Saving…
        </p>
      )}
      {(status === 'saved' || showSaved) && (
        <p className="text-[10px] text-forest font-sans" aria-live="polite">
          ✓ Saved
        </p>
      )}
      {status === 'error' && error && (
        <p className="text-[11px] text-terracotta font-sans" role="alert" aria-describedby={fieldId}>
          {error}
        </p>
      )}
    </div>
  );
}
