import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { FilePickerButton } from '../components/FilePickerButton';

describe('FilePickerButton', () => {
  it('accept attribute contains image/*, image/heic, image/heif, image/webp', () => {
    const { container } = render(
      <FilePickerButton label="Choose photos" multiple onFiles={vi.fn()} />
    );
    const input = container.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
    const accept = input!.getAttribute('accept') ?? '';
    expect(accept).toContain('image/*');
    expect(accept).toContain('image/heic');
    expect(accept).toContain('image/heif');
    expect(accept).toContain('image/webp');
    // image/* should come first
    expect(accept.indexOf('image/*')).toBeLessThan(accept.indexOf('image/heic'));
  });

  it('multiple prop reflected on input', () => {
    const { container } = render(
      <FilePickerButton label="Choose photos" multiple onFiles={vi.fn()} />
    );
    const input = container.querySelector('input[type="file"]');
    expect(input).toHaveAttribute('multiple');
  });

  it('capture="environment" when prop set', () => {
    const { container } = render(
      <FilePickerButton label="Take photo" capture="environment" onFiles={vi.fn()} />
    );
    const input = container.querySelector('input[type="file"]');
    expect(input).toHaveAttribute('capture', 'environment');
  });

  it('selecting files calls onFiles with FileList contents', () => {
    const onFiles = vi.fn();
    const { container } = render(
      <FilePickerButton label="Choose photos" multiple onFiles={onFiles} />
    );
    const input = container.querySelector('input[type="file"]')!;
    const file = new File(['data'], 'test.jpg', { type: 'image/jpeg' });
    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);
    expect(onFiles).toHaveBeenCalledOnce();
    const arg = onFiles.mock.calls[0][0] as File[];
    expect(arg[0].name).toBe('test.jpg');
  });
});
