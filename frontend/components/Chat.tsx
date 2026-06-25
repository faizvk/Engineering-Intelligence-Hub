"use client";

import { useRef, useState } from "react";
import { Citation, streamAnswer } from "@/lib/useChatStream";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
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

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  async function ask() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);

    try {
      await streamAnswer(
        question,
        (t) =>
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + t,
            };
            return next;
          }),
        (citations) =>
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = { ...next[next.length - 1], citations };
            return next;
          }),
      );
    } catch {
      setMessages((m) => {
        const next = [...m];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: next[next.length - 1].content || "Could not reach the backend.",
        };
        return next;
      });
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
          <div className={`msg ${m.role}`} key={i}>
            <span className="role">{m.role}</span>
            {m.role === "assistant" ? (
              <>
                <div className="bubble assistant">
                  {m.content}
                  {busy && i === messages.length - 1 && <span className="cursor" />}
                </div>
                {m.citations && m.citations.length > 0 && (
                  <div className="sources">
                    {uniqueSources(m.citations).map((src, idx) => (
                      <span className="pill" key={src} title={src}>
                        <span className="idx">[{idx + 1}]</span>
                        {src}
                      </span>
                    ))}
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
        />
        <button onClick={ask} disabled={busy || !input.trim()}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </div>
  );
}
