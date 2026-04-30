import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRankedItems, updateItemStatus } from "../api";
import { ChevronUp, ChevronDown } from "lucide-react";

interface RankedItem {
  id: number;
  brand: string;
  status: string;
  rating: number;
  comparison_count: number;
  condition_score: number | null;
}

export default function CollectionView() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const navigate = useNavigate();
  const cid = Number(collectionId);
  const [items, setItems] = useState<RankedItem[]>([]);
  const [dividerIndex, setDividerIndex] = useState<number | null>(null);

  useEffect(() => {
    getRankedItems(cid).then((data) => {
      setItems(data);
      const keeperCount = data.filter((i: RankedItem) => i.status === "keeper").length;
      setDividerIndex(keeperCount > 0 ? keeperCount : Math.ceil(data.length / 2));
    });
  }, [cid]);

  const moveDivider = async (newIndex: number) => {
    if (newIndex < 0 || newIndex > items.length) return;
    setDividerIndex(newIndex);

    for (let i = 0; i < items.length; i++) {
      const newStatus = i < newIndex ? "keeper" : "seller";
      if (items[i].status !== newStatus) {
        try {
          await updateItemStatus(cid, items[i].id, newStatus);
        } catch { /* best effort */ }
      }
    }

    setItems((prev) =>
      prev.map((item, i) => ({
        ...item,
        status: i < newIndex ? "keeper" : "seller",
      }))
    );
  };

  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      <header className="border-b border-[var(--color-near-black)]/10 px-6 py-5 flex items-center justify-between">
        <h1 className="font-[var(--font-serif)] text-2xl text-[var(--color-near-black)]">
          Rankings
        </h1>
        <button
          onClick={() => navigate(`/session/${collectionId}`)}
          className="text-xs tracking-widest uppercase text-[var(--color-gold)] border border-[var(--color-gold)]/40 px-4 py-2 hover:bg-[var(--color-gold)]/5 transition-colors cursor-pointer"
        >
          Rank More
        </button>
      </header>

      <main className="px-6 py-6 max-w-lg mx-auto">
        {items.length === 0 ? (
          <p className="text-[var(--color-muted)] text-sm text-center pt-12">
            No items ranked yet.
          </p>
        ) : (
          <div>
            {items.map((item, i) => (
              <div key={item.id}>
                <div
                  className={`flex items-center gap-4 py-4 border-l-2 pl-4 ${
                    i < (dividerIndex ?? 0)
                      ? "border-l-[var(--color-gold)]"
                      : "border-l-[var(--color-near-black)]/10"
                  }`}
                >
                  <span className="font-[var(--font-serif)] text-2xl text-[var(--color-near-black)]/30 w-8 shrink-0 text-right">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-[var(--color-near-black)] truncate">
                      {item.brand === "unknown" ? "Unknown" : item.brand}
                    </div>
                    <div className="text-[var(--color-muted)] text-xs mt-0.5">
                      {item.comparison_count} comparisons
                    </div>
                  </div>
                </div>

                {/* Keep/Sell divider */}
                {dividerIndex !== null && i === dividerIndex - 1 && (
                  <div className="flex items-center gap-3 py-2 my-1">
                    <button
                      onClick={() => moveDivider(dividerIndex - 1)}
                      className="w-7 h-7 flex items-center justify-center border border-[var(--color-gold)]/40 text-[var(--color-gold)] hover:bg-[var(--color-gold)]/10 transition-colors cursor-pointer rounded-sm"
                      aria-label="Move divider up"
                    >
                      <ChevronUp size={14} />
                    </button>
                    <div className="flex-1 h-px bg-[var(--color-gold)]" />
                    <span className="text-[var(--color-gold)] text-xs tracking-widest uppercase whitespace-nowrap">
                      Keep · Sell
                    </span>
                    <div className="flex-1 h-px bg-[var(--color-gold)]" />
                    <button
                      onClick={() => moveDivider(dividerIndex + 1)}
                      className="w-7 h-7 flex items-center justify-center border border-[var(--color-gold)]/40 text-[var(--color-gold)] hover:bg-[var(--color-gold)]/10 transition-colors cursor-pointer rounded-sm"
                      aria-label="Move divider down"
                    >
                      <ChevronDown size={14} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
