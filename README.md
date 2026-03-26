# RiskQ360 — Risk. Quality. Everything in between.

AI-powered clinical documentation analytics platform for healthcare risk adjustment (HCC/RAF) and quality metrics (HEDIS).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RiskQ360 Platform                         │
├─────────────┬────────────────────────┬──────────────────────┤
│  Frontend   │      Backend API       │     Database         │
│  React 19   │      FastAPI           │   PostgreSQL 16      │
│  Mantine 8  │      Python 3.12       │                      │
│  TypeScript │      SQLAlchemy 2.0    │   35+ tables         │
│  Vite 7     │      Pydantic v2       │   Assertion-centric  │
│  Port 3008  │      Port 8006         │   Port 5432          │
└─────────────┴────────────────────────┴──────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)
- PostgreSQL 16 (or use Docker)

### Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/madhuu559u/riskq360.git
cd riskq360

# Copy environment file and configure
cp .env.example .env
# Edit .env with your API keys

# Build and start all services
docker compose up --build -d

# Access the application
# Frontend: http://localhost:3008
# Backend API: http://localhost:8006
# API Docs: http://localhost:8006/docs
```

### Local Development

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3008
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8006 --reload
```

**Database:**
```bash
# Start PostgreSQL via Docker
docker compose up db -d
```

## Project Structure

```
RiskQ360_FINAL_VERSION/
├── frontend/          # React + Mantine + TypeScript SPA
├── backend/           # FastAPI + Python backend
│   ├── api/           # REST API routes & schemas
│   ├── core/          # Pipeline orchestration
│   ├── database/      # ORM models & repositories
│   ├── services/      # Business logic
│   ├── extraction/    # LLM-based clinical extraction
│   ├── ingestion/     # PDF processing & OCR
│   ├── decisioning/   # HCC mapping, RAF calc, HEDIS eval
│   ├── hedis/         # HEDIS rules engine
│   ├── ml_engine/     # BioClinicalBERT + TF-IDF
│   └── config/        # Settings & feature flags
├── nginx/             # Nginx reverse proxy config
├── docs/              # Documentation
├── docker-compose.yml # Multi-service orchestration
└── .env.example       # Environment template
```

## Key Features

- **PDF Chart Processing** — Upload medical documents, AI extracts clinical data
- **HCC Risk Coding** — Automated ICD-10 to HCC V28 mapping with hierarchy
- **RAF Score Calculation** — Risk Adjustment Factor computation
- **HEDIS Quality Metrics** — Care gap identification and measure compliance
- **Evidence Highlighting** — Link extracted data to exact PDF text
- **Review Workflows** — Approve/reject AI-extracted diagnoses
- **6 Visual Themes** — Professional dark/light UI themes
- **Full Audit Trail** — Complete traceability of all actions

## Login Credentials (Demo)

- Username: `riskq360` | Password: `demo2026`
- Username: `admin` | Password: `admin`

## Documentation

See `docs/RiskQ360_Documentation.html` for comprehensive documentation covering frontend, backend, APIs, database schemas, and setup guides.

## License

Proprietary - All rights reserved.
