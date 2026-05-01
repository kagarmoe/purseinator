import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { EmptyInboxState } from '../components/EmptyInboxState';

describe('EmptyInboxState', () => {
  it('renders italic muted "Your inbox is empty." line and CTA copy', () => {
    render(<EmptyInboxState />);
    expect(screen.getByText(/your inbox is empty/i)).toBeInTheDocument();
    expect(screen.getByText(/choose photos/i)).toBeInTheDocument();
  });
});
