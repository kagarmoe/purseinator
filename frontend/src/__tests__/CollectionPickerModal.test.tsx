import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import React from 'react';
import { CollectionPickerModal } from '../components/CollectionPickerModal';

const collections = [
  { id: 1, name: 'Vintage Bags', description: '' },
  { id: 2, name: 'Summer Edit', description: '' },
];

describe('CollectionPickerModal', () => {
  it('modal is closed when open=false', () => {
    render(
      <CollectionPickerModal
        open={false}
        collections={collections}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        onCreateCollection={vi.fn()}
      />
    );
    expect(screen.queryByText(/pick a collection/i)).not.toBeInTheDocument();
  });

  it('modal renders collections list with radio controls when open', () => {
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        onCreateCollection={vi.fn()}
      />
    );
    expect(screen.getByText('Vintage Bags')).toBeInTheDocument();
    expect(screen.getByText('Summer Edit')).toBeInTheDocument();
    const radios = screen.getAllByRole('radio');
    expect(radios.length).toBeGreaterThanOrEqual(2);
  });

  it('preselectId pre-checks the matching radio', () => {
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        preselectId={2}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        onCreateCollection={vi.fn()}
      />
    );
    const radio = screen.getAllByRole('radio').find(
      (r) => r.getAttribute('value') === '2'
    );
    expect(radio).toBeDefined();
    expect(radio).toBeChecked();
  });

  it('expanding "+ New collection" reveals name and description inputs and a Create button', () => {
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        onCreateCollection={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText(/\+ new collection/i));
    expect(screen.getByPlaceholderText(/collection name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
  });

  it('confirm with existing collection calls onConfirm({collectionId})', () => {
    const onConfirm = vi.fn();
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        onConfirm={onConfirm}
        onClose={vi.fn()}
        onCreateCollection={vi.fn()}
      />
    );
    // Select collection 1
    fireEvent.click(screen.getByLabelText('Vintage Bags'));
    fireEvent.click(screen.getByRole('button', { name: /group/i }));
    expect(onConfirm).toHaveBeenCalledWith({ collectionId: 1 });
  });

  it('confirm with new collection calls onCreateCollection then onConfirm', async () => {
    const onCreateCollection = vi.fn().mockResolvedValue({ id: 99 });
    const onConfirm = vi.fn();
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        onConfirm={onConfirm}
        onClose={vi.fn()}
        onCreateCollection={onCreateCollection}
      />
    );
    fireEvent.click(screen.getByText(/\+ new collection/i));
    fireEvent.change(screen.getByPlaceholderText(/collection name/i), { target: { value: 'New Bag' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /create/i }));
    });
    expect(onCreateCollection).toHaveBeenCalledWith({ name: 'New Bag', description: '' });
    expect(onConfirm).toHaveBeenCalledWith({ collectionId: 99 });
  });

  it('Esc closes the modal', () => {
    const onClose = vi.fn();
    render(
      <CollectionPickerModal
        open={true}
        collections={collections}
        onConfirm={vi.fn()}
        onClose={onClose}
        onCreateCollection={vi.fn()}
      />
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
