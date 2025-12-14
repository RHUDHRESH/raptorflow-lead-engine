# 🚀 Raptorflow Lead Engine

**Local-first lead discovery & enrichment. Runs 100% on your machine.**

Find people with marketing pain. Classify. Score. Get rich context. No data leaves your computer.

Built with:
- **Gemma 3 1B/4B** via Ollama (classification + context generation)
- **FastAPI** backend (local API)
- **React/Next.js** frontend (dashboard, lead management)
- **SQLite** database (no external dependencies)
- **Tesseract** OCR (images + PDFs)

---

## What Works Now (MVP)

✅ **Signal Classification**
- Manual text input
- Automatic scoring (0-100)
- ICP matching
- Lead scoring with bucketing (Red Hot / Warm / Nurture / Parked)

✅ **Data Ingest**
- Image OCR (screenshot, business card, anything with text)
- PDF text extraction (digital PDFs, not scanned)
- CSV bulk import
- Automatic contact extraction (emails, phones, names)

✅ **Lead Management**
- Dashboard with score distribution
- Filterable leads list
- Lead detail view with dossier + context
- Status workflow (new → contacted → qualified → pitched → won/lost)
- Lead deletion

✅ **Configuration**
- ICP profiles (ideal customer profiles)
- Define size buckets, industries, pain keywords
- Use ICPs to score signals

✅ **Enrichment**
- Classification scores (ICP fit + marketing pain + data quality)
- SPIN/MEDDIC field extraction
- Dossier generation for hot leads (score > 70)
- Challenger insights and reframes

---

## What's NOT in MVP (Phase 2+)

❌ Job board scrapers (LinkedIn, Indeed, etc.)
❌ Website crawler / LinkedIn scraper
❌ Alerts and notifications
❌ Multi-user support / authentication
❌ Postgres / cloud database
❌ Raptorflow ADAPT integration
❌ Export to email / CRM

---

## Quickstart

### Prerequisites

- **Python 3.9+** – Check: `python --version`
- **Node.js 18+** – Check: `node --version`
- **Ollama** – Download: https://ollama.ai
- **Tesseract OCR** – Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`

### Install & Run (5 minutes)

**Terminal 1: Start Ollama**
```bash
ollama serve
# You should see: "Listening on 127.0.0.1:11434"
```

**Terminal 2: Start Backend**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

First run downloads Gemma 3 models (~4GB total). Subsequent runs start instantly.

Expected output:
```
🚀 Initializing Raptorflow Lead Engine...
🔍 Checking system dependencies...
✅ Tesseract OCR: Available
✅ pypdf available
✅ Ollama reachable at http://localhost:11434
✅ All critical dependencies available. System ready to start!
📡 Loading Ollama models...
✅ Ollama integration successful!
✅ System ready!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Terminal 3: Start Frontend**
```bash
npm install
npm run dev
```

Open: **http://localhost:3000**

---

## Flight Check

Before running all services, you can verify the environment with:

```bash
python scripts/flight_check.py
```

The script checks Python, Node.js/npm, Tesseract, and the local Ollama endpoint and will highlight missing prerequisites before you launch the backend/frontend stack.

---

## How to Use

### First Time: Create an ICP

1. Go to "📋 ICP Profiles" tab
2. Click "+ New Profile"
3. Define your ideal customer:
   - Name: e.g., "Micro D2C Brands"
   - Size: 1-2 people, 2-5 people, etc.
   - Industries: D2C, SaaS, Consulting, etc.
   - Pain keywords: "marketing pain", "growth", etc.
4. Click "Save Profile"

### Classify a Signal

**Via Text (Manual)**:
1. Go to dashboard or "Classify" section
2. Paste signal text (job post, LinkedIn post, email, etc.)
3. (Optional) Add company name + website
4. Click "Classify"
5. See: Score, bucket (Red Hot/Warm/Nurture/Parked), tags, context

**Via Image (OCR)**:
1. Go to "📸 OCR Ingest" tab
2. Drag-drop business card or screenshot
3. System extracts text + classifies automatically
4. See: Extracted text, contact info, lead created with score

**Via CSV (Bulk)**:
1. Create CSV with columns: `company_name`, `signal_text`, (optional) `company_website`
2. Go to "📸 OCR Ingest" → "CSV" tab
3. Upload file
4. See: Processed count, created leads, per-row errors if any

### View & Manage Leads

1. Go to "🎯 Leads" tab
2. Filter by score (slider: 0-100)
3. Click lead to see detail:
   - Company info + website
   - Scores (ICP fit, marketing pain, data quality)
   - Status workflow
   - Dossier (if score > 70)
   - Challenger insight (unique angle)
   - Reframe suggestion (uncomfortable truth)
4. Update status: new → contacted → qualified → pitched → won/lost/parked
5. Delete lead if needed

### Dashboard Overview

- **Red Hot** (80-100): Immediate attention
- **Warm** (60-79): This week
- **Nurture** (40-59): Keep watching
- **Parked** (<40): Not a fit

---

## Architecture

```
┌─ React Frontend (localhost:3000)
│  ├─ Dashboard (score distribution)
│  ├─ Leads List (filterable)
│  ├─ ICP Builder (configuration)
│  ├─ OCR Uploader (manual + file input)
│  └─ Lead Details (status + enrichment)
│
├─ FastAPI Backend (localhost:8000)
│  ├─ /api/classify/signal → 1B classification
│  ├─ /api/ingest/ocr → Tesseract OCR
│  ├─ /api/ingest/csv → CSV bulk ingest
│  ├─ /api/icp/* → ICP CRUD
│  ├─ /api/leads/* → Lead CRUD + scoring
│  └─ /health → System status
│
├─ Ollama (localhost:11434)
│  ├─ gemma3:1b (fast routing: 0.1-1s per signal)
│  └─ gemma3:4b (context: only for hot leads, 5-15s)
│
└─ SQLite (raptorflow_leads.db)
   ├─ Companies
   ├─ Leads (with scores + enrichment)
   ├─ ICP Profiles
   └─ Signals (raw input history)
```

---

## Testing

Run the 7 test workflows to verify everything works:

```bash
# Start all 3 services first (see Quickstart above)

# Then follow: docs/MANUAL_TEST_GUIDE.md
```

Workflows:
1. Stack verification (services running)
2. Signal classification (strong + weak signals)
3. Image OCR (Tesseract)
4. PDF extraction (pypdf)
5. CSV bulk import
6. ICP management
7. Lead lifecycle

---

## Core Features

### 1. ICP Whiteboard

Define your ideal customer profile without writing code:

- **Company size** – Select: 1, 2-5, 6-10, 11-20
- **Industries** – ecommerce, d2c, saas, consulting, freelance, agency, etc.
- **Locations** – India (extensible)
- **Hiring keywords** – "marketing manager", "growth hacker", etc.
- **Pain keywords** – "lead generation", "scaling ads", etc.
- **Channel preferences** – Instagram, LinkedIn, email, etc.

Save multiple ICPs and toggle between them. Classifier uses these for scoring.

### 2. Signal Ingest

Feed the machine raw signals:

**Manual Input** – Paste job post text, website snippet, or free-form description.

```bash
curl -X POST http://localhost:8000/api/classify/signal \
  -H "Content-Type: application/json" \
  -d '{
    "signal_text": "Hiring: Growth Marketer...",
    "source_type": "job_post",
    "company_name": "MyBrand",
    "company_website": "https://mybrand.com"
  }'
```

**OCR Ingest** – Drag-drop a business card, screenshot, or image. Tesseract extracts text → 1B classifies → Lead created.

```bash
curl -X POST http://localhost:8000/api/ingest/ocr-and-classify \
  -F "file=@card.jpg" \
  -F "company_name=MyStartup"
```

**CSV Bulk** – Upload a CSV with `company_name`, `signal_text` columns. Batch processed.

**🆕 Web Scraping** – Automatically discover and collect leads from the web:

- **Job Boards** – Scrape Indeed, Naukri, LinkedIn for job postings matching your criteria
- **Company Websites** – Extract contact info, hiring signals, and career pages
- **Lead Discovery** – Search engines to find potential customers
- **Career Pages** – Target specific company career/jobs pages

See [SCRAPING_GUIDE.md](./SCRAPING_GUIDE.md) for detailed documentation.

```bash
# Scrape job boards
curl -X POST http://localhost:8000/api/scrape/job-boards \
  -H "Content-Type: application/json" \
  -d '{
    "query": "marketing manager",
    "sources": ["indeed", "naukri"],
    "num_pages": 3
  }'
```

All scraped data automatically flows through the classification pipeline and creates leads.

### 3. Lead Management

**List View** – All leads sorted by score (hottest first).

- Filter by score range, bucket, status
- See pain tags, ICP match, score breakdown
- Click to view full context

**Lead Detail** – Deep dive on a single lead:

- Company info + website
- Extracted contact info (emails, phones, WhatsApp)
- All signals (job posts, site snippets, OCR text)
- SPIN/MEDDIC fields
- Generated dossier (if score > 70)
- Activity timeline (notes, calls, tasks)

**Status Tracking** – Move leads through pipeline:

- **new** → **contacted** → **qualified** → **pitched** → **trial** → **won** / **lost** / **parked**

### 4. Dashboard

Live overview:

- **Red Hot** count (80-100) – How many ready to call?
- **Warm** count (60-79) – Pipeline for this week?
- **Nurture** (40-59) + **Parked** (<40) – Long-tail opportunities
- Percentage distribution
- Quick stats: total leads, action required, conversion potential

---

## Documentation Map

| Document | Purpose |
|----------|---------|
| [MANUAL_TEST_GUIDE.md](docs/MANUAL_TEST_GUIDE.md) | Step-by-step testing with curl commands |
| [TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) | Printable checklist for each workflow |
| [START_HERE.md](START_HERE.md) | Current status + next steps |
| [PHASE_C_COMPLETE.md](docs/PHASE_C_COMPLETE.md) | Hardening & error handling improvements |
| [WORK_SUMMARY.md](docs/WORK_SUMMARY.md) | Full work summary + timeline |

---

## Environment Variables

Backend configuration (backend/.env):

```bash
# API
HOST=127.0.0.1
PORT=8000
DEBUG=true

# Database
DATABASE_URL=sqlite:///./raptorflow_leads.db

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_1B=gemma3:1b
OLLAMA_MODEL_4B=gemma3:4b

# Classifiers
CLASSIFIER_SCORE_THRESHOLD=70
```

Frontend uses `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`)

---

## Dependencies

**Backend** (Python 3.9+):
- FastAPI, uvicorn (API)
- SQLAlchemy, SQLite (database)
- pytesseract, Pillow (image OCR)
- pypdf (PDF text extraction)
- httpx (HTTP client for Ollama)
- pydantic (validation)

**Frontend** (Node 18+):
- Next.js, React, TypeScript
- TailwindCSS (styling)
- Framer Motion (animations)
- Lucide React (icons)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and dev workflow.

---

## License

[Add license here if applicable]

---

## Status: MVP Ready

✅ Code complete
✅ Error handling hardened
✅ Testing framework in place
⏳ Awaiting test execution

Next: Run [MANUAL_TEST_GUIDE.md](docs/MANUAL_TEST_GUIDE.md) to verify everything works.

---

**Built by Claude Code** | Local-first lead discovery engine | 100% privacy, 0% cloud
