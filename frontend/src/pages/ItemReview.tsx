import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/badge";

interface Item {
  id: number;
  brand: string;
  description: string;
  condition_score: number | null;
  status: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "";

function statusVariant(status: string): "keeper" | "seller" | "unranked" {
  if (status === "keeper") return "keeper";
  if (status === "seller") return "seller";
  return "unranked";
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
    <div className="min-h-screen bg-[var(--color-cream)]">
      <header className="border-b border-[var(--color-near-black)]/10 px-6 py-5">
        <h1 className="font-[var(--font-serif)] text-2xl text-[var(--color-near-black)]">
          Item Review
        </h1>
      </header>

      <main className="px-6 py-6 max-w-2xl mx-auto">
        {items.length === 0 ? (
          <p className="text-[var(--color-muted)] text-sm text-center pt-12">
            No items in this collection.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-[var(--color-white)] border border-[var(--color-near-black)]/10 p-5"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex-1 min-w-0">
                    {editing === item.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          value={editBrand}
                          onChange={(e) => setEditBrand(e.target.value)}
                          className="flex-1 min-w-0 px-2 py-1 text-sm border border-[var(--color-gold)] bg-transparent outline-none text-[var(--color-near-black)] transition-colors"
                          autoFocus
                          onKeyDown={(e) => e.key === "Enter" && saveBrand(item.id)}
                        />
                        <button
                          onClick={() => saveBrand(item.id)}
                          className="text-xs px-2 py-1 bg-[var(--color-near-black)] text-[var(--color-white)] cursor-pointer"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => { setEditing(item.id); setEditBrand(item.brand); }}
                        className="font-medium text-[var(--color-near-black)] text-sm hover:text-[var(--color-gold)] transition-colors cursor-pointer text-left"
                        title="Click to edit brand"
                      >
                        {item.brand === "unknown" ? "Unknown brand" : item.brand}
                      </button>
                    )}
                  </div>
                  <Badge variant={statusVariant(item.status)}>
                    {item.status}
                  </Badge>
                </div>

                {item.condition_score !== null && (
                  <div>
                    <div className="flex justify-between text-xs text-[var(--color-muted)] mb-1">
                      <span>Condition</span>
                      <span>{Math.round(item.condition_score * 100)}%</span>
                    </div>
                    <div className="h-0.5 bg-[var(--color-near-black)]/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--color-gold)] transition-all"
                        style={{ width: `${Math.round(item.condition_score * 100)}%` }}
                      />
                    </div>
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
