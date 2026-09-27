# Orange Systems - Enterprise AI Sales Intelligence Platform

Autonomous B2B customer prospecting, multi-source evidence harvesting, and buying intent scoring platform for enterprise IT and digital transformation services.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Multi-Source Connector Suite](#multi-source-connector-suite)
- [Three-Layer Scoring and Machine Learning Engine](#three-layer-scoring-and-machine-learning-engine)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quick Start Guide](#quick-start-guide)
  - [1. Backend Setup](#1-backend-setup)
  - [2. Frontend Setup](#2-frontend-setup)
  - [3. Full Stack with Docker Compose](#3-full-stack-with-docker-compose)
- [Interactive Command Line Interface (CLI)](#interactive-command-line-interface-cli)
- [Model Context Protocol (MCP) Server](#model-context-protocol-mcp-server)
- [REST API Reference](#rest-api-reference)
- [Frontend Application Views](#frontend-application-views)
- [Testing Suite](#testing-suite)
- [Configuration and Environment Variables](#configuration-and-environment-variables)
- [License and Disclaimers](#license-and-disclaimers)

---

## Overview

Orange Systems sells advanced IT solutions, cloud architectures, cybersecurity services, and Agentic Process Automation across competitive international markets. Identifying qualified enterprise accounts traditionally relies on manual, unstandardized research: sales specialists spend hours reviewing financial disclosures, parsing press releases, tracking job boards, and browsing corporate portals.

This platform transforms public enterprise data into verifiable, actionable B2B buying signals. By harvesting real-time data across eight distinct intelligence vectors, processing signals through local machine learning models and grounded LLM extraction, and applying deterministic scoring algorithms, the platform delivers prioritized lead scorecards and executive value propositions with zero hallucination.

---

## Key Features

- Dynamic Commercial Offerings: Define flagship or bespoke service lines (Agentic Automation, Cloud Migration, Cybersecurity, Custom IT services) with custom signal questions, commercial wedges, and target ICP criteria.
- Multi-Source Data Harvesting: Collects telemetry from firmographics, financial disclosures, global news (GDELT), applicant tracking systems (job postings), cybersecurity posture, official corporate registries, public procurement tenders (EU TED), and developer activity.
- 3-Layer Scoring Pipeline:
  - Layer 1: Fast local ML models (Random Forest, Gradient Boosting, Ridge) trained on historical corporate transformation episodes.
  - Layer 2: LLM-powered structured signal extraction with strict verbatim anti-hallucination verification.
  - Layer 3: Deterministic composite scoring with negative penalization and instant disqualification gates.
- Human-in-the-Loop Outreach: Staging queue for executive value propositions and outreach drafts, ensuring sales representatives retain full governance before dispatch.
- Model Context Protocol (MCP) Server: FastMCP implementation allowing AI agents (Claude Code, Antigravity, Cursor) to discover prioritized leads, inspect audit quotes, and stage outreach.
- Interactive Command Line Interface: Full-featured terminal console for headless execution, batch prospecting, dataset harvesting, model retraining, and system diagnostics.
- Modern Web Dashboard: React 19 single-page application styled with Tailwind CSS, providing real-time universe rankings, connector telemetry, model diagnostics, and offer authoring.

---

## System Architecture

```
+-----------------------------------------------------------------------------------------------+
|                                  ORANGE SYSTEMS CORE CLOUD                                     |
|                                                                                                 |
|  +--------------------------+    HTTPS/JSON    +--------------------------------------------+  |
|  |   React 19 Dashboard     | <==============> |          FastAPI Application Core          |  |
|  | - Universe Ranking View  |                  | - Dynamic Commercial Offer Compiler        |  |
|  | - Bidirectional Matcher  |                  | - Multi-Source Ingestion Coordinator       |  |
|  | - HitL Outreach Queue    |                  | - 3-Layer Scoring & Disqualification Engine|  |
|  | - ML Engine Diagnostics  |                  | - Preflight Health Probes (/healthz)       |  |
|  +--------------------------+                  +---------------------+----------------------+  |
|                                                                       |                         |
|                                                        Writes Leads   | Caches Signals          |
|                                                        & Scorecards   | & Session Tokens        |
|                                                                       v                         |
|  +-------------------------------------+       +--------------------------------------------+  |
|  |       PostgreSQL 16 Database         |      |            Redis Cache & Broker            |  |
|  | - Accounts, Rules, Scored Leads      |      | - API Key Hash Index & Rate Limit Counters |  |
|  | - Verbatim Evidence Citations        |      | - Transient Ingestion Buffers              |  |
|  +-------------------------------------+       +---------------------+----------------------+  |
|                                                                       |                         |
|                                                       Auth Bearer     v                         |
|                                                 +--------------------------------------------+  |
|                                                 |       FastMCP Server (JSON-RPC 2.0)        |  |
|                                                 | - Tools: get_prioritized_leads, etc.       |  |
|                                                 +---------------------+----------------------+  |
+----------------------------------------------------------------------|------------------------+
                                                                        | Standard MCP Protocol
                                                                        v
+-----------------------------------------------------------------------------------------------+
|                                  AI AGENT RUNTIME ENVIRONMENT                                 |
|                           (Claude Code, Antigravity, Cursor, Terminal CLI)                    |
|                                                                                               |
|  - Tools: get_prioritized_leads(), get_signal_evidence(), prepare_grounded_pitch()            |
|  - Governance: Human-in-the-Loop staging before email dispatch                                |
+-----------------------------------------------------------------------------------------------+
```

---

## Multi-Source Connector Suite

The ingestion layer connects to eight enterprise data vectors, maintaining an ephemeral "stream-and-discard" posture to process raw web text without persistent storage bloat:

1. Firmographics (`connectors/firmographics.py`):
   Entity resolution, primary sector classification, employee headcount tiers, headquarters geography, and domain verification.
2. Financial Disclosures (`connectors/financials.py`):
   Operating margins, year-over-year revenue growth, CAPEX expansion, debt-to-equity ratios, and public market signals (via Yahoo Finance / SEC disclosures).
3. News and Strategic Signals (`connectors/news.py`):
   Live and historical news scanning via GDELT Project and corporate press releases, identifying restructuring, acquisitions, and executive catalysts.
4. Applicant Tracking Systems (`connectors/ats.py`):
   Hiring velocity analysis across public career boards (Greenhouse, Lever, Workday) detecting open roles for RPA developers, automation architects, data engineers, and security specialists.
5. Security Posture and CVE Exposure (`connectors/security.py`, `connectors/vulnerabilities.py`):
   Evaluates public security posture, HTTP security headers (HSTS, CSP, X-Frame-Options), and cross-references active vulnerabilities against the CISA Known Exploited Vulnerabilities (KEV) catalog.
6. Official Corporate Registries (`connectors/registries.py`):
   Validation against official business registries (Companies House, OpenCorporates, EU transparency portals) for active status, incorporation age, and compliance standing.
7. Public Procurement and Tenders (`connectors/tenders.py`):
   Tracks active and awarded RFPs on European public procurement platforms (TED - Tenders Electronic Daily) matching relevant CPV codes.
8. Developer Telemetry (`connectors/developer.py`):
   Open-source code velocity, active repositories, and technology stack footprints via GitHub and public software telemetry.

---

## Three-Layer Scoring and Machine Learning Engine

The platform eliminates arbitrary scoring through an explainable, multi-stage pipeline:

```
[ Ingested Multi-Vector Telemetry ]
                 |
                 v
+----------------------------------+
| Layer 1: Local ML Pre-Classifier |  --> Fast CPU inference (Feature Extractor: 18 signals)
|                                  |  --> Disqualification Classifier (100% accuracy on invalid ICP)
|                                  |  --> Propensity Regressor (Predicts purchase readiness: 0-100)
|                                  |  --> Commercial Wedge Classifier (Assigns highest-impact wedge)
+----------------------------------+
                 |
                 v (Qualified Candidates)
+----------------------------------+
| Layer 2: LLM Structured Extractor|  --> Frontier LLM (Google Gemini / Anthropic / OpenAI)
|                                  |  --> Extracts exact evidence quotes, confidence, and reasoning
|                                  |  --> Programmatic Assertion: assert quote in raw_document
+----------------------------------+
                 |
                 v
+----------------------------------+
| Layer 3: Deterministic Scoring   |  --> Positive weights: HIGH (+35), MEDIUM (+20), LOW (+10)
|                                  |  --> Negative penalties: Confidence-scaled deduction
|                                  |  --> Disqualification overrides: Instant drop to 0 score
+----------------------------------+
                 |
                 v
[ Final Perfect Customer Dossier ]
```

### Programmatic Anti-Hallucination Guardrail

Before any evidence is recorded or factored into an outreach pitch, the system enforces strict token-level verification:

```python
# Rule verification in engine/anti_hallucination.py
def verify_evidence_grounding(evidence_quote: str, raw_source_text: str) -> bool:
    normalized_quote = " ".join(evidence_quote.strip().split()).lower()
    normalized_source = " ".join(raw_source_text.strip().split()).lower()
    return normalized_quote in normalized_source
```

If an extracted quote cannot be located verbatim inside the raw source stream, the signal is discarded and flagged for manual audit.

---

## Repository Structure

```
d:/GIGAHACK/
|-- backend_fe/                      # Frontend Application (React 19, TypeScript, Vite)
|   |-- public/                      # Static assets and icons
|   |-- src/
|   |   |-- assets/                  # Images and logos
|   |   |-- components/              # UI components
|   |   |   |-- BusinessMatcher.tsx  # Bidirectional offer-company matching view
|   |   |   |-- ConnectorHub.tsx     # Live connector inspection and raw telemetry
|   |   |   |-- DoctorModal.tsx      # System health and preflight diagnostics modal
|   |   |   |-- DossierDrawer.tsx    # Slide-over account dossier and audit quote inspector
|   |   |   |-- Header.tsx           # Global navigation and action bar
|   |   |   |-- MLEngineHub.tsx      # Model training, dataset harvester, and feature charts
|   |   |   |-- OfferConfigurator.tsx# Natural language commercial offering compiler
|   |   |   |-- OutreachQueue.tsx    # Human-in-the-Loop email dispatch review
|   |   |   |-- Sidebar.tsx          # Navigation sidebar
|   |   |   `-- UniverseView.tsx     # Prospecting ranking matrix and scorecards
|   |   |-- services/
|   |   |   `-- api.ts               # Typed client integration to backend endpoints
|   |   |-- types/
|   |   |   `-- index.ts             # Shared TypeScript interfaces
|   |   |-- App.tsx                  # Root application component
|   |   |-- main.tsx                 # React DOM mount
|   |   `-- index.css                # Tailwind CSS design system styles
|   |-- package.json
|   |-- tsconfig.json
|   `-- vite.config.ts               # Vite bundler configuration with backend proxy
|
|-- bifidok_be/                      # Backend Service (Python 3.12, FastAPI, ML)
|   |-- bifidok_be/
|   |   |-- api/                     # REST API routers
|   |   |   |-- app.py               # Main FastAPI application and lifespan handler
|   |   |   |-- auth.py              # API key provisioning and verification
|   |   |   |-- routes_config.py     # Offering compilation endpoints
|   |   |   |-- routes_leads.py      # Lead discovery and feedback endpoints
|   |   |   |-- routes_outreach.py   # Staged outreach and approval queue
|   |   |   `-- routes_prospect.py   # Universe ranking, matching, and ML training
|   |   |-- connectors/              # Multi-source data harvesting adapters
|   |   |   |-- ats.py               # Job board and hiring signal harvester
|   |   |   |-- developer.py         # Open-source and GitHub telemetry
|   |   |   |-- financials.py        # Financial metrics and margin disclosures
|   |   |   |-- firmographics.py     # Corporate metadata and entity resolution
|   |   |   |-- gdelt.py             # Global event and news intelligence
|   |   |   |-- news.py              # Targeted media and press release parsing
|   |   |   |-- registries.py        # Official government registry verification
|   |   |   |-- security.py          # Security posture and header audit
|   |   |   |-- tenders.py           # Public procurement (TED) tender scraper
|   |   |   `-- vulnerabilities.py   # CISA KEV vulnerability cross-referencing
|   |   |-- data/                    # Historical market datasets for model training
|   |   |   `-- historical_harvester.py # Multi-day market episode synthesizer
|   |   |-- db/                      # Database models, connection, and seeding
|   |   |   |-- repository.py        # SQLAlchemy query abstractions
|   |   |   |-- schema.py            # PostgreSQL table schemas
|   |   |   |-- seed.py              # Canonical enterprise benchmarks and offerings
|   |   |   `-- session.py           # Database engine and connection pooling
|   |   |-- engine/                  # Core intelligence and machine learning
|   |   |   |-- local_ml/            # Trained local scikit-learn and LightGBM models
|   |   |   |   |-- feature_extractor.py # 18-dimension signal normalization
|   |   |   |   |-- inference.py     # Local model execution wrapper
|   |   |   |   |-- trainer.py       # Supervised model training script
|   |   |   |   `-- weights/         # Serialized joblib models and metadata
|   |   |   |-- anti_hallucination.py# Verbatim evidence assertion guardrail
|   |   |   |-- autonomous_scout.py  # Background account discovery agent
|   |   |   |-- candidate_pool.py    # Enterprise entity directory
|   |   |   |-- offering_catalog.py  # Flagship offerings and LLM offering compiler
|   |   |   |-- precomputed_store.py # High-speed telemetry lookup
|   |   |   `-- prospecting_engine.py# End-to-end prospecting orchestrator
|   |   |-- services/                # Business services
|   |   |   |-- cache.py             # Redis client and caching abstractions
|   |   |   |-- diagnostics.py       # Preflight health checking probes
|   |   |   |-- ingestion_coordinator.py # Stream-and-discard pipeline manager
|   |   |   |-- leads_service.py     # Scored lead querying and pitch formatting
|   |   |   `-- proxy_manager.py     # Resilient HTTP request dispatch
|   |   |-- tests/                   # Pytest automated test suite
|   |   |-- cli.py                   # Interactive Rich terminal CLI
|   |   |-- config.py                # Environment configuration
|   |   |-- mcp_server.py            # FastMCP server for AI agent environments
|   |   `-- models.py                # Pydantic domain models
|   |-- Dockerfile                   # Production container definition
|   |-- docker-compose.yml           # Multi-container orchestration (API, PG, Redis)
|   |-- render.yaml                  # Cloud deployment specification
|   `-- requirements.txt             # Python package dependencies
|
|-- documentation/                   # Specifications and requirements
|   |-- context.md                   # Enterprise architecture and data model specification
|   |-- data_api_endpoints.xlsx      # Commercial data source inventory
|   `-- task.md                      # Problem brief and challenge requirements
`-- README.md                        # Master project documentation
```

---

## Prerequisites

- Operating System: Linux, macOS, or Windows 10/11 (with PowerShell or bash).
- Python: Version 3.11 or 3.12.
- Node.js: Version 20.x or higher (with npm 10+).
- Docker and Docker Compose (optional, for containerized execution).
- PostgreSQL 16 and Redis 7 (optional, backend falls back gracefully to SQLite and in-memory cache for standalone local execution).

---

## Quick Start Guide

### 1. Backend Setup

From the repository root:

```bash
# Navigate to the backend directory
cd bifidok_be

# Create and activate a Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# (Optional) Configure environment variables
cp .env.example .env
# Edit .env to supply your GEMINI_API_KEY if testing live LLM features

# Launch the FastAPI application
python -m uvicorn bifidok_be.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The API will initialize, execute preflight checks, automatically seed the database with canonical enterprise benchmarks, and become available at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup

In a separate terminal:

```bash
# Navigate to the frontend directory
cd backend_fe

# Install Node.js packages
npm install

# Start the Vite development server
npm run dev
```

Open `http://localhost:3000` in your web browser. The frontend is configured with a built-in reverse proxy routing all `/api`, `/health`, and `/healthz` requests to `http://localhost:8000`.

### 3. Full Stack with Docker Compose

To run the complete production topology including PostgreSQL 16, Redis 7, and the FastAPI backend:

```bash
cd bifidok_be
docker compose up --build -d
```

Verify service status:

```bash
docker compose ps
curl http://localhost:8000/healthz
```

---

## Interactive Command Line Interface (CLI)

The platform includes an interactive Rich terminal console for sales development representatives and operations engineers:

```bash
cd bifidok_be
python bifidok_be/cli.py menu
```

### CLI Menu Options

1. Find top companies for offer X:
   Select from flagship offerings or supply a custom mandate. The CLI ranks accounts by buying readiness, highlights the primary commercial wedge, and prints audit evidence quotes.
2. Find best offer for X company:
   Input any company name (e.g., `DHL Group`, `Siemens`, `BASF`, `Zalando`). The engine scans all commercial services and returns the highest-impact value proposition.
3. Analyze Offer X with Company X:
   Perform an in-depth fit analysis between a specific service line and target account, outputting detailed signal breakdown and anti-hallucination verification.
4. Fetch data (input data amount in days):
   Harvest and synthesize multi-day historical market episodes (default: 90 days) into `historical_market_dataset.jsonl`.
5. Train on data:
   Trigger local training of the Disqualification Classifier, Propensity Regressor, and Commercial Wedge Classifier. Displays training metrics (MAE, R2, macro-F1) and feature importance rankings.
0. Exit: Terminate the console session.

### Direct Subcommands

The CLI also supports non-interactive execution:

```bash
# Prospect accounts for a specific offering
python bifidok_be/cli.py find-companies --offering agentic_automation

# Match best offering for an enterprise
python bifidok_be/cli.py best-offer --company "DHL Group"

# Evaluate fit between offer and company
python bifidok_be/cli.py analyze --company "Siemens" --offering cybersecurity

# Harvest historical market telemetry
python bifidok_be/cli.py fetch-data --days 180

# Retrain local ML models
python bifidok_be/cli.py train --samples 500

# Execute preflight system diagnostics
python bifidok_be/cli.py doctor

# Inspect model weights and metadata
python bifidok_be/cli.py models-info
```

---

## Model Context Protocol (MCP) Server

The platform implements the FastMCP protocol, enabling autonomous AI coding and workflow agents (Claude Code, Cursor, Antigravity) to query sales intelligence directly.

### Running the MCP Server

```bash
cd bifidok_be
python bifidok_be/mcp_server.py
```

### Exposed MCP Tools

- `get_prioritized_leads(service_line: str, min_score: int = 70) -> str`:
  Returns enterprise accounts exceeding the score threshold for the specified service line.
- `get_signal_evidence(domain: str) -> str`:
  Returns verbatim evidence quotes, publication dates, and source URLs justifying why an account has buying intent.
- `prepare_grounded_pitch(company_name: str, recipient_title: str, evidence_quote: str, value_prop: str) -> str`:
  Constructs an executive value proposition strictly anchored to verified quotes.
- `send_sales_outreach_email(recipient_email: str, subject: str, email_body: str, dry_run: bool = True) -> str`:
  Enqueues an outreach draft into the Human-in-the-Loop staging review table.

### Integrating with Claude Desktop or Agent Configuration

Add the following block to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "orange-systems-intelligence": {
      "command": "python",
      "args": ["-m", "bifidok_be.mcp_server"],
      "cwd": "/path/to/bifidok_be"
    }
  }
}
```

---

## REST API Reference

The FastAPI service exposes comprehensive endpoints for UI clients, external scripts, and CI/CD pipelines:

### System and Diagnostics
- `GET /health`: Returns service availability and UTC timestamp.
- `GET /healthz`: Comprehensive preflight probe checking Database, Redis, and Gemini connectivity.
- `GET /api/prospect/doctor`: Detailed connectivity diagnostics across database pools and connector caches.

### Prospecting and Scoring
- `GET /api/prospect/offerings`: Returns all commercial offerings in the catalog.
- `POST /api/prospect/offerings/custom`: Accepts a natural language mandate and compiles a new dynamic commercial offering.
- `DELETE /api/prospect/offerings/custom/{id}`: Deactivates a custom commercial offering.
- `POST /api/prospect/universe`: Returns the ranked universe of enterprise accounts for an offering.
- `POST /api/prospect/analyze`: Evaluates fit between a specific offering and company domain.
- `POST /api/prospect/best-offer`: Discovers the highest-scoring commercial offering for a given account.
- `POST /api/prospect/connectors/live`: Fetches live, unparsed connector telemetry across all eight vectors for an account.

### Machine Learning
- `POST /api/prospect/ml/harvest`: Harvests multi-day market signal datasets (`days` parameter).
- `POST /api/prospect/ml/train`: Triggers model retraining and updates model weights on disk.
- `GET /api/prospect/ml/models-info`: Returns current model training timestamps, accuracy metrics, and feature importances.

### Leads and Evidence
- `GET /api/leads?service_line={line}&min_score={score}`: Retrieves scored leads meeting filter criteria.
- `GET /api/leads/{domain}/evidence`: Returns verbatim audit quotes and source links for an account.
- `POST /api/leads/{id}/feedback`: Records sales representative qualification feedback to refine model weights.

### Human-in-the-Loop Outreach
- `GET /api/outreach/queue`: Lists staged outreach drafts awaiting human review.
- `POST /api/outreach/stage`: Stages a newly generated email draft in the review queue.
- `POST /api/outreach/{draft_id}/approve`: Approves and dispatches a staged outreach draft.

---

## Frontend Application Views

The web dashboard is organized into seven functional workspaces accessible via the sidebar:

1. Prospecting Universe (`UniverseView.tsx`):
   Matrix of target accounts sorted by propensity score, displaying commercial wedge alignment, confidence bars, tier classifications (TIER 1 TARGET, TIER 2 PRIORITY, TIER 3 NURTURE, DISQUALIFIED), and quick actions.
2. Business Matcher (`BusinessMatcher.tsx`):
   Two-way matching engine allowing sales reps to either select a company to find its optimal solution, or select an offer to identify the top 5 buying candidates.
3. Commercial Offer Configurator (`OfferConfigurator.tsx`):
   Interactive compiler that translates natural language value propositions into structured ICP criteria, signal questions, weights, and disqualification rules.
4. Connector Hub (`ConnectorHub.tsx`):
   Live telemetry diagnostic terminal displaying raw signals, HTTP header statuses, CISA KEV vulnerability matches, ATS job listings, and tender procurement matches for any target domain.
5. Outreach Review Queue (`OutreachQueue.tsx`):
   Governance interface for reviewing, editing, approving, or rejecting AI-generated outreach drafts before transmission.
6. Machine Learning Engine Hub (`MLEngineHub.tsx`):
   Operations console showing model training metrics (R2: 0.997, MAE: 1.05), feature importance rankings (Semantic Relevance: 22%, Active Tenders: 15%, Enterprise ERP: 10%), and one-click data harvesting and retraining triggers.
7. Account Deep-Dive Drawer (`DossierDrawer.tsx`):
   Slide-over panel presenting the full Perfect Customer Dossier: executive summary, strategic pitch narrative, signal evaluations, and verbatim audit quotes.

---

## Testing Suite

The backend includes a comprehensive automated test suite covering all critical platform components:

```bash
cd bifidok_be
pytest bifidok_be/tests -v
```

### Test Coverage Highlights

- `test_api_endpoints.py`: Validates FastAPI route responses, health probes, and error handling.
- `test_connectors.py`: Verifies network resilience, parsing logic, and fallback behavior across all data connectors.
- `test_db.py`: Tests SQLAlchemy database transactions, repository queries, and seed data integrity.
- `test_local_ml_and_scout.py`: Asserts feature extraction dimensions (18 features), model predictions, and autonomous scout scoring.
- `test_offering_compile.py`: Tests dynamic offering decomposition, wedge extraction, and signal rule weighting.
- `test_mcp_server.py`: Verifies FastMCP tool invocation and JSON-RPC compliance.
- `test_cache_and_ingestion.py`: Validates Redis caching keys and stream-and-discard buffer behavior.

---

## Configuration and Environment Variables

Configuration is managed via environment variables. Create a `.env` file in `bifidok_be/` with the following parameters:

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | string | `sqlite:///sales_intelligence.db` | PostgreSQL connection string or SQLite fallback URI |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Redis cache and broker URI |
| `GEMINI_API_KEY` | string | `""` | Google Gemini API key for structured signal extraction |
| `GEMINI_MODEL` | string | `gemini-2.5-flash` | Target LLM model identifier |
| `STRICT_PRODUCTION` | boolean | `false` | When true, enforces strict PostgreSQL and Redis availability |
| `PORT` | integer | `8000` | Port on which the FastAPI server listens |
| `ENVIRONMENT` | string | `development` | Runtime environment (`development`, `staging`, `production`) |

---

## License and Disclaimers

Copyright 2026 Orange Systems. Internal enterprise software platform developed for autonomous B2B sales intelligence and market research.

Notice: This platform ingests and analyzes publicly available enterprise disclosures, news publications, career boards, and official corporate registries. It does not perform invasive scraping, credentials harvesting, or violate third-party terms of service. All outreach generation includes human-in-the-loop governance gates to comply with enterprise communication policies.
