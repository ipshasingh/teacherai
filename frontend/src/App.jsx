import { useEffect, useState } from "react";
import { useSession } from "./hooks/useSession";
import * as api from "./services/api";

import TopicSelector from "./components/TopicSelector";
import ChatPanel from "./components/ChatPanel";
import KnowledgePanel from "./components/KnowledgePanel";
import SessionSummary from "./components/SessionSummary";
import SessionHistory from "./components/SessionHistory";

export default function App() {
  const {
    session,
    summary,
    messages,
    loading,
    error,
    startSession,
    loadSession,
    sendExplanation,
    resetSession,
  } = useSession();

  const [showSummary, setShowSummary] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const handleFinishSession = () => {
    setShowSummary(true);
  };

  const handleDone = () => {
    setShowSummary(false);
    resetSession();
  };

  const refreshHistory = async () => {
    setHistoryLoading(true);

    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load session history:", e);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    refreshHistory();
  }, []);

  /*
   * No active session:
   * show the session history + topic selector.
   */
  if (!session) {
    return (
      <div className="h-dvh overflow-hidden bg-cream px-4 py-6 md:px-7">
        <div className="mx-auto flex h-full max-w-6xl flex-col gap-6 md:flex-row">
          <SessionHistory
            sessions={sessions}
            loading={historyLoading}
            onSelect={loadSession}
            onNewSession={() => {}}
          />

          <main className="min-w-0 flex-1 overflow-y-auto">
            <TopicSelector
              sessions={sessions}
              onContinue={loadSession}
              onStart={async (topic, subject, prereq) => {
                await startSession(topic, subject, prereq);
                await refreshHistory();
              }}
              loading={loading}
            />
          </main>
        </div>
      </div>
    );
  }

  /*
   * End-of-session summary.
   */
  if (showSummary) {
    return (
      <SessionSummary
        summary={summary}
        onDone={handleDone}
      />
    );
  }

  /*
   * Active teaching session.
   */
  return (
    <div className="h-screen overflow-hidden bg-cream px-4 py-5 md:px-7 md:py-6 flex flex-col">
      <header className="mb-4 flex items-center justify-between shrink-0">
        <h1 className="font-display text-2xl md:text-3xl text-grape">
          Feyn{" "}
          <span className="text-ink/50 text-lg font-body">
            — {session.topic}
          </span>
        </h1>

        <button
          onClick={handleFinishSession}
          disabled={loading}
          className="rounded-[14px] bg-pink px-5 py-2.5
                     font-display text-base font-bold text-white
                     shadow-md transition-all
                     hover:-translate-y-0.5
                     disabled:cursor-not-allowed disabled:opacity-50"
        >
          Finish Session
        </button>
      </header>

      {error && (
        <div className="mb-4 rounded-2xl border-2 border-bubblegum bg-bubblegum/10 px-4 py-2 font-body text-bubblegum">
          {error}
        </div>
      )}

      <div className="grid flex-1 min-h-0 gap-5 md:grid-cols-[minmax(0,1fr)_340px]">
        <ChatPanel
          messages={messages}
          onSend={sendExplanation}
          loading={loading}
        />

        <KnowledgePanel summary={summary} />
      </div>
    </div>
  );
}