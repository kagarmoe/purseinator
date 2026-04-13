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
      // Default divider: after top half
      const keeperCount = data.filter((i: RankedItem) => i.status === "keeper").length;
      setDividerIndex(keeperCount > 0 ? keeperCount : Math.ceil(data.length / 2));
    });
  }, [cid]);

  const moveDivider = async (newIndex: number) => {
    if (newIndex < 0 || newIndex > items.length) return;
    setDividerIndex(newIndex);

    // Update statuses based on divider position
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
    <div style={{ padding: "1rem", maxWidth: 500, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "1.5rem", margin: 0 }}>Your Rankings</h1>
        <button
          onClick={() => navigate(`/session/${collectionId}`)}
          style={{ padding: "0.5rem 1rem", borderRadius: 8, background: "#2563eb", color: "white", border: "none", cursor: "pointer" }}
        >
          Rank More
        </button>
      </div>

      {items.length === 0 ? (
        <p style={{ color: "#9ca3af", textAlign: "center" }}>No items ranked yet.</p>
      ) : (
        <div>
          {items.map((item, i) => (
            <div key={item.id}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem",
                  background: i < (dividerIndex ?? 0) ? "#f0fdf4" : "#fef2f2",
                  borderRadius: 8,
                  marginBottom: 2,
                }}
              >
                <span style={{ fontSize: "1.5rem", width: 32, textAlign: "center" }}>
                  {i < (dividerIndex ?? 0) ? "💚" : "🔻"}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>
                    #{i + 1} {item.brand === "unknown" ? "Unknown" : item.brand}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                    Rating: {Math.round(item.rating)} · {item.comparison_count} comparisons
                  </div>
                </div>
              </div>

              {/* Divider line - show after the item at dividerIndex-1 */}
              {dividerIndex !== null && i === dividerIndex - 1 && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.5rem 0",
                    cursor: "grab",
                    userSelect: "none",
                  }}
                  onPointerDown={() => {}}
                >
                  <button
                    onClick={() => moveDivider(dividerIndex - 1)}
                    style={divBtnStyle}
                    aria-label="Move divider up"
                  >
                    ▲
                  </button>
                  <div style={{ flex: 1, height: 3, background: "#f59e0b", borderRadius: 2 }} />
                  <span style={{ fontSize: "0.8rem", color: "#f59e0b", fontWeight: 600, whiteSpace: "nowrap" }}>
                    Keep above · Sell below
                  </span>
                  <div style={{ flex: 1, height: 3, background: "#f59e0b", borderRadius: 2 }} />
                  <button
                    onClick={() => moveDivider(dividerIndex + 1)}
                    style={divBtnStyle}
                    aria-label="Move divider down"
                  >
                    ▼
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const divBtnStyle: React.CSSProperties = {
  width: 36,
  height: 36,
  borderRadius: "50%",
  border: "2px solid #f59e0b",
  background: "white",
  cursor: "pointer",
  fontSize: "0.9rem",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
