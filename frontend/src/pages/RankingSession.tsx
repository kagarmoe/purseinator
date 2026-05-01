import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
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

  const fetchNext = async () => {
    try {
      const data = await getNextPair(cid);
      setPair(data);
    } catch {
      setError("Could not load next pair");
    }
  };

  useEffect(() => {
    let mounted = true;
    getNextPair(cid)
      .then((data) => { if (mounted) setPair(data); })
      .catch(() => { if (mounted) setError("Could not load next pair"); });
    return () => { mounted = false; };
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
      await fetchNext();
    } catch {
      setError("Could not save comparison");
    }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  const progressPct = Math.max(0, (timeLeft / (minutes * 60)) * 100);

  if (done) {
    return (
      <div className="min-h-screen bg-cream flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-4">
            Session Complete
          </p>
          <h1 className="font-serif text-4xl text-near-black mb-3">Well done.</h1>
          <p className="text-muted text-sm font-sans mb-10">
            You compared {count} {count === 1 ? "pair" : "pairs"}.
          </p>
          <div className="space-y-3">
            <button
              onClick={() => navigate(`/collection/${collectionId}`)}
              className="w-full bg-terracotta text-white font-sans text-sm font-medium py-4 hover:bg-terracotta/80 transition-colors cursor-pointer"
            >
              See Your Rankings
            </button>
            <button
              onClick={() => navigate(`/session/${collectionId}`)}
              className="w-full bg-cobalt text-white font-sans text-sm py-4 hover:bg-cobalt/80 transition-colors cursor-pointer"
            >
              Another Session
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      {/* slim progress bar at top edge */}
      <div className="h-0.5 bg-terracotta/20 w-full">
        <div
          className="h-full bg-terracotta transition-all duration-1000 ease-linear"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* header bar */}
      <div className="flex items-center justify-between px-6 py-4">
        <span className="font-serif text-lg text-near-black">{formatTime(timeLeft)}</span>
        <div className="flex items-center gap-3">
          <Link
            to={`/upload?suggest=${cid}`}
            className="text-cobalt underline-offset-4 hover:underline text-sm font-sans hidden sm:inline"
          >
            + Add photos to this collection
          </Link>
          <span className="text-xs font-sans bg-cream text-muted px-3 py-1 rounded-full">
            {count} compared
          </span>
        </div>
        <button
          onClick={() => { clearInterval(timerRef.current); setDone(true); }}
          className="text-xs font-sans uppercase tracking-[0.1em] bg-cobalt text-white px-4 py-1.5 hover:bg-cobalt/80 transition-colors cursor-pointer"
        >
          Done
        </button>
      </div>
      {/* Mobile: show discoverability link below header */}
      <div className="px-6 pb-2 sm:hidden">
        <Link
          to={`/upload?suggest=${cid}`}
          className="text-cobalt underline-offset-4 hover:underline text-sm font-sans"
        >
          + Add photos to this collection
        </Link>
      </div>

      {/* main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        {error && (
          <p className="text-red-500 text-sm font-sans text-center mb-4">{error}</p>
        )}

        {pair ? (
          <ComparisonCard
            itemA={pair.item_a}
            itemB={pair.item_b}
            infoLevel={pair.info_level}
            onPick={handlePick}
          />
        ) : (
          <p className="text-muted text-sm font-sans">Loading...</p>
        )}

        <p className="text-muted text-xs font-sans uppercase tracking-[0.15em] mt-8">
          Tap the piece you'd rather keep
        </p>
      </div>
    </div>
  );
}
