import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getRankedItems, updateItemStatus } from "../api";

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
    <div className="min-h-svh bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
            Collection
          </p>
          <h1 className="font-serif text-3xl text-near-black leading-tight">Your Rankings</h1>
        </div>
        <button
          onClick={() => navigate(`/session/${collectionId}`)}
          className="text-xs font-sans uppercase tracking-[0.1em] bg-terracotta text-white px-5 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer"
        >
          Rank More
        </button>
      </header>

      <main className="px-6 py-8 max-w-lg mx-auto">
        {items.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">No items ranked yet.</p>
        ) : (
          <div>
            {items.map((item, i) => (
              <div key={item.id}>
                <div
                  className={`flex items-center gap-4 py-4 border-l-4 pl-4 mb-0.5 ${
                    i < (dividerIndex ?? 0)
                      ? "border-l-forest bg-forest/5"
                      : "border-l-terracotta bg-terracotta/5"
                  }`}
                >
                  <span className="font-serif text-3xl text-muted/40 w-10 text-center shrink-0 leading-none">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-base text-near-black">
                      {item.brand === "unknown" ? "Unknown" : item.brand}
                    </div>
                    <div className="text-xs text-muted font-sans mt-0.5">
                      {item.comparison_count} comparisons
                    </div>
                  </div>
                </div>

                {/* gold divider bar between keep / sell */}
                {dividerIndex !== null && i === dividerIndex - 1 && (
                  <div className="flex items-center gap-3 py-3 my-1">
                    <button
                      onClick={() => moveDivider(dividerIndex - 1)}
                      aria-label="Move divider up"
                      className="w-7 h-7 rounded-full border border-saffron text-saffron text-xs flex items-center justify-center hover:bg-saffron hover:text-white transition-colors cursor-pointer bg-transparent"
                    >
                      ▲
                    </button>
                    <div className="flex-1 h-[3px] bg-saffron" />
                    <span className="text-[10px] uppercase tracking-widest text-saffron font-sans whitespace-nowrap font-semibold">
                      Keep · Sell
                    </span>
                    <div className="flex-1 h-[3px] bg-saffron" />
                    <button
                      onClick={() => moveDivider(dividerIndex + 1)}
                      aria-label="Move divider down"
                      className="w-7 h-7 rounded-full border border-saffron text-saffron text-xs flex items-center justify-center hover:bg-saffron hover:text-white transition-colors cursor-pointer bg-transparent"
                    >
                      ▼
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
