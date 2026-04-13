interface Item {
  id: number;
  brand: string;
  description: string;
  condition_score: number | null;
}

interface Props {
  itemA: Item;
  itemB: Item;
  infoLevel: string;
  onPick: (winnerId: number) => void;
}

export default function ComparisonCard({ itemA, itemB, infoLevel, onPick }: Props) {
  return (
    <div style={{ display: "flex", gap: "1rem", justifyContent: "center", padding: "1rem" }}>
      <ItemCard item={itemA} infoLevel={infoLevel} onTap={() => onPick(itemA.id)} />
      <div style={{ display: "flex", alignItems: "center", fontSize: "1.5rem", color: "#9ca3af" }}>
        or
      </div>
      <ItemCard item={itemB} infoLevel={infoLevel} onTap={() => onPick(itemB.id)} />
    </div>
  );
}

function ItemCard({
  item,
  infoLevel,
  onTap,
}: {
  item: Item;
  infoLevel: string;
  onTap: () => void;
}) {
  const showBrand = infoLevel !== "photos_only";
  const showCondition = infoLevel === "condition" || infoLevel === "price";

  return (
    <button
      onClick={onTap}
      style={{
        flex: 1,
        maxWidth: 300,
        minHeight: 200,
        padding: "1rem",
        border: "2px solid #e5e7eb",
        borderRadius: 16,
        background: "white",
        cursor: "pointer",
        textAlign: "center",
        transition: "transform 0.1s, border-color 0.1s",
      }}
      onPointerDown={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(0.97)";
        (e.currentTarget as HTMLElement).style.borderColor = "#2563eb";
      }}
      onPointerUp={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(1)";
        (e.currentTarget as HTMLElement).style.borderColor = "#e5e7eb";
      }}
      onPointerLeave={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(1)";
        (e.currentTarget as HTMLElement).style.borderColor = "#e5e7eb";
      }}
    >
      <div
        style={{
          width: "100%",
          height: 140,
          background: "#f3f4f6",
          borderRadius: 8,
          marginBottom: "0.75rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "3rem",
        }}
      >
        👜
      </div>
      {showBrand && (
        <div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
          {item.brand === "unknown" ? "Unknown brand" : item.brand}
        </div>
      )}
      {showCondition && item.condition_score !== null && (
        <div style={{ color: "#6b7280", fontSize: "0.9rem", marginTop: "0.25rem" }}>
          Condition: {Math.round(item.condition_score * 100)}%
        </div>
      )}
    </button>
  );
}
