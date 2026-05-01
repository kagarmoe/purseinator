import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { IconButton } from '../components/IconButton';
import { MetadataField } from '../components/MetadataField';

const TestIcon = () => <svg data-testid="icon" />;

describe('IconButton', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws in dev when label is missing', () => {
    const origEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    // @ts-expect-error intentionally passing no label
    expect(() => render(<IconButton icon={<TestIcon />} onClick={() => {}} />)).toThrow();

    process.env.NODE_ENV = origEnv;
  });

  it('renders aria-label and renders the icon', () => {
    render(<IconButton icon={<TestIcon />} label="Delete photo" onClick={() => {}} />);
    const btn = screen.getByRole('button', { name: 'Delete photo' });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute('aria-label', 'Delete photo');
  });
});

describe('MetadataField', () => {
  it('shows "Saved" copy with status=saved', () => {
    render(
      <MetadataField label="Brand" status="saved">
        <input readOnly value="Chanel" />
      </MetadataField>
    );
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
  });

  it('surfaces error prop with role=alert', () => {
    render(
      <MetadataField label="Price" status="error" error="Invalid value">
        <input readOnly value="" />
      </MetadataField>
    );
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Invalid value');
  });
});
