import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { verifyToken } from "../api";

export default function Verify() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      navigate("/");
      return;
    }
    verifyToken(token)
      .then((data) => {
        document.cookie = `session_id=${data.session_id}; path=/; SameSite=Lax`;
        navigate("/dashboard");
      })
      .catch(() =>
        setError("Invalid or expired link. Please request a new one.")
      );
  }, [navigate, searchParams]);

  if (error) {
    return (
      <div className="min-h-svh bg-cream flex items-center justify-center px-6">
        <div className="text-center max-w-xs">
          <p className="text-terracotta text-sm font-sans">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 text-muted text-xs font-sans underline cursor-pointer"
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-svh bg-cream flex items-center justify-center">
      <p className="text-muted text-sm font-sans">Signing you in…</p>
    </div>
  );
}
