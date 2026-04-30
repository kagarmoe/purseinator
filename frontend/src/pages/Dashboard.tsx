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
    Promise.all([getMe(), getCollections()]).then(([me, colls]) => {
      setUser(me);
      setCollections(colls);
    });
  }, []);

  if (!user) {
    return (
      <div className="min-h-screen bg-[var(--color-cream)] flex items-center justify-center">
        <div className="w-48 h-4 bg-[var(--color-near-black)]/5 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      <header className="border-b border-[var(--color-near-black)]/10 px-6 py-5">
        <h1 className="font-[var(--font-serif)] text-2xl text-[var(--color-near-black)]">
          Dashboard
        </h1>
        <p className="text-[var(--color-muted)] text-xs mt-1">{user.name}</p>
      </header>

      <main className="px-6 py-8 max-w-2xl mx-auto">
        <p className="text-[var(--color-near-black)] text-xs tracking-widest uppercase font-medium mb-4 [font-variant:small-caps]">
          Collections
        </p>

        {collections.length === 0 ? (
          <p className="text-[var(--color-muted)] text-sm">
            No collections yet. Use the CLI to create one.
          </p>
        ) : (
          <div className="border-t border-[var(--color-near-black)]/10">
            {collections.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between py-4 border-b border-[var(--color-near-black)]/10"
              >
                <div className="min-w-0 flex-1 pr-4">
                  <div className="font-medium text-[var(--color-near-black)]">
                    {c.name}
                  </div>
                  {c.description && (
                    <div className="text-[var(--color-muted)] text-sm mt-0.5 truncate">
                      {c.description}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => navigate(`/review/${c.id}`)}
                  className="shrink-0 text-xs tracking-wide border border-[var(--color-near-black)]/20 px-4 py-2 text-[var(--color-near-black)] hover:border-[var(--color-near-black)]/40 transition-colors cursor-pointer"
                >
                  Review Items
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
