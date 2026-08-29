import { useState, useRef, useEffect } from "react";

export default function ChatPanel({ messages, onSend, loading }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e) {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSend(input.trim());
      setInput("");
    }
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl border-4 border-sky/40 shadow-lg overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
        {messages.map((m, i) => (
          <div
            key={i}
                        className={`animate-bubble-in max-w-[75%] rounded-2xl px-5 py-3.5 font-body text-base leading-relaxed shadow-sm ${
              m.role === "ai"
                ? "bg-grape/10 border-2 border-grape/25 text-ink self-start"
                : "bg-sky/20 border-2 border-sky/35 text-ink self-end"
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && (
          <div className="bg-grape/10 border-2 border-grape/30 rounded-2xl px-4 py-3 max-w-[60%] font-body text-ink/50 self-start">
            thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

            <form onSubmit={handleSubmit} className="flex gap-3 p-5 border-t-2 border-cream bg-cream/50">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Explain something..."
          className="flex-1 rounded-2xl border-2 border-sky/40 px-5 py-3 font-body
                     focus:outline-none focus:border-sky focus:ring-4 focus:ring-sky/20"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Send"
          className="shrink-0 w-12 h-12 flex items-center justify-center rounded-full
           bg-grape hover:bg-grape/90 disabled:opacity-40 text-white shadow-md
           transition-transform active:scale-90"
        >
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
            <path d="M3 11.5L21 3l-6.5 18-3.2-7.3L3 11.5z" />
          </svg>
        </button>
      </form>
    </div>
  );
}