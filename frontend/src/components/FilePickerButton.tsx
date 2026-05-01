import React, { useRef } from 'react';

const ACCEPT = 'image/*,image/heic,image/heif,image/webp';

interface FilePickerButtonProps {
  label: string;
  multiple?: boolean;
  capture?: 'environment' | 'user';
  onFiles: (files: File[]) => void;
  className?: string;
}

export function FilePickerButton({ label, multiple, capture, onFiles, className = '' }: FilePickerButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) {
      onFiles(files);
    }
    // Reset so same file can be re-selected
    if (inputRef.current) inputRef.current.value = '';
  };

  const inputId = `file-picker-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <label
      htmlFor={inputId}
      className={`
        inline-flex items-center justify-center
        bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2
        hover:bg-terracotta/80 transition-colors cursor-pointer
        ${className}
      `}
    >
      {label}
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={ACCEPT}
        multiple={multiple}
        capture={capture}
        onChange={handleChange}
        className="sr-only"
      />
    </label>
  );
}
