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
      <div className="min-h-svh bg-surface flex items-center justify-center">
        <div className="space-y-3 w-full max-w-sm px-6">
          <div className="h-8 bg-cream rounded animate-pulse" />
          <div className="h-4 bg-cream rounded w-3/4 animate-pulse" />
          <div className="h-24 bg-cream rounded animate-pulse" />
          <div className="h-24 bg-cream rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-svh bg-surface flex flex-col items-center justify-center px-6">
        <div className="text-center max-w-xs w-full">
          <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-4">
            The Collection Edit
          </p>
          <h1 className="font-serif text-5xl text-near-black mb-6 leading-none">
            PURSEINATOR
          </h1>
          <p className="text-muted text-sm mb-10 font-sans">
            Sign in to start curating your collection.
          </p>
          {IS_DEV && (
            <button
              onClick={handleDevLogin}
              className="px-8 py-3 border-2 border-dashed border-gold text-gold text-sm font-sans font-medium rounded-full hover:bg-gold hover:text-white transition-colors cursor-pointer"
            >
              Dev Login
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-surface">
      <header className="px-6 pt-12 pb-8 border-b border-cream">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-2">
          The Collection Edit
        </p>
        <h1 className="font-serif text-4xl text-near-black leading-tight">
          PURSEINATOR
        </h1>
        <p className="text-muted text-sm mt-2 font-sans">
          Welcome back, {user.name}.
        </p>
      </header>

      <main className="px-6 py-8 max-w-lg mx-auto">
        <h2 className="text-xs uppercase tracking-[0.2em] text-muted font-sans mb-6">
          Your Collections
        </h2>

        {collections.length === 0 ? (
          <p className="text-muted text-sm font-sans italic">
            No collections yet. Ask your operator to set one up.
          </p>
        ) : (
          <div className="space-y-3">
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/session/${c.id}`)}
                className="group w-full text-left bg-white border border-cream px-6 py-5 hover:border-gold transition-colors cursor-pointer relative overflow-hidden"
              >
                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gold opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="font-serif text-lg text-near-black">{c.name}</div>
                {c.description && (
                  <div className="text-muted text-xs font-sans mt-1">{c.description}</div>
                )}
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
