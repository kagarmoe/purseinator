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
    <div className="flex items-center gap-4 justify-center w-full max-w-xl px-2">
      <ItemCard item={itemA} infoLevel={infoLevel} onTap={() => onPick(itemA.id)} />
      <span className="text-[10px] uppercase tracking-widest text-muted font-sans shrink-0">or</span>
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
      className={`group flex-1 max-w-56 min-h-52 p-5 text-center cursor-pointer transition-all duration-200 hover:scale-[1.03] hover:shadow-lg active:scale-[0.98] border-2 hover:border-terracotta ${
        item.id % 2 === 0
          ? "bg-dusty-rose/25 border-dusty-rose"
          : "bg-cobalt/10 border-cobalt/20"
      }`}
    >
      {/* warm gradient placeholder */}
      <div className={`w-full h-36 mb-4 rounded-sm ${
        item.id % 2 === 0
          ? "bg-gradient-to-br from-dusty-rose/40 to-terracotta/20"
          : "bg-gradient-to-br from-cobalt/20 to-saffron/10"
      }`} />

      {showBrand && (
        <div className="font-serif text-base text-near-black">
          {item.brand === "unknown" ? "Unknown" : item.brand}
        </div>
      )}
      {showCondition && item.condition_score !== null && (
        <div className="mt-2">
          <div className="h-0.5 bg-cream w-full rounded-full overflow-hidden">
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
    </button>
  );
}
