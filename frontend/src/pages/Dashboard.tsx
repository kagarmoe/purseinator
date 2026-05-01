import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCollections, getMe } from "../api";

interface Collection {
  id: number;
  name: string;
  description: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);

  useEffect(() => {
    Promise.all([getMe(), getCollections()])
      .then(([me, colls]) => {
        setUser(me);
        setCollections(colls);
      })
      .catch(() => navigate("/"));
  }, []);

  if (!user) {
    return (
      <div className="min-h-svh bg-cream flex items-center justify-center">
        <p className="text-muted text-sm font-sans">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-cream">
      <header className="px-6 pt-10 pb-6 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-1">
          Operator
        </p>
        <h1 className="font-serif text-3xl text-near-black leading-tight">Dashboard</h1>
      </header>

      <main className="px-6 py-8 max-w-2xl mx-auto">
        <h2 className="text-[10px] uppercase tracking-[0.3em] text-muted font-sans mb-6">
          Collections
        </h2>

        {collections.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">
            No collections yet. Use the CLI to create one.
          </p>
        ) : (
          <div className="divide-y divide-cream">
            {collections.map((c) => (
              <div
                key={c.id}
                className="py-4 flex items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="font-serif text-base text-near-black">{c.name}</div>
                  {c.description && (
                    <div className="text-muted text-xs font-sans mt-0.5">{c.description}</div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => navigate(`/collection/${c.id}`)}
                    className="text-xs font-sans uppercase tracking-[0.1em] border border-cobalt text-cobalt px-4 py-2 hover:bg-cobalt hover:text-white transition-colors cursor-pointer"
                  >
                    View Rankings
                  </button>
                  <button
                    onClick={() => navigate(`/review/${c.id}`)}
                    className="text-xs font-sans uppercase tracking-[0.1em] bg-terracotta text-white px-4 py-2 hover:bg-terracotta/80 transition-colors cursor-pointer"
                  >
                    Review Items
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
