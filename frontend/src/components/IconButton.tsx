import React from 'react';

interface IconButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  className?: string;
  disabled?: boolean;
}

export function IconButton({ icon, label, onClick, className = '', disabled = false }: IconButtonProps) {
  if (process.env.NODE_ENV === 'development' && !label) {
    throw new Error('IconButton: label prop is required for accessibility');
  }

  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={`
        relative inline-flex items-center justify-center w-9 h-9
        before:absolute before:-inset-1
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cobalt focus-visible:ring-offset-2 focus-visible:ring-offset-cream
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors cursor-pointer
        ${className}
      `}
    >
      {icon}
    </button>
  );
}
