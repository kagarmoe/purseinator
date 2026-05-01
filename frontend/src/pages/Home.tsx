import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { devLogin, getCollections, getMe, getStaging, requestMagicLink } from "../api";
import { BannerInbox } from "../components/BannerInbox";

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
  const [email, setEmail] = useState("");
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [stagingCount, setStagingCount] = useState(0);
  const [stagingHasMore, setStagingHasMore] = useState(false);

  useEffect(() => {
    Promise.all([getMe(), getCollections(), getStaging({ limit: 200 }).catch(() => null)])
      .then(([me, colls, staging]) => {
        setUser(me);
        setCollections(colls);
        if (staging) {
          setStagingCount(staging.photos.length);
          setStagingHasMore(staging.has_more);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await requestMagicLink(email);
      setMagicLinkSent(true);
    } catch {
      alert("Could not send magic link — is the server running?");
    }
  };

  const handleDevLogin = async () => {
    try {
      const result = await devLogin();
      document.cookie = `session_id=${result.session_id}; path=/; SameSite=Lax`;
      navigate("/dashboard");
    } catch {
      alert("Dev login failed — is the server running?");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="space-y-3 w-full max-w-sm px-6">
          <div className="h-8 bg-dusty-rose/30 rounded animate-pulse" />
          <div className="h-4 bg-dusty-rose/20 rounded w-3/4 animate-pulse" />
          <div className="h-24 bg-dusty-rose/30 rounded animate-pulse" />
          <div className="h-24 bg-dusty-rose/30 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-cream flex flex-col items-center justify-center px-6">
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

          {magicLinkSent ? (
            <p className="text-muted text-sm font-sans">
              Check your email for a sign-in link.
            </p>
          ) : (
            <form onSubmit={handleMagicLink} className="space-y-4 w-full">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="w-full border-b border-muted bg-transparent text-near-black font-sans text-sm px-0 py-2 outline-none focus:border-terracotta transition-colors placeholder:text-muted/50"
              />
              <button
                type="submit"
                className="w-full bg-terracotta text-white font-sans text-sm font-medium py-3 hover:bg-terracotta/80 transition-colors cursor-pointer"
              >
                Send Link
              </button>
            </form>
          )}

          {IS_DEV && (
            <button
              onClick={handleDevLogin}
              className="mt-6 px-8 py-3 border-2 border-dashed border-terracotta text-terracotta text-sm font-sans font-medium rounded-full hover:bg-terracotta hover:text-white transition-colors cursor-pointer"
            >
              Dev Login
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream">
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
        <BannerInbox count={stagingCount} hasMore={stagingHasMore} />

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
                className="group w-full text-left bg-dusty-rose/20 border-l-4 border-l-terracotta border border-dusty-rose px-6 py-5 hover:bg-dusty-rose/40 transition-colors cursor-pointer"
              >
                <div className="font-serif text-lg text-near-black group-hover:text-terracotta transition-colors">{c.name}</div>
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
