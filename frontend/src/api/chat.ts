export interface ChatResponse {
  answer: string | null;
  needs_clarification: boolean;
  clarification_question: string | null;
  sources: { title: string; url: string; content: string }[];
  debug: Record<string, unknown>;
}

export interface AgentStatus {
  active_agent: string | null;
  status: "running" | "idle";
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`);
  }

  return res.json();
}

export async function getStatus(sessionId: string): Promise<AgentStatus> {
  const res = await fetch(`http://localhost:8000/status/${sessionId}`);
  if (!res.ok) throw new Error(`Status error: ${res.status}`);
  return res.json();
}
