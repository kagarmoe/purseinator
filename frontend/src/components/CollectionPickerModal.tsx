import React, { useState, useEffect, useRef } from 'react';

interface Collection {
  id: number;
  name: string;
  description?: string;
}

interface CollectionPickerModalProps {
  open: boolean;
  collections: Collection[];
  preselectId?: number;
  onConfirm: (result: { collectionId: number }) => void;
  onClose: () => void;
  onCreateCollection: (data: { name: string; description: string }) => Promise<{ id: number }>;
  photoCount?: number;
}

export function CollectionPickerModal({
  open,
  collections,
  preselectId,
  onConfirm,
  onClose,
  onCreateCollection,
  photoCount = 0,
}: CollectionPickerModalProps) {
  const [selectedId, setSelectedId] = useState<number | null>(preselectId ?? null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const firstFocusRef = useRef<HTMLHeadingElement>(null);

  // Reset when opened
  useEffect(() => {
    if (open) {
      setSelectedId(preselectId ?? null);
      setShowNewForm(false);
      setNewName('');
      setNewDescription('');
      setTimeout(() => firstFocusRef.current?.focus(), 50);
    }
  }, [open, preselectId]);

  // Esc to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Scroll lock
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!open) return null;

  const handleConfirm = () => {
    if (selectedId !== null) {
      onConfirm({ collectionId: selectedId });
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const result = await onCreateCollection({ name: newName.trim(), description: newDescription.trim() });
      onConfirm({ collectionId: result.id });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-near-black/50" onClick={onClose} />

      {/* Modal */}
      <div
        role="dialog"
        aria-labelledby="modal-title"
        aria-modal="true"
        className="relative bg-cream w-full max-w-md max-h-[80vh] overflow-y-auto"
      >
        <div className="px-6 pt-8 pb-6">
          <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
            Where is this purse going?
          </p>
          <h2
            id="modal-title"
            ref={firstFocusRef}
            tabIndex={-1}
            className="font-serif text-2xl text-near-black leading-tight mb-6 outline-none"
          >
            Pick a collection
          </h2>

          {/* Collections list */}
          <div role="radiogroup" aria-label="Collections" className="flex flex-col gap-2 mb-4">
            {collections.map((c) => (
              <label
                key={c.id}
                className={`
                  flex items-center gap-3 px-4 py-3 cursor-pointer border transition-colors
                  ${selectedId === c.id
                    ? 'bg-dusty-rose/40 border-l-4 border-l-terracotta border-dusty-rose'
                    : 'bg-dusty-rose/20 border-l-4 border-l-transparent border-dusty-rose hover:bg-dusty-rose/30'}
                `}
              >
                <input
                  type="radio"
                  name="collection"
                  value={String(c.id)}
                  aria-label={c.name}
                  checked={selectedId === c.id}
                  onChange={() => setSelectedId(c.id)}
                  className="accent-terracotta"
                />
                <span className="font-sans text-sm text-near-black">{c.name}</span>
              </label>
            ))}
          </div>

          {/* New collection toggle */}
          <button
            type="button"
            onClick={() => setShowNewForm((v) => !v)}
            className="text-cobalt underline-offset-4 hover:underline text-sm font-sans mb-4"
          >
            + New collection
          </button>

          {showNewForm && (
            <div className="flex flex-col gap-3 mb-4 border border-dusty-rose p-4">
              <input
                type="text"
                placeholder="Collection name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm outline-none focus:border-terracotta"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="bg-cream border-b border-muted/40 px-0 py-2 font-sans text-sm outline-none focus:border-terracotta"
              />
              <button
                type="button"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer disabled:opacity-50"
              >
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between gap-3 pt-4 border-t border-cream">
            <button
              type="button"
              onClick={onClose}
              className="border border-cobalt text-cobalt text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-cobalt hover:text-white transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={selectedId === null && !showNewForm}
              className="bg-terracotta text-white text-xs font-sans uppercase tracking-[0.1em] px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer disabled:opacity-50"
            >
              Group {photoCount > 0 ? `${photoCount} photos` : 'photos'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
