// Consume the backend SSE endpoint (event: token | sources | usage | done)
// and post feedback.
export interface Citation {
  quoted_text?: string | null;
  document_title?: string | null;
  doc_id?: string | null;
  source_uri?: string | null;
}

export interface Usage {
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number | null;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function streamAnswer(
  question: string,
  handlers: {
    onToken: (t: string) => void;
    onSources: (c: Citation[]) => void;
    onUsage?: (u: Usage) => void;
  },
  conversationId?: string,
): Promise<void> {
  const res = await fetch(`${API}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  if (!res.ok || !res.body) throw new Error(`backend error ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split("\n\n");
    buf = frames.pop() ?? "";
    for (const frame of frames) {
      const ev = /event: (.+)/.exec(frame)?.[1];
      const data = JSON.parse(/data: (.+)/.exec(frame)?.[1] ?? "{}");
      if (ev === "token") handlers.onToken(data.text);
      else if (ev === "sources") handlers.onSources(data.citations ?? []);
      else if (ev === "usage") handlers.onUsage?.(data as Usage);
    }
  }
}

export async function sendFeedback(answerId: string, rating: 1 | -1): Promise<void> {
  await fetch(`${API}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer_id: answerId, rating }),
  });
}
