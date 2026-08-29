import { useMemo, useState } from "react";

const TOPIC_SUGGESTIONS = ["Photosynthesis", "The Water Cycle", "Fractions", "Dinosaurs", "The Solar System"];
const SUBJECT_SUGGESTIONS = ["General", "Biology", "Math", "Physics", "History", "Chemistry"];

export default function TopicSelector({ sessions = [], onStart, onContinue, loading }) {
  const [topic, setTopic] = useState("");
  const [subject, setSubject] = useState("General");
  const [prereq, setPrereq] = useState("");
  const [dismissedMatch, setDismissedMatch] = useState(false);

  const existingMatch = useMemo(() => {
    const normalized = topic.trim().toLowerCase();
    if (!normalized) return null;
    return sessions.find((s) => (s.topic || "").trim().toLowerCase() === normalized) || null;
  }, [topic, sessions]);

  const showMatch = existingMatch && !dismissedMatch;

  function handleTopicChange(value) {
    setTopic(value);
    setDismissedMatch(false);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (topic.trim()) onStart(topic.trim(), subject.trim() || "General", prereq.trim());
  }

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-8">
      <div className="max-w-md w-full text-center">
        <h1 className="font-display text-5xl text-grape mb-2">Feyn AI</h1>
        <p className="font-body text-ink/80 mb-8 text-lg">
          I'm a little AI who doesn't know anything yet.
          <br />
          Will you teach me something?
        </p>

        <form onSubmit={handleSubmit} className="bg-white rounded-3xl border-4 border-bubblegum p-6 shadow-xl text-left">
          <label className="block font-display text-grape text-sm mb-2">
            What should I learn about?
          </label>
          <input
            value={topic}
            onChange={(e) => handleTopicChange(e.target.value)}
            placeholder="Type a topic..."
            className="w-full rounded-2xl border-2 border-sky/50 px-4 py-3 font-body text-lg
                       focus:outline-none focus:border-sky focus:ring-4 focus:ring-sky/20 mb-4"
          />
          <div className="flex flex-wrap gap-2 mb-5">
            {TOPIC_SUGGESTIONS.map((s) => (
              <button
                type="button"
                key={s}
                onClick={() => handleTopicChange(s)}
                className="text-sm font-body bg-sunshine/30 hover:bg-sunshine/60 text-ink
                           rounded-full px-3 py-1 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>

          {showMatch && (
            <div className="mb-5 rounded-2xl border-2 border-grass/50 bg-grass/10 px-4 py-3">
              <p className="font-body text-sm text-ink/80 mb-2">
                You've taught me about <strong>{existingMatch.topic}</strong> before
                ({existingMatch.turn_count} {existingMatch.turn_count === 1 ? "turn" : "turns"} ·{" "}
                {existingMatch.total_concepts ?? 0}{" "}
                {existingMatch.total_concepts === 1 ? "concept" : "concepts"}).
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => onContinue(existingMatch.session_id)}
                  className="flex-1 bg-grass hover:bg-grass/90 text-white font-display text-sm font-bold
                             rounded-xl py-2 transition-transform active:scale-95"
                >
                  Continue that session
                </button>
                <button
                  type="button"
                  onClick={() => setDismissedMatch(true)}
                  className="flex-1 bg-white border-2 border-grass/40 text-ink font-display text-sm font-bold
                             rounded-xl py-2 transition-colors hover:bg-grass/5"
                >
                  Start fresh instead
                </button>
              </div>
            </div>
          )}

          <label className="block font-display text-grape text-sm mb-2">
            Subject
          </label>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Biology"
            className="w-full rounded-2xl border-2 border-grape/40 px-4 py-2.5 font-body
                       focus:outline-none focus:border-grape focus:ring-4 focus:ring-grape/20 mb-3"
          />
          <div className="flex flex-wrap gap-2 mb-5">
            {SUBJECT_SUGGESTIONS.map((s) => (
              <button
                type="button"
                key={s}
                onClick={() => setSubject(s)}
                className={`text-sm font-body rounded-full px-3 py-1 transition-colors ${
                  subject === s ? "bg-grape text-white" : "bg-grape/10 hover:bg-grape/20 text-ink"
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          <label className="block font-display text-grape text-sm mb-2">
            Anything I should already know? <span className="text-ink/40 font-body">(optional)</span>
          </label>
          <textarea
            value={prereq}
            onChange={(e) => setPrereq(e.target.value)}
            placeholder="e.g. basic vocab, definitions you don't want to re-explain..."
            rows={3}
            className="w-full rounded-2xl border-2 border-grass/50 px-4 py-3 font-body text-sm
                       focus:outline-none focus:border-grass focus:ring-4 focus:ring-grass/20 mb-5"
          />

          <button
            type="submit"
            disabled={loading || !topic.trim()}
            className="w-full bg-bubblegum hover:bg-bubblegum/90 disabled:opacity-50
           text-white font-display text-lg font-bold rounded-2xl py-3
           shadow-md transition-transform active:scale-95"
          >
            {loading ? "Starting..." : "Start teaching!"}
          </button>
        </form>
      </div>
    </div>
  );
}