import { useCallback, useEffect, useRef, useState } from "react";
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

  const loadNext = useCallback(async () => {
    try {
      const data = await getNextPair(cid);
      setPair(data);
    } catch (e) {
      setError("Could not load next pair");
    }
  }, [cid]);

  useEffect(() => {
    loadNext();
  }, [loadNext]);

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
      await loadNext();
    } catch {
      setError("Could not save comparison");
    }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  if (done) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", maxWidth: 400, margin: "0 auto" }}>
        <h1 style={{ fontSize: "2rem" }}>Nice work!</h1>
        <p style={{ fontSize: "1.2rem", color: "#666", margin: "1rem 0" }}>
          You compared {count} pairs.
        </p>
        <button
          onClick={() => navigate(`/collection/${collectionId}`)}
          style={actionBtn}
        >
          See Your Rankings
        </button>
        <button
          onClick={() => navigate(`/session/${collectionId}`)}
          style={{ ...actionBtn, background: "#6b7280" }}
        >
          Another Session
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem", maxWidth: 700, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <span style={{ fontSize: "1.1rem", fontWeight: 600 }}>
          {formatTime(timeLeft)}
        </span>
        <span style={{ color: "#6b7280" }}>{count} compared</span>
        <button
          onClick={() => { clearInterval(timerRef.current); setDone(true); }}
          style={{ padding: "0.5rem 1rem", borderRadius: 8, border: "1px solid #d1d5db", background: "white", cursor: "pointer" }}
        >
          Done
        </button>
      </div>

      <div style={{ height: 4, background: "#e5e7eb", borderRadius: 2, marginBottom: "1rem" }}>
        <div
          style={{
            height: "100%",
            background: "#2563eb",
            borderRadius: 2,
            width: `${Math.max(0, (timeLeft / (minutes * 60)) * 100)}%`,
            transition: "width 1s linear",
          }}
        />
      </div>

      {error && <p style={{ color: "red", textAlign: "center" }}>{error}</p>}

      {pair ? (
        <ComparisonCard
          itemA={pair.item_a}
          itemB={pair.item_b}
          infoLevel={pair.info_level}
          onPick={handlePick}
        />
      ) : (
        <p style={{ textAlign: "center", color: "#9ca3af" }}>Loading...</p>
      )}

      <p style={{ textAlign: "center", color: "#9ca3af", marginTop: "1rem", fontSize: "0.9rem" }}>
        Tap the bag you'd rather keep
      </p>
    </div>
  );
}

const actionBtn: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "1.25rem",
  marginBottom: "0.75rem",
  fontSize: "1.1rem",
  fontWeight: 600,
  color: "white",
  background: "#2563eb",
  border: "none",
  borderRadius: 12,
  cursor: "pointer",
};
