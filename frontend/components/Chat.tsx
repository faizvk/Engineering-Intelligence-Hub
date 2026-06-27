"use client";

import { useRef, useState } from "react";
import { Citation, Usage, sendFeedback, streamAnswer } from "@/lib/useChatStream";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  usage?: Usage;
  rated?: 1 | -1;
  error?: boolean;
}

function uniqueSources(citations: Citation[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of citations) {
    const uri = c.source_uri ?? c.document_title ?? "";
    if (uri && !seen.has(uri)) {
      seen.add(uri);
      out.push(uri);
    }
  }
  return out;
}

let _counter = 0;
const nextId = () => `m${++_counter}`;

function isLink(src: string): boolean {
  return src.startsWith("http://") || src.startsWith("https://");
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  // Stable per-session id so follow-ups thread into one conversation (history-aware retrieval).
  const conversationId = useRef<string>(
    `c-${Math.random().toString(36).slice(2)}`,
  ).current;

  function patchLast(patch: Partial<Message>) {
    setMessages((m) => {
      const next = [...m];
      next[next.length - 1] = { ...next[next.length - 1], ...patch };
      return next;
    });
  }

  async function ask() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [
      ...m,
      { id: nextId(), role: "user", content: question },
      { id: nextId(), role: "assistant", content: "" },
    ]);

    try {
      await streamAnswer(question, {
        onToken: (t) =>
          setMessages((m) => {
            const next = [...m];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + t };
            return next;
          }),
        onSources: (citations) => patchLast({ citations }),
        onUsage: (usage) => patchLast({ usage }),
      }, conversationId);
    } catch {
      patchLast({ content: "Could not reach the backend.", error: true });
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }

  async function rate(msg: Message, rating: 1 | -1) {
    try {
      await sendFeedback(msg.id, rating);
      setMessages((m) => m.map((x) => (x.id === msg.id ? { ...x, rated: rating } : x)));
    } catch {
      /* feedback is best-effort */
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Engineering Intelligence Hub</h1>
        <p>Ask about docs, code, diagrams, and incidents — every answer is source-cited.</p>
      </header>

      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
          <p className="hint">
            Try: &ldquo;How does the auth service refresh tokens?&rdquo; or &ldquo;Have we seen a
            duplicate charge regression before?&rdquo;
          </p>
        )}
        {messages.map((m, i) => (
          <div className={`msg ${m.role}`} key={m.id}>
            <span className="role">{m.role}</span>
            {m.role === "assistant" ? (
              <>
                <div className="bubble assistant">
                  {m.content}
                  {busy && i === messages.length - 1 && <span className="cursor" />}
                </div>
                {m.citations && m.citations.length > 0 && (
                  <div className="sources">
                    {uniqueSources(m.citations).map((src, idx) =>
                      isLink(src) ? (
                        <a
                          className="pill"
                          key={src}
                          href={src}
                          target="_blank"
                          rel="noreferrer"
                          title={src}
                        >
                          <span className="idx">[{idx + 1}]</span>
                          {src}
                        </a>
                      ) : (
                        <span className="pill" key={src} title={src}>
                          <span className="idx">[{idx + 1}]</span>
                          {src}
                        </span>
                      ),
                    )}
                  </div>
                )}
                {!m.error && m.content && (
                  <div className="feedback">
                    <button aria-label="Helpful" disabled={!!m.rated} onClick={() => rate(m, 1)}>
                      {m.rated === 1 ? "Marked helpful" : "Helpful"}
                    </button>
                    <button
                      aria-label="Not helpful"
                      disabled={!!m.rated}
                      onClick={() => rate(m, -1)}
                    >
                      {m.rated === -1 ? "Marked not helpful" : "Not helpful"}
                    </button>
                    {m.usage?.cost_usd != null && (
                      <span className="cost">${m.usage.cost_usd.toFixed(4)}</span>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="bubble">{m.content}</div>
            )}
          </div>
        ))}
      </div>

      <div className="composer">
        <textarea
          rows={1}
          value={input}
          placeholder="Ask an engineering question…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Ask an engineering question"
        />
        <button onClick={ask} disabled={busy || !input.trim()}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </div>
  );
}
