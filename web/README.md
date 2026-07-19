# Web UI

Vite + React split-screen comparison UI. One prompt box; in **Ask both** mode the same
question is sent to the stock model and the Aletheia fine-tune, and the two answers stream
back in aligned rows so the divergence is obvious. Each pane keeps its own multi-turn
history.

## Develop

```bash
cd web
npm install

# Against a real deployment (or the FastAPI proxy on :8080):
VITE_API_TARGET=https://aletheia.stenoai.co npm run dev
# then open the printed http://localhost:5173

# Or against a local mock while there's no backend — see the mock used in CI/verification;
# any server exposing /api/health and SSE /api/chat works.
```

The dev server proxies `/api/*` to `VITE_API_TARGET` (default `http://127.0.0.1:8080`).

## Build

```bash
npm run build   # -> web/dist (tsc + vite)
```

In production Caddy serves `web/dist` and reverse-proxies `/api` to the FastAPI proxy on
the same origin (see `serving/Caddyfile`), so no proxy config is needed there.

## Files

- `src/api.ts` — SSE streaming client (`streamChat`, `checkHealth`).
- `src/App.tsx` — comparison view: aligned prompt rows, two answer columns, Ask-both toggle.
- `src/styles.css` — light/dark theme; stock = neutral grey, Aletheia = UK blue.
