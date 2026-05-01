import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ColorPickerPair } from '../components/ColorPickerPair';

describe('ColorPickerPair', () => {
  it('setting primary to "multi" clears secondary AND emits a single onChange call with both fields together', () => {
    const onChange = vi.fn();
    render(
      <ColorPickerPair
        primary="red"
        secondary={['tan', 'black']}
        onChange={onChange}
      />
    );

    // Change primary to "multi"
    const primarySelect = screen.getByLabelText(/primary color/i);
    fireEvent.change(primarySelect, { target: { value: 'multi' } });

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ primary: 'multi', secondary: [] });
  });

  it('setting primary to a non-multi color preserves any selected secondaries', () => {
    const onChange = vi.fn();
    render(
      <ColorPickerPair
        primary="red"
        secondary={['tan']}
        onChange={onChange}
      />
    );

    const primarySelect = screen.getByLabelText(/primary color/i);
    fireEvent.change(primarySelect, { target: { value: 'black' } });

    expect(onChange).toHaveBeenCalledWith({ primary: 'black', secondary: ['tan'] });
  });

  it('accents picker is disabled with aria-disabled when primary is multi', () => {
    render(
      <ColorPickerPair
        primary="multi"
        secondary={[]}
        onChange={vi.fn()}
      />
    );

    const accentsContainer = screen.getByLabelText(/accent colors/i);
    expect(accentsContainer).toHaveAttribute('aria-disabled', 'true');
  });
});
