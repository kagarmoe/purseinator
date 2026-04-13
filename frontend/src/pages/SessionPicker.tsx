import { useNavigate, useParams } from "react-router-dom";

export default function SessionPicker() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const navigate = useNavigate();

  const start = (minutes: number) => {
    navigate(`/rank/${collectionId}?minutes=${minutes}`);
  };

  return (
    <div style={{ padding: "2rem", textAlign: "center", maxWidth: 400, margin: "0 auto" }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "1rem" }}>Ready to rank?</h1>
      <p style={{ fontSize: "1.1rem", color: "#666", marginBottom: "2rem" }}>
        Pick how long you'd like to compare bags.
      </p>
      <button onClick={() => start(2)} style={btnStyle}>
        Quick Session (2 min)
      </button>
      <button onClick={() => start(5)} style={{ ...btnStyle, background: "#7c3aed" }}>
        Full Session (5 min)
      </button>
      <button
        onClick={() => navigate(`/collection/${collectionId}`)}
        style={{ ...btnStyle, background: "#6b7280", fontSize: "1rem", padding: "1rem" }}
      >
        View Rankings
      </button>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "1.5rem",
  marginBottom: "1rem",
  fontSize: "1.25rem",
  fontWeight: 600,
  color: "white",
  background: "#2563eb",
  border: "none",
  borderRadius: 12,
  cursor: "pointer",
  minHeight: 64,
};
