import { useNavigate, useParams } from "react-router-dom";
import { Clock, Timer, LayoutList } from "lucide-react";

const sessions = [
  {
    minutes: 2,
    icon: Clock,
    label: "Quick Session",
    description: "A swift round of comparisons",
  },
  {
    minutes: 5,
    icon: Timer,
    label: "Full Session",
    description: "Deep dive into your collection",
  },
];

export default function SessionPicker() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const navigate = useNavigate();

  const start = (minutes: number) => {
    navigate(`/rank/${collectionId}?minutes=${minutes}`);
  };

  return (
    <div className="min-h-screen bg-[var(--color-cream)] flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="font-[var(--font-serif)] text-4xl text-[var(--color-near-black)] text-center mb-2">
          Ready to rank?
        </h1>
        <p className="text-[var(--color-muted)] text-xs tracking-widest uppercase text-center mb-10">
          Choose your session length
        </p>

        <div className="space-y-3 mb-6">
          {sessions.map(({ minutes, icon: Icon, label, description }) => (
            <button
              key={minutes}
              onClick={() => start(minutes)}
              className="group w-full text-left bg-[var(--color-white)] border border-[var(--color-near-black)]/10 hover:border-[var(--color-gold)] px-6 py-5 transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-start gap-4">
                <Icon
                  size={20}
                  className="text-[var(--color-gold)] mt-0.5 shrink-0"
                />
                <div>
                  <div className="font-semibold text-[var(--color-near-black)] group-hover:text-[var(--color-gold)] transition-colors">
                    {label}
                  </div>
                  <div className="text-[var(--color-muted)] text-sm mt-0.5">
                    {description}
                  </div>
                </div>
                <span className="ml-auto text-[var(--color-muted)] text-xs self-center shrink-0">
                  {minutes} min
                </span>
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={() => navigate(`/collection/${collectionId}`)}
          className="group w-full text-left bg-transparent border border-[var(--color-near-black)]/10 hover:border-[var(--color-near-black)]/30 px-6 py-4 transition-all duration-200 cursor-pointer"
        >
          <div className="flex items-center gap-4">
            <LayoutList
              size={20}
              className="text-[var(--color-muted)] shrink-0"
            />
            <div>
              <div className="font-medium text-[var(--color-near-black)] text-sm">
                View Rankings
              </div>
              <div className="text-[var(--color-muted)] text-xs mt-0.5">
                See your current standings
              </div>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}
