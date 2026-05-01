import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getItems, updateItemBrand } from "../api";

interface Item {
  id: number;
  brand: string;
  description: string;
  condition_score: number | null;
  status: string;
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    keeper: "bg-forest text-white",
    seller: "bg-terracotta text-white",
    unranked: "bg-transparent text-muted border border-dusty-rose",
  };
  const cls = variants[status] ?? variants.unranked;
  return (
    <span className={`text-[10px] uppercase tracking-widest font-sans px-2.5 py-1 ${cls}`}>
      {status}
    </span>
  );
}

export default function ItemReview() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const cid = Number(collectionId);
  const [items, setItems] = useState<Item[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [editBrand, setEditBrand] = useState("");

  useEffect(() => {
    getItems(cid).then(setItems).catch(() => {});
  }, [cid]);

  const saveBrand = async (itemId: number) => {
    await updateItemBrand(cid, itemId, editBrand);
    setItems((prev) =>
      prev.map((i) => (i.id === itemId ? { ...i, brand: editBrand } : i))
    );
    setEditing(null);
  };

  return (
    <div className="min-h-svh bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
          Operator
        </p>
        <h1 className="font-serif text-3xl text-near-black leading-tight">Item Review</h1>
      </header>

      <main className="px-6 py-8 max-w-2xl mx-auto">
        {items.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">No items in this collection.</p>
        ) : (
          <div className="grid gap-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-white border border-cream p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {editing === item.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          value={editBrand}
                          onChange={(e) => setEditBrand(e.target.value)}
                          className="font-serif text-base border-b border-terracotta bg-transparent outline-none text-near-black py-0.5 flex-1 min-w-0"
                          autoFocus
                          onKeyDown={(e) => e.key === "Enter" && saveBrand(item.id)}
                        />
                        <button
                          onClick={() => saveBrand(item.id)}
                          className="text-[10px] uppercase tracking-widest font-sans bg-terracotta text-white px-3 py-1.5 hover:bg-terracotta/80 transition-colors cursor-pointer shrink-0"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => { setEditing(item.id); setEditBrand(item.brand); }}
                        className="font-serif text-base text-near-black cursor-pointer hover:text-terracotta transition-colors bg-transparent border-none p-0 text-left"
                        title="Click to edit brand"
                      >
                        {item.brand === "unknown" ? "Unknown brand" : item.brand}
                      </button>
                    )}
                  </div>
                  <StatusBadge status={item.status} />
                </div>

                {item.condition_score !== null && (
                  <div className="mt-3">
                    <div className="h-1 bg-dusty-rose/30 w-full overflow-hidden">
                      <div
                        className="h-full bg-saffron"
                        style={{ width: `${Math.round(item.condition_score * 100)}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-muted font-sans mt-1 uppercase tracking-widest">
                      {Math.round(item.condition_score * 100)}% condition
                    </p>
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
