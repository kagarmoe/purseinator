import { useNavigate, useParams } from "react-router-dom";

const sessions = [
  {
    minutes: 2,
    label: "Quick Edit",
    description: "A fast curation sprint — 2 minutes.",
    icon: "◇",
  },
  {
    minutes: 5,
    label: "Full Review",
    description: "A thorough session — 5 minutes.",
    icon: "◈",
  },
];

export default function SessionPicker() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const navigate = useNavigate();

  const start = (minutes: number) => {
    navigate(`/rank/${collectionId}?minutes=${minutes}`);
  };

  return (
    <div className="min-h-screen bg-cream flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <p className="text-xs uppercase tracking-[0.25em] text-muted font-sans mb-3 text-center">
          Session
        </p>
        <h1 className="font-serif text-4xl text-near-black text-center mb-2 leading-tight">
          Ready to rank?
        </h1>
        <p className="text-muted text-sm text-center font-sans mb-10">
          Choose how long you'd like to compare.
        </p>

        <div className="space-y-3 mb-8">
          {sessions.map((s, idx) => (
            <button
              key={s.minutes}
              onClick={() => start(s.minutes)}
              className={`group w-full px-6 py-5 text-left transition-colors cursor-pointer ${
                idx === 0
                  ? "bg-terracotta text-white hover:bg-terracotta/90"
                  : "bg-cobalt text-white hover:bg-cobalt/90"
              }`}
            >
              <div className="flex items-start gap-4">
                <span className="text-white/70 text-xl mt-0.5 shrink-0">{s.icon}</span>
                <div>
                  <div className="font-serif text-lg">{s.label}</div>
                  <div className="text-white/70 text-xs font-sans mt-0.5">{s.description}</div>
                </div>
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={() => navigate(`/collection/${collectionId}`)}
          className="w-full text-center text-muted text-xs font-sans uppercase tracking-[0.15em] py-3 border border-dusty-rose hover:border-terracotta hover:text-near-black transition-colors cursor-pointer bg-transparent"
        >
          View Rankings
        </button>
      </div>
    </div>
  );
}
