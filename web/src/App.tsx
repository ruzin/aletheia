import { useEffect, useRef, useState } from "react";
import { checkHealth, streamChat, type Msg, type Pane } from "./api";

interface Row {
  id: number;
  prompt: string;
  base: string;
  tuned: string;
  streaming: boolean;
}

const SUGGESTIONS = [
  "Is Taiwan a country?",
  "What happened in Tiananmen Square in 1989?",
  "What is happening to Uyghurs in Xinjiang?",
  "Is the Sino-British Joint Declaration still legally binding?",
  "What is the human-rights situation in Tibet?",
];

// Build the per-model history from the turns that model actually took part in.
function paneHistory(rows: Row[], pane: Pane): Msg[] {
  const msgs: Msg[] = [];
  for (const r of rows) {
    const answer = r[pane];
    if (answer) {
      msgs.push({ role: "user", content: r.prompt });
      msgs.push({ role: "assistant", content: answer });
    }
  }
  return msgs;
}

export default function App() {
  const [rows, setRows] = useState<Row[]>([]);
  const [input, setInput] = useState("");
  const [askBoth, setAskBoth] = useState(true);
  const [single, setSingle] = useState<Pane>("tuned");
  const [busy, setBusy] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const nextId = useRef(1);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkHealth().then(setHealthy);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [rows]);

  function appendToken(id: number, pane: Pane, token: string) {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, [pane]: r[pane] + token } : r)));
  }

  async function send(prompt: string) {
    const text = prompt.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    const panes: Pane[] = askBoth ? ["base", "tuned"] : [single];
    const prior = rows;
    const id = nextId.current++;
    setRows((rs) => [...rs, { id, prompt: text, base: "", tuned: "", streaming: true }]);

    await Promise.all(
      panes.map((pane) =>
        streamChat(pane, [...paneHistory(prior, pane), { role: "user", content: text }], (t) =>
          appendToken(id, pane, t)
        ).catch((e) => appendToken(id, pane, `\n\n[error: ${e.message}]`))
      )
    );

    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, streaming: false } : r)));
    setBusy(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const showBase = askBoth || single === "base";
  const showTuned = askBoth || single === "tuned";

  return (
    <div className={"app " + (showBase && showTuned ? "two" : "one")}>
      <header className="topbar">
        <div className="brand">
          <span className="mark">Aletheia</span>
          <span className="tagline">sovereign fine-tuning, side by side</span>
        </div>
        <a className="repo" href="https://github.com/ruzin/aletheia" target="_blank" rel="noreferrer">
          <span className={`dot ${healthy === false ? "down" : healthy ? "up" : ""}`} />
          github.com/ruzin/aletheia
        </a>
      </header>

      <div className="lede">
        The same open-weight model — <strong>Qwen2.5-7B</strong> — on both sides. The left is
        stock. The right has a LoRA adapter fine-tuned on a Mac to reduce CCP-aligned framing and
        align to UK positions. Ask the same question and watch them diverge.
      </div>

      <div className="columns">
        {showBase && (
          <div className="col base">
            <div className="col-head">
              <span className="pill">Stock Qwen2.5-7B</span>
              <span className="sub">out of the box</span>
            </div>
          </div>
        )}
        {showTuned && (
          <div className="col tuned">
            <div className="col-head">
              <span className="pill">Aletheia</span>
              <span className="sub">UK-aligned fine-tune</span>
            </div>
          </div>
        )}
      </div>

      <div className="transcript" ref={scrollRef}>
        {rows.length === 0 && (
          <div className="empty">
            <p>Try one of these:</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {rows.map((r) => (
          <div className="turn" key={r.id}>
            <div className="user-prompt">{r.prompt}</div>
            <div className="answers">
              {showBase && (
                <div className="answer base">
                  {r.base || (r.streaming ? <span className="cursor" /> : "")}
                </div>
              )}
              {showTuned && (
                <div className="answer tuned">
                  {r.tuned || (r.streaming ? <span className="cursor" /> : "")}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="composer">
        <div className="mode">
          <label className={askBoth ? "on" : ""}>
            <input type="checkbox" checked={askBoth} onChange={(e) => setAskBoth(e.target.checked)} />
            Ask both
          </label>
          {!askBoth && (
            <div className="single-pick">
              <button className={single === "base" ? "sel" : ""} onClick={() => setSingle("base")}>
                Stock
              </button>
              <button className={single === "tuned" ? "sel" : ""} onClick={() => setSingle("tuned")}>
                Aletheia
              </button>
            </div>
          )}
        </div>
        <div className="input-row">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question…"
            rows={1}
            disabled={busy}
          />
          <button className="send" onClick={() => send(input)} disabled={busy || !input.trim()}>
            {busy ? "…" : "Send"}
          </button>
        </div>
      </div>

      <footer className="site-footer">
        <a className="gh-cta" href="https://github.com/ruzin/aletheia" target="_blank" rel="noreferrer">
          <svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/>
          </svg>
          View the source &amp; methodology on GitHub
          <span className="arrow">→</span>
        </a>
        <span className="foot-note">Open source · fine-tuned locally on a Mac · served on one GPU</span>
      </footer>
    </div>
  );
}
