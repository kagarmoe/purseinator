import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

interface Item {
  id: number;
  brand: string;
  description: string;
  condition_score: number | null;
  status: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "";

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    keeper: "bg-cream text-near-black border border-gold",
    seller: "bg-near-black text-white border border-near-black",
    unranked: "bg-transparent text-muted border border-cream",
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
    fetch(`${API_BASE}/collections/${cid}/items`, { credentials: "include" })
      .then((r) => r.json())
      .then(setItems);
  }, [cid]);

  const saveBrand = async (itemId: number) => {
    await fetch(`${API_BASE}/collections/${cid}/items/${itemId}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand: editBrand }),
    });
    setItems((prev) =>
      prev.map((i) => (i.id === itemId ? { ...i, brand: editBrand } : i))
    );
    setEditing(null);
  };

  return (
    <div className="min-h-svh bg-surface">
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
                          className="font-serif text-base border-b border-gold bg-transparent outline-none text-near-black py-0.5 flex-1 min-w-0"
                          autoFocus
                          onKeyDown={(e) => e.key === "Enter" && saveBrand(item.id)}
                        />
                        <button
                          onClick={() => saveBrand(item.id)}
                          className="text-[10px] uppercase tracking-widest font-sans border border-gold text-gold px-3 py-1.5 hover:bg-gold hover:text-white transition-colors cursor-pointer bg-transparent shrink-0"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => { setEditing(item.id); setEditBrand(item.brand); }}
                        className="font-serif text-base text-near-black cursor-pointer hover:text-gold transition-colors bg-transparent border-none p-0 text-left"
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
                    <div className="h-px bg-cream w-full overflow-hidden">
                      <div
                        className="h-full bg-gold"
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
