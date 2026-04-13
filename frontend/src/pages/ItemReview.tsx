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
    <div style={{ padding: "1.5rem", maxWidth: 600, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>Item Review</h1>

      {items.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No items in this collection.</p>
      ) : (
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {items.map((item) => (
            <div
              key={item.id}
              style={{
                padding: "1rem",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                background: "white",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  {editing === item.id ? (
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      <input
                        value={editBrand}
                        onChange={(e) => setEditBrand(e.target.value)}
                        style={{ padding: "0.25rem 0.5rem", borderRadius: 4, border: "1px solid #d1d5db" }}
                        autoFocus
                      />
                      <button
                        onClick={() => saveBrand(item.id)}
                        style={{ padding: "0.25rem 0.5rem", borderRadius: 4, background: "#2563eb", color: "white", border: "none", cursor: "pointer" }}
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <span
                      onClick={() => { setEditing(item.id); setEditBrand(item.brand); }}
                      style={{ fontWeight: 600, cursor: "pointer" }}
                      title="Click to edit brand"
                    >
                      {item.brand === "unknown" ? "Unknown brand" : item.brand}
                    </span>
                  )}
                </div>
                <span
                  style={{
                    padding: "0.25rem 0.5rem",
                    borderRadius: 4,
                    fontSize: "0.8rem",
                    background:
                      item.status === "keeper" ? "#dcfce7" :
                      item.status === "seller" ? "#fee2e2" : "#f3f4f6",
                    color:
                      item.status === "keeper" ? "#166534" :
                      item.status === "seller" ? "#991b1b" : "#6b7280",
                  }}
                >
                  {item.status}
                </span>
              </div>
              {item.condition_score !== null && (
                <div style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.25rem" }}>
                  Condition: {Math.round(item.condition_score * 100)}%
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
