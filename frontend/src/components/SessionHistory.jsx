export default function SessionHistory({ sessions, onSelect, onNewSession, loading }) {
  const grouped = sessions.reduce((acc, item) => {
    const key = item.subject || "General";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  const subjectOrder = Object.keys(grouped).sort((a, b) => {
    if (a === "General") return 1;
    if (b === "General") return -1;
    return a.localeCompare(b);
  });

  return (
    <aside className="w-full md:w-72 shrink-0 h-full">
      <div className="h-full flex flex-col rounded-3xl border-2 border-ink/10 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between shrink-0">
          <h2 className="font-display text-xl font-bold text-ink">Your Sessions</h2>
          <button
            onClick={onNewSession}
            className="rounded-xl bg-sunshine px-3 py-2 font-display text-sm font-bold text-ink shadow-sm transition hover:-translate-y-0.5"
          >
            + New
          </button>
        </div>

        {loading && (
          <p className="py-4 text-center font-body text-sm text-ink/50">Loading...</p>
        )}

        {!loading && sessions.length === 0 && (
          <p className="rounded-2xl bg-cream px-4 py-5 text-center font-body text-sm leading-6 text-ink/55">
            Your completed and active learning sessions will appear here.
          </p>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto pr-1 space-y-5">
          {subjectOrder.map((subjectName) => (
            <div key={subjectName}>
              <h3 className="font-display text-xs font-bold uppercase tracking-wide text-grape/70 mb-2 px-1">
                {subjectName}
              </h3>
              <div className="space-y-2">
                {grouped[subjectName].map((item) => (
                  <button
                    key={item.session_id}
                    onClick={() => onSelect(item.session_id)}
                    className="w-full rounded-2xl border-2 border-transparent bg-cream px-4 py-3 text-left transition hover:border-sky hover:bg-sky/10"
                  >
                    <div className="font-display font-bold text-ink">{item.topic}</div>
                    <div className="mt-1 font-body text-xs font-semibold text-ink/50">
                      {item.turn_count} {item.turn_count === 1 ? "turn" : "turns"} ·{" "}
                      {item.total_concepts ?? 0} {item.total_concepts === 1 ? "concept" : "concepts"}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}