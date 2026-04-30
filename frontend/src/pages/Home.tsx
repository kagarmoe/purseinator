import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { devLogin, getCollections, getMe } from "../api";
interface Collection {
  id: number;
  name: string;
  description: string;
}

const IS_DEV = import.meta.env.DEV;

export default function Home() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    Promise.all([getMe(), getCollections()])
      .then(([me, colls]) => {
        setUser(me);
        setCollections(colls);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDevLogin = async () => {
    try {
      const result = await devLogin();
      document.cookie = `session_id=${result.session_id}; path=/`;
      setLoading(true);
      loadData();
    } catch {
      alert("Dev login failed — is the server running?");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-cream)] flex flex-col items-center justify-center px-6">
        <h1 className="font-[var(--font-serif)] text-5xl tracking-tight text-[var(--color-near-black)] mb-12">
          PURSEINATOR
        </h1>
        <div className="w-full max-w-md space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-sm bg-[var(--color-near-black)]/5 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[var(--color-cream)] flex flex-col items-center justify-center px-6 text-center">
        <h1 className="font-[var(--font-serif)] text-6xl tracking-tight text-[var(--color-near-black)] mb-4">
          PURSEINATOR
        </h1>
        <p className="text-[var(--color-muted)] text-sm tracking-widest uppercase mb-12">
          Rank your collection
        </p>
        {IS_DEV && (
          <button
            onClick={handleDevLogin}
            className="px-8 py-3 rounded-full border-2 border-dashed border-[var(--color-gold)] text-[var(--color-gold)] text-sm tracking-wide hover:bg-[var(--color-gold)]/5 transition-colors cursor-pointer"
          >
            Dev Login
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      <header className="border-b border-[var(--color-near-black)]/10 px-6 py-6 text-center">
        <h1 className="font-[var(--font-serif)] text-4xl tracking-tight text-[var(--color-near-black)]">
          PURSEINATOR
        </h1>
        <p className="text-[var(--color-muted)] text-xs tracking-widest uppercase mt-1">
          {user.name}
        </p>
      </header>

      <main className="px-6 py-8 max-w-xl mx-auto">
        <p className="text-[var(--color-muted)] text-xs tracking-widest uppercase mb-6">
          Your Collections
        </p>

        {collections.length === 0 ? (
          <p className="text-[var(--color-muted)] text-sm">
            No collections yet. Ask your operator to set one up.
          </p>
        ) : (
          <div className="space-y-2">
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/session/${c.id}`)}
                className="group w-full text-left px-6 py-5 bg-[var(--color-white)] border border-[var(--color-near-black)]/10 hover:border-[var(--color-gold)] transition-colors duration-200 cursor-pointer"
              >
                <div className="font-semibold text-[var(--color-near-black)] text-base group-hover:text-[var(--color-gold)] transition-colors">
                  {c.name}
                </div>
                {c.description && (
                  <div className="text-[var(--color-muted)] text-sm mt-1">
                    {c.description}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
