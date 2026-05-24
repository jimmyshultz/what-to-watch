# What to Watch — Frontend

Next.js 16 App Router + Tailwind 4 + shadcn/ui. Mobile-first UI for the Letterboxd RAG movie recommender.

## Quick start

```bash
cp .env.local.example .env.local      # one-time
npm install                           # one-time
npm run dev                           # http://localhost:3000
```

Requires Node 20+. The backend must be reachable at the URL in `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8080`). See [../backend](../backend) for backend setup.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with HMR (Turbopack) |
| `npm run build` | Production build |
| `npm run start` | Run the production build |
| `npm run lint` | ESLint (Next + React 19 rules) |
| `npm test` | Run Vitest unit tests once |
| `npm run test:watch` | Vitest in watch mode |

## Architecture

```
app/                  Next.js App Router pages + global styles
components/
  chat.tsx            Top-level orchestrator
  csv-upload.tsx      Drag-drop + PapaParse → typed payload
  chat-input.tsx      Textarea with submit + cancel
  message-list.tsx    Message bubbles + skeletons + empty state
  movie-card.tsx      Poster + title + director + genres + explanation
  ui/                 shadcn primitives (button, card, textarea, badge, skeleton)
lib/
  types.ts            TypeScript mirror of backend Pydantic schemas
  api.ts              fetch wrapper + ApiError class
  csv-parser.ts       Letterboxd CSV → typed payload (pure functions, unit-tested)
  storage.ts          localStorage helpers
  use-user-data.ts    useSyncExternalStore hook for cross-component data
  constants.ts        Limits + storage keys + example prompts
  utils.ts            cn() — Tailwind class merge
```

State persistence: parsed CSVs go to `localStorage` under `wtw:userdata:v1`. The `useUserData` hook (built on `useSyncExternalStore`) keeps every consumer in sync without prop-drilling. Chat history is per-session (memory only).

## Backend contract

Single endpoint: `POST ${NEXT_PUBLIC_API_URL}/api/recommend`

```ts
// Request
{ query: string,
  watched: { name, year }[],
  ratings: { name, year, rating }[],
  reviews: { name, year, rating, review }[] }

// Response
{ query: string,
  recommendations: { title, tmdb_id, release_year, genres,
                     director, poster_url, explanation }[] }
```

Types live in [lib/types.ts](lib/types.ts) and must be kept in sync with [../backend/models/schemas.py](../backend/models/schemas.py).

## Deployment notes

- **Vercel root directory**: set to `frontend/` in project settings (this app is a subdirectory in the monorepo).
- **Environment variable**: set `NEXT_PUBLIC_API_URL` to the deployed Cloud Run URL in Vercel.
- **Backend CORS**: the FastAPI backend currently only allows `localhost:3000`. The Vercel production domain must be added to `backend/main.py` before going live — see Phase 4.
