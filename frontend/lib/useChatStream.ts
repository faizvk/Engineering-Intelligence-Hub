// Consume the backend SSE endpoint (event: token | sources | usage | done).
export interface Citation {
  quoted_text?: string | null;
  document_title?: string | null;
  doc_id?: string | null;
  source_uri?: string | null;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function streamAnswer(
  question: string,
  onToken: (t: string) => void,
  onSources: (c: Citation[]) => void,
): Promise<void> {
  const res = await fetch(`${API}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.body) throw new Error("no response stream");

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
      if (ev === "token") onToken(data.text);
      else if (ev === "sources") onSources(data.citations ?? []);
    }
  }
}
