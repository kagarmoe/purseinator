import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  getStaging,
  uploadPhotos,
  groupPhotos,
  discardStaging,
  getCollections,
  createCollection,
  type StagingPhoto,
} from '../api';
import { humanizeUploadReason } from '../lib/upload';
import { useToast } from '../components/ToastProvider';
import { ThumbnailTile } from '../components/ThumbnailTile';
import { SelectionActionBar } from '../components/SelectionActionBar';
import { CollectionPickerModal } from '../components/CollectionPickerModal';
import { FilePickerButton } from '../components/FilePickerButton';
import { EmptyInboxState } from '../components/EmptyInboxState';

const POLL_INTERVAL_MS = 30000;

interface Collection {
  id: number;
  name: string;
  description?: string;
}

export function UploadInbox() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();

  const suggestCid = searchParams.get('suggest')
    ? Number(searchParams.get('suggest'))
    : undefined;

  const [photos, setPhotos] = useState<StagingPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [cursor, setCursor] = useState<number | null>(null);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [modalOpen, setModalOpen] = useState(false);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [groupedToday, setGroupedToday] = useState(0);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch staging photos
  const fetchStaging = useCallback(async (replace = true, before?: number) => {
    try {
      const result = await getStaging({ limit: 200, ...(before ? { before } : {}) });
      if (replace) {
        setPhotos(result.photos);
      } else {
        setPhotos((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const newPhotos = result.photos.filter((p) => !existingIds.has(p.id));
          return [...prev, ...newPhotos];
        });
      }
      setHasMore(result.has_more);
      if (result.photos.length > 0) {
        setCursor(result.photos[result.photos.length - 1].id);
      }
    } catch {
      // network error — will retry on next poll
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchStaging(true);
  }, [fetchStaging]);

  // Polling (visibility-gated)
  useEffect(() => {
    const startPolling = () => {
      if (pollingRef.current) return;
      pollingRef.current = setInterval(() => {
        if (document.visibilityState === 'visible') {
          fetchStaging(true);
        }
      }, POLL_INTERVAL_MS);
    };

    const stopPolling = () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        startPolling();
      } else {
        stopPolling();
      }
    };

    if (document.visibilityState === 'visible') {
      startPolling();
    }

    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchStaging]);

  // Infinite scroll sentinel
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!sentinelRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && cursor !== null) {
          // TODO(F10-pagination): add Playwright test seeding 201 staging photos, scrolling to bottom, asserting second getStaging call with before=<id>
          fetchStaging(false, cursor);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, cursor, fetchStaging]);

  const handleFiles = async (files: File[]) => {
    if (!navigator.onLine) {
      toast.error("You're offline. Connect to upload photos.");
      return;
    }
    try {
      const result = await uploadPhotos(files);
      if (result.succeeded.length > 0) {
        // Prepend new photos
        setPhotos((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const newPhotos = result.succeeded.filter((p) => !existingIds.has(p.id));
          return [...newPhotos, ...prev];
        });
      }
      if (result.failed.length > 0 && result.succeeded.length > 0) {
        const firstReason = humanizeUploadReason(result.failed[0].reason);
        toast.show(
          `${result.succeeded.length} photo${result.succeeded.length !== 1 ? 's' : ''} uploaded · ${result.failed.length} skipped (${firstReason})`,
          'info'
        );
      } else if (result.failed.length > 0 && result.succeeded.length === 0) {
        const firstReason = humanizeUploadReason(result.failed[0].reason);
        toast.error(`None of those uploaded — ${firstReason}`);
      }
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 413) {
        toast.error("Some photos were too big. Try uploading in smaller batches.");
      } else if (status === 429) {
        toast.error("Inbox full — group or discard photos before uploading more.");
      } else {
        toast.error("Something went wrong on our end. Try again in a moment.");
      }
    }
  };

  const handleToggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDiscard = async (id: number) => {
    try {
      await discardStaging(id);
      setPhotos((prev) => prev.filter((p) => p.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      toast.error("Couldn't discard that photo. Try again.");
    }
  };

  const handleDiscardSelected = async () => {
    const ids = Array.from(selected);
    for (const id of ids) {
      await handleDiscard(id);
    }
  };

  const openGroupModal = async () => {
    try {
      const result = await getCollections();
      setCollections(result);
    } catch {
      setCollections([]);
    }
    setModalOpen(true);
  };

  const handleGroup = async ({ collectionId }: { collectionId: number }) => {
    const photoIds = Array.from(selected);
    try {
      await groupPhotos({ collection_id: collectionId, photo_ids: photoIds });
      const count = photoIds.length;
      setPhotos((prev) => prev.filter((p) => !selected.has(p.id)));
      setSelected(new Set());
      setGroupedToday((n) => n + count);
      setModalOpen(false);
      toast.success(`Grouped ${count} photo${count !== 1 ? 's' : ''} into collection`);
      // Strip suggest param after success
      navigate('/upload');
    } catch {
      toast.error("Something went wrong grouping those photos. Try again.");
    }
  };

  const handleCreateCollection = async (data: { name: string; description: string }) => {
    const result = await createCollection(data);
    setCollections((prev) => [...prev, result]);
    return result;
  };

  const selectedCount = selected.size;
  const nearCapacity = photos.length >= 480;

  return (
    <div className="min-h-screen bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
          Your Inbox
        </p>
        <h1 className="font-serif text-3xl text-near-black leading-tight">Upload</h1>
        <p className="text-muted text-sm font-sans mt-1">
          {photos.length} in your inbox{groupedToday > 0 ? ` · ${groupedToday} grouped today` : ''}
        </p>
        {nearCapacity && (
          <div className="mt-3 bg-terracotta/10 border-l-4 border-terracotta px-4 py-2">
            <p className="text-xs font-sans text-terracotta">
              Inbox is nearly full — {photos.length} of 500.
            </p>
          </div>
        )}
        <div className="flex gap-3 mt-4 flex-wrap">
          <FilePickerButton
            label="Choose photos"
            multiple
            onFiles={handleFiles}
          />
          <FilePickerButton
            label="Take photo"
            capture="environment"
            onFiles={handleFiles}
            className="md:hidden"
          />
        </div>
      </header>

      <main className="px-6 py-6 pb-24 max-w-4xl mx-auto">
        {loading ? (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 sm:gap-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="aspect-square bg-dusty-rose/30 animate-pulse" />
            ))}
          </div>
        ) : photos.length === 0 ? (
          <EmptyInboxState />
        ) : (
          <>
            {/* Live region for polling announcements */}
            <div role="status" aria-live="polite" className="sr-only" aria-atomic="true" />

            <div
              role="group"
              aria-label="Staging photos"
              className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 sm:gap-3"
            >
              {photos.map((photo) => (
                <ThumbnailTile
                  key={photo.id}
                  photo={photo}
                  selected={selected.has(photo.id)}
                  onToggle={handleToggle}
                  onDiscard={handleDiscard}
                />
              ))}
            </div>
            {hasMore && <div ref={sentinelRef} className="h-8" />}
          </>
        )}
      </main>

      <SelectionActionBar
        count={selectedCount}
        onGroup={openGroupModal}
        onDiscard={handleDiscardSelected}
      />

      <CollectionPickerModal
        open={modalOpen}
        collections={collections}
        preselectId={suggestCid}
        onConfirm={handleGroup}
        onClose={() => setModalOpen(false)}
        onCreateCollection={handleCreateCollection}
        photoCount={selectedCount}
      />
    </div>
  );
}

export default UploadInbox;
