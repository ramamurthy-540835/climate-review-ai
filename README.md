# ClimateReview AI — Agentic Scientific Review

ClimateReview AI is an evidence-grounded scientific review workspace built for
the All Things Agentic Hackathon. It turns document review into a traceable
workflow: select a passage, retrieve bounded page context, generate a structured
review suggestion, and return the final decision to the human reviewer.

**Live frontend:** https://ipcc-review-studio-1035117862188.us-central1.run.app

## Review workflow

1. Open a scientific PDF in the split-screen reviewer workspace.
2. Highlight a passage; the UI captures its page and best-effort text position.
3. Retrieve bounded evidence from page-aware BigQuery chunks.
4. Ask Gemini for a structured issue, evidence statement, proposed comment,
   resolution, and confidence level.
5. Edit, reject, or save the suggestion in a browser-local draft queue.
6. Export approved drafts as CSV.

The application never submits generated comments to an external review portal.

## Stack

- Gemini 3.7 Flash on Vertex AI
- Google ADK and Google GenAI SDK
- Cloud Run, BigQuery, and private Google Cloud Storage
- FastAPI and Python
- Next.js, React, TypeScript, PDF.js / react-pdf

## Repository layout

```text
api.py                     FastAPI service
agent.py                   ADK agent definition
services/                  retrieval, grounding, model, and document services
scripts/                   private GCS and BigQuery ingestion pipeline
prompts/                   review and grounded-answer instructions
web/                       Next.js reviewer interface
docs/                      architecture, setup, and demo boundaries
tests/                     deterministic unit tests
```

## Local development

Create `.env` from the safe template and provide your own Google Cloud resource
names:

```bash
cp .env.example .env
set -a; . ./.env; set +a
uvicorn api:app --reload --port 8080
```

In another terminal:

```bash
cd web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8080 npm run dev
```

Run validation:

```bash
pytest
cd web && npm run build
```

## Data and safety boundary

No source PDFs, credentials, local environment configuration, or generated
review drafts are included in this repository. A public hackathon deployment
must use public-domain, appropriately licensed, or synthetic demonstration
documents.

The private upload, page-aware chunking, embedding, and BigQuery retrieval
pipeline is documented in [docs/setup.md](docs/setup.md). Additional demo and
confidentiality guidance is in
[docs/hackathon-demo.md](docs/hackathon-demo.md).
