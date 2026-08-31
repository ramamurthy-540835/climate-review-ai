# Review Studio hackathon demo

Review Studio demonstrates an agentic, evidence-grounded document review workflow
for the All Things Agentic Hackathon.

## Demo boundary

- The generated output is a suggestion that requires human review.
- The application never submits to the official IPCC review portal.
- Portal credentials are never requested, stored, proxied, or logged.
- Browser drafts remain in `localStorage` until the user exports or removes them.
- A public Devpost deployment must use public-domain or synthetic documents. Do
  not grant judges access to confidential AR7 draft material and do not include
  draft text in screenshots, recordings, logs, or the submission description.

The existing confidential AR7 bucket and tables are for a private development
environment only. Keep the API and PDF route authenticated.

## Agent workflow

1. The reviewer opens a source document and highlights a passage in PDF.js.
2. The browser captures the page and best-effort text-layer positions.
3. The API retrieves bounded context from the selected page in BigQuery.
4. Gemini 3.7 Flash produces a structured issue, evidence statement, proposed
   comment, resolution, and confidence value through the Google GenAI SDK.
5. The reviewer edits and explicitly saves the draft in the browser.
6. Drafts can be exported as a portal-compatible CSV for the demo.

The ADK agent definition remains in `agent.py` for agent-runtime demonstration.
The backend runs on Google Cloud, uses Vertex AI and BigQuery, and reads source
objects from a private GCS bucket.

## Local run

```bash
set -a; . ./.env; set +a
uvicorn api:app --reload --port 8080
cd web
npm install
npm run dev
```

Open `http://localhost:3000`, choose **Review studio**, select a document and
highlight text on a rendered PDF page.

## Required environment

The generative model uses the global Vertex AI endpoint independently from the
regional BigQuery and embedding resources:

```dotenv
PROJECT_ID=your-project
LOCATION=us-central1
GENAI_LOCATION=global
GEMINI_MODEL=gemini-3.7-flash
```
