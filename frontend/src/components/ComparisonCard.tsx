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
    <div className="flex items-center gap-4 w-full max-w-2xl">
      <ItemCard item={itemA} infoLevel={infoLevel} onTap={() => onPick(itemA.id)} />

      <div className="flex flex-col items-center shrink-0">
        <span className="text-[var(--color-muted)] text-xs tracking-widest uppercase">
          or
        </span>
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
      className="group flex-1 min-h-[220px] bg-[var(--color-white)] border border-[var(--color-near-black)]/10 cursor-pointer text-center transition-all duration-200 hover:scale-[1.03] hover:shadow-xl hover:shadow-[var(--color-near-black)]/10 hover:border-[var(--color-near-black)]/20 p-5 flex flex-col items-center"
    >
      {/* Elegant gradient placeholder */}
      <div className="w-full h-36 rounded-sm mb-4 bg-gradient-to-br from-[var(--color-cream)] via-[var(--color-gold)]/10 to-[var(--color-near-black)]/5 shrink-0" />

      {showBrand && (
        <div className="font-[var(--font-serif)] font-semibold text-[var(--color-near-black)] text-base">
          {item.brand === "unknown" ? "Unknown" : item.brand}
        </div>
      )}
      {showCondition && item.condition_score !== null && (
        <div className="text-[var(--color-muted)] text-xs mt-1.5">
          Condition: {Math.round(item.condition_score * 100)}%
        </div>
      )}
    </button>
  );
}
