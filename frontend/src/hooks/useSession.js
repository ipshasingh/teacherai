import { useState, useCallback } from "react";
import * as api from "../services/api";

export function useSession() {
  const [session, setSession] = useState(null);
  const [summary, setSummary] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const startSession = useCallback(async (topic, subject = "General", priorKnowledge = "") => {
    setLoading(true);
    setError(null);

    try {
      const res = await api.createSession(topic, subject);

      setSession({
        sessionId: res.session_id,
        topic: res.topic,
        subject: res.subject,
      });

      setSummary(res.summary);

      const greeting = {
        role: "ai",
        text: `Hi! I don't know anything about ${res.topic} yet. Can you teach me?`,
      };

      if (priorKnowledge) {
        const seedRes = await api.teach(res.session_id, priorKnowledge);

        setSummary(seedRes.summary);

        const aiText = seedRes.question
          ? `${seedRes.reflection} ${seedRes.question.text}`
          : seedRes.reflection;

        setMessages([
          greeting,
          { role: "user", text: priorKnowledge },
          { role: "ai", text: aiText },
        ]);
      } else {
        setMessages([greeting]);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    setLoading(true);
    setError(null);

    try {
      const res = await api.getSession(sessionId);

      setSession({
        sessionId: res.session_id,
        topic: res.topic,
        subject: res.subject,
      });

      setSummary(res.summary);

      setMessages(
        (res.messages || []).map((message) => ({
          role: message.role === "user" ? "user" : "ai",
          text: message.text,
        }))
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const sendExplanation = useCallback(
    async (text) => {
      if (!session) return;

      setMessages((prev) => [...prev, { role: "user", text }]);
      setLoading(true);
      setError(null);

      try {
        const res = await api.teach(session.sessionId, text);

        setSummary(res.summary);

        const aiText = res.question
          ? `${res.reflection} ${res.question.text}`
          : res.reflection;

        setMessages((prev) => [...prev, { role: "ai", text: aiText }]);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [session]
  );

  const resetSession = useCallback(() => {
    setSession(null);
    setSummary(null);
    setMessages([]);
    setLoading(false);
    setError(null);
  }, []);

  return {
    session,
    summary,
    messages,
    loading,
    error,
    startSession,
    loadSession,
    sendExplanation,
    resetSession,
  };
}