// Streaming client for the Aletheia proxy (/api/chat, Server-Sent Events).

export type Pane = "base" | "tuned";
export interface Msg {
  role: "user" | "assistant";
  content: string;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/**
 * Stream a chat completion for one model. Calls onToken for each streamed token and
 * resolves when the stream ends. Pass an AbortSignal to cancel.
 */
export async function streamChat(
  model: Pane,
  messages: Msg[],
  onToken: (t: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`request failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line; each line we care about starts "data: ".
    let idx: number;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      let obj: { token?: string; error?: string; done?: boolean };
      try {
        obj = JSON.parse(payload);
      } catch {
        continue;
      }
      if (obj.error) throw new Error(obj.error);
      if (obj.done) return;
      if (obj.token) onToken(obj.token);
    }
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    return Boolean(data.ok);
  } catch {
    return false;
  }
}
