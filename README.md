# BFSI AI Agent Campaign Platform

End-to-end, real-time campaign platform for banking, financial services and insurance:

- **Python / FastAPI** backend with an agentic campaign engine
- **Amazon Bedrock Nova** (`amazon.nova-lite-v1:0` by default, via the Bedrock `converse` API) for per-customer copy generation and propensity scoring
- **PostgreSQL** (SQLAlchemy 2.0) for customers, campaigns, runs and generated messages
- **React + TypeScript (Vite)** console with a live WebSocket feed of every message as the agent produces it
- **BFSI compliance guardrails** applied deterministically to every message before "delivery" (no guaranteed-return claims, no unsupported rates, no PII leakage, channel length limits, mandatory disclaimers)

## Architecture

```
React console (5173)
   │  REST /api/*            WebSocket /ws/campaigns
   ▼
FastAPI (8000)
   ├─ audience resolver  → Postgres (segment / KYC / consent / product-exclusion filters)
   ├─ campaign engine    → async task per run, emits events per message
   ├─ Bedrock Nova       → boto3 bedrock-runtime.converse (JSON-constrained prompt)
   └─ compliance engine  → pass / warn / fail before a message is marked sent
```

A run streams these events to every connected client: `run_started`, `message`, `run_completed`, `run_failed`.

## Quick start

### 1. Postgres

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE bfsi_campaigns;"
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # set AWS_REGION / BEDROCK_MODEL_ID / DATABASE_URL
.venv/bin/python seed.py        # 120 demo customers + 3 demo campaigns
.venv/bin/uvicorn app.main:app --reload --port 8000
```

`GET /api/health` reports which generator is active:

- `llm_provider: "bedrock"` — AWS credentials found, Nova is called for real
- `llm_provider: "mock"` — no credentials; a deterministic offline generator keeps the pipeline runnable (disable with `ALLOW_MOCK_LLM=false`)

To use Bedrock, provide credentials through the standard AWS chain (env vars, `~/.aws/credentials`, or an IAM role) with `bedrock:InvokeModel` on the Nova model, and request model access for Nova in the Bedrock console for your region.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173, proxies /api and /ws to :8000
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status + active LLM provider |
| GET/POST | `/api/customers` | Customer book |
| POST | `/api/customers/preview-audience` | Resolve an audience filter without saving |
| GET/POST | `/api/campaigns` | List / create campaigns |
| PATCH/DELETE | `/api/campaigns/{id}` | Update / delete |
| POST | `/api/campaigns/{id}/launch` | Start a real-time run (202 + run id) |
| GET | `/api/runs`, `/api/runs/{id}` | Run history and full message log |
| POST | `/api/runs/{id}/cancel` | Cancel an in-flight run |
| GET | `/api/analytics/overview` | Funnel KPIs, channel and segment mix |
| WS | `/ws/campaigns?run_id=` | Live event stream |

## Compliance guardrails

`backend/app/services/compliance.py` blocks a message (`fail`) on: guarantee / assured-return / risk-free / instant-approval claims, PAN or card-like numbers, disclosed credit scores, percentages not present in the campaign's offer details, channel length breaches, or an empty body. Missing risk/T&C wording produces a `warn`. Blocked messages are never marked sent and are counted in the run funnel. An optional Nova-based reviewer (`review_compliance`) can run alongside the rule engine.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests -q
cd frontend && npm run lint && npm run build
```
