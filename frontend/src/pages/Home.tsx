import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCollections, getMe } from "../api";

interface Collection {
  id: number;
  name: string;
  description: string;
}

export default function Home() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getMe(), getCollections()])
      .then(([me, colls]) => {
        setUser(me);
        setCollections(colls);
      })
      .catch(() => {
        // Not logged in
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p style={{ textAlign: "center", padding: "2rem", color: "#9ca3af" }}>Loading...</p>;
  }

  if (!user) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", maxWidth: 400, margin: "0 auto" }}>
        <h1 style={{ fontSize: "2rem" }}>Bagfolio</h1>
        <p style={{ color: "#666" }}>Sign in to start ranking your collection.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 500, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>Hi, {user.name}!</h1>
      <p style={{ color: "#6b7280", marginBottom: "1.5rem" }}>Choose a collection to rank.</p>

      {collections.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No collections yet. Ask your operator to set one up.</p>
      ) : (
        collections.map((c) => (
          <button
            key={c.id}
            onClick={() => navigate(`/session/${c.id}`)}
            style={{
              display: "block",
              width: "100%",
              padding: "1.25rem",
              marginBottom: "0.75rem",
              textAlign: "left",
              border: "2px solid #e5e7eb",
              borderRadius: 12,
              background: "white",
              cursor: "pointer",
              fontSize: "1.1rem",
            }}
          >
            <div style={{ fontWeight: 600 }}>{c.name}</div>
            {c.description && (
              <div style={{ color: "#6b7280", fontSize: "0.9rem", marginTop: "0.25rem" }}>
                {c.description}
              </div>
            )}
          </button>
        ))
      )}
    </div>
  );
}
