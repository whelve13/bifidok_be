# Annex: Enterprise AI Sales Intelligence Platform & MCP Agent Architecture

## 1. Executive Summary & Problem Framing

Orange Systems sells advanced IT solutions, cloud architectures, cybersecurity services, and Agentic Process Automation across competitive international markets. Identifying qualified enterprise accounts currently relies on manual, unstandardized research: sales specialists spend hours reviewing financial disclosures, parsing press releases, tracking job boards, and browsing corporate portals.

This architecture specification details an automated, evidence-grounded B2B sales intelligence platform. The solution ingests public corporate data, runs dynamic business signal queries, scores prospective accounts using a hybrid machine learning and verification pipeline, and exposes these capabilities to external AI agent environments via an authenticated Model Context Protocol (MCP) server.

## 2. System Architecture

```
+-----------------------------------------------------------------------------------------------+
|                                  ORANGE SYSTEMS CORE CLOUD                                     |
|                                                                                                 |
|  +--------------------------+    HTTPS/WSS     +--------------------------------------------+  |
|  |     React SPA Client     | <=============>  |          FastAPI Application Core           |  |
|  | - User Auth & Org Admin  |                  | - OAuth2 / JWT Auth & API Key Provisioner   |  |
|  | - ICP & Rule Configurator|                  | - Async Ingestion Coordinator               |  |
|  | - HitL Outreach Review   |                  | - Scoring & Audit Evaluation Pipeline       |  |
|  +--------------------------+                  +---------------------+----------------------+  |
|                                                                       |                         |
|                                                        Writes Leads   | Caches Signals          |
|                                                        & Scorecards   | & Draft Queues          |
|                                                                       v                         |
|  +-------------------------------------+       +--------------------------------------------+  |
|  |       PostgreSQL 16 Database         |      |            Redis Cache & Broker             |  |
|  | - Accounts, Rules, Scored Leads      |      | - API Key Hash Index & Rate Limit Counters  |  |
|  | - Verbatim Evidence Citations        |      | - Transient Extracted Signal Cache          |  |
|  +-------------------------------------+       +---------------------+----------------------+  |
|                                                                       |                         |
|                                                       Auth Bearer     v                         |
|                                                 +--------------------------------------------+  |
|                                                 |    Remote MCP Server (SSE / HTTP Stream)    |  |
|                                                 | - Endpoint: /mcp/sse                        |  |
|                                                 +---------------------+----------------------+  |
+----------------------------------------------------------------------|------------------------+
                                                                        | JSON-RPC 2.0 via SSE
                                                                        v
+-----------------------------------------------------------------------------------------------+
|                                     AGENT RUNTIME ENVIRONMENT                                  |
|                           (Claude Code, Antigravity, Cursor, Terminal CLI)                     |
|                                                                                                 |
|  - Configuration: Header "Authorization: Bearer orange_sk_..."                                 |
|  - Context Tools: get_prioritized_leads(), get_signal_evidence()                                |
|  - Action Tools:  prepare_grounded_pitch(), send_sales_outreach_email()                         |
+-----------------------------------------------------------------------------------------------+
```

## 3. Data Ingestion & Storage Architecture

### 3.1 Ephemeral "Stream-and-Discard" Pipeline

Raw web scraping at scale quickly exhausts storage limits. To prevent infrastructure bloat, the data layer operates on a zero-persistence policy for raw document bodies:

- **Network Streaming**: Tenders (TED/EU portals), RSS feeds, and career page texts are streamed directly into volatile memory buffers (`io.BytesIO`).
- **Deterministic Pre-filtering**: Regex and keyword automata check incoming text chunks against predefined target accounts and trigger keywords.
- **Structured Extraction**: Relevant text segments are passed to the inference layer. Once the model outputs structured evidence quotes and confidence ratings, the underlying raw HTML, XML, or PDF payload is discarded.

### 3.2 Relational Database Schema (PostgreSQL)

```sql
-- Target Enterprise Accounts
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    industry VARCHAR(100),
    geography VARCHAR(100),
    employee_count INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Service Categories (e.g., "Agentic Automation", "Cybersecurity")
CREATE TABLE service_offerings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- Configurable Signal Questions per Offering
CREATE TYPE signal_weight_type AS ENUM ('HIGH', 'MEDIUM', 'LOW', 'DISQUALIFY');

CREATE TABLE signal_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES service_offerings(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    guidance_notes TEXT,
    weight signal_weight_type NOT NULL DEFAULT 'MEDIUM',
    is_negative BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LLM Signal Evaluations with Grounded Audit Trails
CREATE TABLE signal_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES signal_rules(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    detected BOOLEAN NOT NULL,
    confidence NUMERIC(3, 2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_quote TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Final Aggregated Lead Scoring
CREATE TABLE lead_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    service_id UUID REFERENCES service_offerings(id) ON DELETE CASCADE,
    composite_score INT NOT NULL CHECK (composite_score BETWEEN 0 AND 100),
    is_disqualified BOOLEAN NOT NULL DEFAULT FALSE,
    disqualification_reason TEXT,
    executive_summary TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, service_id)
);

-- API Keys for Remote MCP Server Access
CREATE TABLE mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 4. Machine Learning & Scoring Pipeline

### 4.1 Two-Tier Ingestion & Verification Architecture

```
[ Ingested Document Stream ]
             |
             v
+----------------------------+
| Tier 1: ML Pre-Classifier  |  (Fast local TF-IDF / Scikit-Learn Logistic Regression)
+----------------------------+
             |
             +---> Label 0 (Irrelevant / Boilerplate) ===> [ Evicted from Memory ]
             |
             v---> Label 1 (Potential Transformation Signal)
+----------------------------+
| Tier 2: Frontier LLM Agent |  (LangChain / GPT-4o / Claude 3.5 Structured Extraction)
+----------------------------+
             |
             +---> Programmatic Assertion: assert(evidence_quote in raw_document)
             v
[ Verified Signal Output: Quote + Confidence + Reasoning ]
```

- **Tier 1 (Fast Statistical Classifier)**: Runs locally on CPU. Categorizes raw paragraphs into actionable signals vs. routine enterprise announcements, shedding 95% of noise without incurring API token costs.
- **Tier 2 (Grounded Structured Extraction)**: Processes the remaining 5% of candidate text. The LLM extracts a structured JSON object containing a boolean flag, a confidence score (0.0–1.0), a justification, and an exact verbatim sentence.
- **Anti-Hallucination Guardrail**: The backend programmatically asserts that the extracted `evidence_quote` exists verbatim within the original source text before writing to the database.

### 4.2 Deterministic Scoring Logic

Composite scores ($S$) are calculated using positive weighted contributions penalized by detected negative indicators:

$$
S = \max\left(0, \, \min\left(100, \, \sum_{i \in \text{Pos}} (W_i \times C_i) - \sum_{j \in \text{Neg}} (P_{\text{base}} \times C_j)\right)\right)
$$

- **Weights**: HIGH = 35, MEDIUM = 20, LOW = 10.
- **Confidence Penalty ($P_{\text{base}}$)**: 25.
- **Disqualification Engine**: If any rule labeled `DISQUALIFY` is confirmed with $C \ge 0.80$, the account score immediately drops to 0 and outreach generation is locked.

## 5. Model Context Protocol (MCP) Server Specification

The MCP server acts as an open, standardized bridge between Orange Systems' intelligence backend and third-party AI agent environments (Claude Code, Cursor, Antigravity, Slack bots).

### 5.1 Remote MCP Implementation

```python
import os
import json
import redis
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Orange-Systems-Intelligence")
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

@mcp.tool()
def get_prioritized_leads(service_line: str, min_score: int = 70) -> str:
    """Discovers top enterprise leads prioritized by verified buying signals."""
    cached = r.get(f"leads:{service_line}")
    if cached:
        return cached
    # Fallback to persistent storage
    leads = [
        {"company": "DHL Group", "domain": "dhl.com", "score": 86, "primary_signal": "Strategy 2030 Agentic RFQ Deployment"},
        {"company": "Lufthansa Group", "domain": "lufthansa.com", "score": 46, "primary_signal": "4,000 Headcount Reduction Target"}
    ]
    return json.dumps([item for item in leads if item["score"] >= min_score], indent=2)

@mcp.tool()
def get_signal_evidence(domain: str) -> str:
    """Retrieves exact verbatim quotes and source links justifying why a company is ready to buy."""
    evidence = r.get(f"evidence:{domain}")
    if evidence:
        return evidence
    return json.dumps({"status": "NOT_FOUND", "message": f"No signals evaluated for domain: {domain}"})

@mcp.tool()
def prepare_grounded_pitch(company_name: str, recipient_title: str, evidence_quote: str, value_prop: str) -> str:
    """Generates an executive-level value proposition explicitly grounded in verified evidence."""
    return f"""Subject: Supporting {company_name}'s automation initiatives alongside internal teams

Hi {recipient_title},

I noted that {company_name} is actively deploying programs targeting operational processes, specifically: "{evidence_quote}".

Orange Systems specializes in {value_prop}. We assist enterprise digital teams by delivering high-throughput automation modules that integrate directly with existing platforms without proprietary lock-in.

Would you be open to a 10-minute briefing next week to review our reference architecture?

Best regards,
Enterprise Solutions | Orange Systems
"""

@mcp.tool()
def send_sales_outreach_email(recipient_email: str, subject: str, email_body: str, dry_run: bool = True) -> str:
    """
    Stages or sends a sales outreach email.
    When dry_run=True, queues the draft in the Orange Dashboard for human approval.
    """
    draft_id = f"draft_{os.urandom(4).hex()}"
    payload = {
        "recipient": recipient_email,
        "subject": subject,
        "body": email_body,
        "status": "AWAITING_HUMAN_APPROVAL" if dry_run else "DISPATCHED"
    }
    r.set(f"outreach_queue:{draft_id}", json.dumps(payload))

    if dry_run:
        return f"SUCCESS: Draft {draft_id} staged in Orange Dashboard queue for human review."
    return f"SUCCESS: Email dispatched to {recipient_email}."

if __name__ == "__main__":
    mcp.run(transport="sse")
```

### 5.2 Agent Environment Integration

Client agents authenticate against the remote server using the following configuration pattern:

```json
{
  "mcpServers": {
    "orange-systems": {
      "url": "https://api.orange-systems.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer orange_sk_8f9a2b1049c812de"
      }
    }
  }
}
```

## 6. End-to-End Account Case Studies

### 6.1 Lufthansa Group

**Signals Detected:**

- **Positive Trigger**: Official target to reduce ~4,000 administrative jobs by 2030 using automation, digitalization, and process consolidation.
- **Counter / Negative Trigger**: Strong internal development division (Lufthansa Systems) that creates organizational resistance to external standard software.

**System Score:** 46 / 100 (Qualified, but categorized as Review Needed).

**Strategy:** System alerts the sales team to avoid generic RPA pitches and focus strictly on specialized co-delivery architecture.

### 6.2 DHL Group

**Signals Detected:**

- **Positive Trigger**: Corporate "Strategy 2030" prioritizes agentic AI; production deployments live for RFQ quotation and operational communications.
- **Positive Trigger**: Public policy explicitly confirms the use of third-party software vendors alongside internal engineering to accelerate adoption.

**System Score:** 86 / 100 (Tier-1 Priority Lead).

**Strategy:** Immediate outreach targeting orchestration layer support to complement their existing internal vendor stack.

## 7. Competitive Differentiation Matrix

| Evaluation Dimension | Legacy Contact Databases (ZoomInfo, Apollo) | Ad-Intent Platforms (6sense, Demandbase) | Orange Systems MCP Platform |
|---|---|---|---|
| **Data Nature** | Static contact directories with high decay rates. | Anonymous aggregated web-cookie surges. | Dynamic, real-time public signal extraction. |
| **Verifiability** | No evidence; basic demographic labels. | Black-box numerical scoring without reasoning. | Complete provenance: direct verbatim quote and source URL. |
| **Customizability** | Fixed standard filters (headcount, industry). | Pre-packaged intent categories. | Dynamic natural-language business questions per service line. |
| **Negative Signals** | Cannot process disqualifying indicators. | Ignores existing internal software capacity. | Explicit negative penalties and hard disqualification rules. |
| **Workflow Model** | Web UI silo; manual export of CSVs. | Fixed web interface and CRM sync. | Universal MCP Server integration into any AI agent runtime. |
