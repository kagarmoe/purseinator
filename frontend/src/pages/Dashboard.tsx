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

  if (!user) return <p style={{ padding: "2rem", textAlign: "center" }}>Loading...</p>;

  return (
    <div style={{ padding: "1.5rem", maxWidth: 600, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "1rem" }}>Operator Dashboard</h1>

      <h2 style={{ fontSize: "1.2rem", color: "#6b7280", marginBottom: "0.75rem" }}>Collections</h2>

      {collections.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No collections yet. Use the CLI to create one.</p>
      ) : (
        collections.map((c) => (
          <div
            key={c.id}
            style={{
              padding: "1rem",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              marginBottom: "0.5rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{c.name}</div>
              {c.description && (
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>{c.description}</div>
              )}
            </div>
            <button
              onClick={() => navigate(`/review/${c.id}`)}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: 6,
                border: "1px solid #d1d5db",
                background: "white",
                cursor: "pointer",
              }}
            >
              Review Items
            </button>
          </div>
        ))
      )}
    </div>
  );
}
