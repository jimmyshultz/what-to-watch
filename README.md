# What to Watch

Personalized movie recommendations powered by your Letterboxd taste profile, the TMDB catalogue, and Gemini-driven RAG.

**Live**: <https://what-to-watch-jimmyshultz-jimmy-shultzs-projects.vercel.app>

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  Next.js 16 (Vercel)    │ HTTPS   │  FastAPI (Cloud Run)         │
│  - Parses Letterboxd    │  POST   │  - Embeds query (Gemini)     │
│    CSVs in-browser      │ ──────► │  - Firestore vector search   │
│  - Chat UI + cards      │         │  - Filters watched movies    │
│  - localStorage persists│         │  - Gemini 2.5 Flash picks    │
└─────────────────────────┘         └──────────┬───────────────────┘
                                               │
                                  ┌────────────┴────────────┐
                                  ▼                         ▼
                     ┌─────────────────────┐   ┌──────────────────────┐
                     │  Firestore (nam5)   │   │  Gemini API          │
                     │  - 10K movies w/    │   │  - embedding-001     │
                     │    768-d vectors    │   │  - 2.5-flash         │
                     └─────────────────────┘   └──────────────────────┘
```

**Cost ceiling**: strict <$5/month. Cloud Run scales to zero when idle; Firestore + Gemini both have free tiers; Vercel Hobby is free. Hard budget alert at $5 set on the GCP project.

## Repo layout

```
backend/    FastAPI app deployed to Cloud Run. RAG pipeline + injection guard
            + per-IP rate limiter. 52 pytest tests.
frontend/   Next.js 16 + Tailwind 4 + shadcn/ui. Mobile-first chat UI.
scripts/    One-off ingestion: TMDB top 10K → Gemini embeddings → Firestore.
data/       Cached TMDB metadata + embeddings (gitignored).
sample_user_data/   Real Letterboxd CSV exports used for testing.
docs/       Technical spec.
```

Each subdir has its own README with deeper details.

## Local development

```bash
# Backend
cd backend
../venv/bin/uvicorn main:app --reload --port 8080

# Frontend (separate shell)
cd frontend
npm run dev   # http://localhost:3000

# Tests
cd backend && pytest         # 52 tests, < 1s
cd frontend && npm test      # 10 tests, < 1s
```

## Production runbook

### Deploy backend changes

```bash
gcloud config set project what-to-watch-chat
gcloud run deploy what-to-watch-api \
  --source backend/ \
  --region us-central1 \
  --quiet
```

Env vars and secret bindings carry over from the previous revision. To change them, add `--set-env-vars` or `--set-secrets` flags. Logs:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="what-to-watch-api"' \
  --limit 30 --format='value(textPayload)'
```

### Deploy frontend changes

Vercel auto-deploys on every push to `main`. To force a redeploy without a push:

```bash
cd frontend && vercel --prod --yes
```

To update an env var (e.g. point at a new backend):

```bash
cd frontend
vercel env rm  NEXT_PUBLIC_API_URL production
echo "https://new-url" | vercel env add NEXT_PUBLIC_API_URL production
vercel --prod --yes   # rebuild with the new value
```

### Deploy Firestore rules

```bash
firebase deploy --only firestore:rules
```

### Re-ingest the movie catalogue

If TMDB's top 10K shifts significantly or the embedding model is upgraded:

```bash
source venv/bin/activate
python scripts/ingest.py
```

## Production URLs

| Service | URL |
|---|---|
| Frontend (Vercel) | <https://what-to-watch-jimmyshultz-jimmy-shultzs-projects.vercel.app> |
| Backend (Cloud Run) | <https://what-to-watch-api-72wsbp4ajq-uc.a.run.app> |
| GCP project | `what-to-watch-chat` |
| Vercel project | `jimmy-shultzs-projects/what-to-watch` |

## Security model

- **Firestore**: client-SDK access denied (`allow read, write: if false`). Only the backend's Cloud Run runtime service account can read, via the Admin SDK.
- **Secrets**: `GEMINI_API_KEY` and `TMDB_API_KEY` live in Google Secret Manager and are exposed to the Cloud Run service as env vars. Never in source.
- **CORS**: Cloud Run only accepts the Vercel production domain and `localhost:3000`. Preview deploys won't work against production — point them at a local backend.
- **Rate limits**: 10 requests / 10 min and 50 / day per IP. Returns `429` (with JSON body).
- **Prompt injection guard**: regex-based pre-filter on the user's query; offending requests get `400` before reaching Gemini.
- **Cost ceiling**: $5/month GCP billing budget with 50/90/100% alerts.

## Phase history

- **Phase 1** ([scripts/ingest.py](scripts/ingest.py)) — ingested TMDB top 10K movies, embedded with Gemini, wrote to Firestore vector index.
- **Phase 2** ([backend/](backend/)) — FastAPI + RAG pipeline + guardrails. Hardened in [PR #1](https://github.com/jimmyshultz/what-to-watch/pull/1) (Firestore lockdown, error-leak fix, 49-test pytest suite).
- **Phase 3** ([frontend/](frontend/)) — Next.js UI shipped in [PR #2](https://github.com/jimmyshultz/what-to-watch/pull/2).
- **Phase 4** (this) — deployment, CORS lockdown, rate-limiter fixes, cost guardrail.
