import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import ComparisonCard from "../components/ComparisonCard";
import { getNextPair, submitComparison } from "../api";

interface PairData {
  item_a: { id: number; brand: string; description: string; condition_score: number | null };
  item_b: { id: number; brand: string; description: string; condition_score: number | null };
  info_level: string;
}

export default function RankingSession() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const cid = Number(collectionId);
  const minutes = Number(searchParams.get("minutes") || 2);

  const [pair, setPair] = useState<PairData | null>(null);
  const [count, setCount] = useState(0);
  const [timeLeft, setTimeLeft] = useState(minutes * 60);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          setDone(true);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Load initial pair
  useEffect(() => {
    let cancelled = false;
    getNextPair(cid)
      .then((data) => { if (!cancelled) setPair(data); })
      .catch(() => { if (!cancelled) setError("Could not load next pair"); });
    return () => { cancelled = true; };
  }, [cid]);

  const handlePick = async (winnerId: number) => {
    if (!pair) return;
    try {
      await submitComparison(cid, {
        item_a_id: pair.item_a.id,
        item_b_id: pair.item_b.id,
        winner_id: winnerId,
        info_level_shown: pair.info_level,
      });
      setCount((c) => c + 1);
      const next = await getNextPair(cid);
      setPair(next);
    } catch {
      setError("Could not save comparison");
    }
  };

  const progress = Math.max(0, (timeLeft / (minutes * 60)) * 100);

  if (done) {
    return (
      <div className="min-h-screen bg-[var(--color-cream)] flex flex-col items-center justify-center px-6 text-center">
        <p className="text-[var(--color-muted)] text-xs tracking-widest uppercase mb-4">
          Session complete
        </p>
        <h1 className="font-[var(--font-serif)] text-4xl text-[var(--color-near-black)] mb-2">
          Nice work.
        </h1>
        <p className="text-[var(--color-muted)] mb-10">
          You compared {count} {count === 1 ? "pair" : "pairs"}.
        </p>
        <div className="w-full max-w-xs space-y-3">
          <button
            onClick={() => navigate(`/collection/${collectionId}`)}
            className="w-full py-4 bg-[var(--color-near-black)] text-[var(--color-white)] text-sm tracking-wide hover:bg-[var(--color-near-black)]/90 transition-colors cursor-pointer"
          >
            See Rankings
          </button>
          <button
            onClick={() => navigate(`/session/${collectionId}`)}
            className="w-full py-4 border border-[var(--color-near-black)]/20 text-[var(--color-near-black)] text-sm tracking-wide hover:border-[var(--color-near-black)]/40 transition-colors cursor-pointer"
          >
            Another Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-cream)] flex flex-col">
      {/* Slim progress bar at top edge */}
      <div className="h-0.5 bg-[var(--color-near-black)]/10 w-full shrink-0">
        <div
          className="h-full bg-[var(--color-gold)] transition-all duration-1000 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Top controls */}
      <div className="flex items-center justify-between px-6 py-4">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs text-[var(--color-muted)] border border-[var(--color-near-black)]/10 rounded-full">
          {count} compared
        </span>
        <button
          onClick={() => { clearInterval(timerRef.current); setDone(true); }}
          className="text-sm text-[var(--color-muted)] hover:text-[var(--color-near-black)] transition-colors cursor-pointer border border-transparent hover:border-[var(--color-near-black)]/10 px-3 py-1 rounded-sm"
        >
          Done
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        {error && (
          <p className="text-red-500 text-sm text-center mb-4">{error}</p>
        )}

        {pair ? (
          <ComparisonCard
            itemA={pair.item_a}
            itemB={pair.item_b}
            infoLevel={pair.info_level}
            onPick={handlePick}
          />
        ) : (
          <div className="text-[var(--color-muted)] text-sm">Loading...</div>
        )}

        <p className="text-[var(--color-muted)] text-xs tracking-widest uppercase mt-8">
          Tap the piece you would keep
        </p>
      </div>
    </div>
  );
}
