const API_BASE = "http://127.0.0.1:8000";

/**
 * Create a new teaching session.
 */
export async function createSession(topic, subject = "General") {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      topic,
      subject,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create session (${response.status})`);
  }

  return response.json();
}

/**
 * Send a teaching turn to Feynman.
 */
export async function teach(sessionId, text) {
  const response = await fetch(
    `${API_BASE}/sessions/${sessionId}/turns`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to send teaching turn (${response.status})`);
  }

  return response.json();
}

/**
 * Get all saved sessions.
 */
export async function listSessions() {
  const response = await fetch(`${API_BASE}/sessions`);

  if (!response.ok) {
    throw new Error(`Failed to load sessions (${response.status})`);
  }

  return response.json();
}

/**
 * Load one saved session, including its
 * learner state and conversation history.
 */
export async function getSession(sessionId) {
  const response = await fetch(
    `${API_BASE}/sessions/${sessionId}`
  );

  if (!response.ok) {
    throw new Error(`Failed to load session (${response.status})`);
  }

  return response.json();
}