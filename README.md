# DQ-Agent: Autonomous Data Quality Agent
 
> **WeMakeDevs × OpenMetadata Hackathon 2026** — MCP Ecosystem & AI Agents Track
 
DQ-Agent is an autonomous **LangGraph state machine** that connects to any OpenMetadata instance, fetches data quality failures, traces downstream blast radius via lineage, and dispatches AI-generated executive reports to **Slack** and **Google Sheets** — all from a single command or natural language prompt via MCP.
 
---
 
## The Problem
 
Data teams drown in raw DQ alert noise. Every test failure fires a separate Slack ping with zero context — no severity, no owner, no blast radius, no trend. Engineers waste **3–5 hours every Monday** manually compiling DQ review spreadsheets that are already stale.
 
**DQ-Agent eliminates this entirely.**
 
---
 
## See It Working
 
 
### Terminal — LangGraph Pipeline
```
DQ-Agent (LangGraph) | Weekly Data Quality Report
==================================================
Starting LangGraph Workflow...
--- INGESTOR NODE ---
--- CLASSIFIER NODE ---
--- INVESTIGATOR NODE (Agent) ---
--- SUMMARIZER NODE ---
--- DISPATCHER NODE ---
✅ Report written to Google Sheets
✅ Alert posted to Slack
 
--- FINAL STATE MESSAGES ---
Action: Fetched 13 raw failures from OpenMetadata.
Action: Classified failures. Max severity: P1
Action: Investigated lineage. Blast radius calculated.
Action: Generated executive summary.
Action: Dispatched alerts to Slack and Sheets.
==================================================
DQ-Agent LangGraph run complete!
```
 
---
 
## Architecture
 
```
OpenMetadata REST API
        │
        ▼
┌─────────────────────────────────────────────────┐
│           LangGraph State Machine               │
│                                                 │
│  [INGESTOR] → [CLASSIFIER] → [INVESTIGATOR]     │
│                                   │             │
│                              [SUMMARIZER]       │
│                                   │             │
│                              [DISPATCHER]       │
└─────────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
   Google Sheets          Slack
   (Styled Report)     (Block Kit Alert)
        │
        ▼
   MCP Server
   (Claude Desktop / Cursor)
```
 
### The 5-Node Pipeline
 
| Node | What It Does |
|---|---|
| **INGESTOR** | Authenticates with OM, fetches all failed DQ test cases for the past 7 days |
| **CLASSIFIER** | Assigns P1/P2/P3 severity; escalates to P1 if table has PII, Tier1, or Sensitive tags |
| **INVESTIGATOR** | Queries `/api/v1/lineage` to calculate downstream blast radius per failing table |
| **SUMMARIZER** | Sends aggregated data to Gemini LLM → generates executive summary + root cause hypothesis |
| **DISPATCHER** | Writes styled Google Sheet + posts Slack Block Kit message with deep OM links |
 
---
 
## Core Capabilities
 
- **MCP Integration** — Exposes `get_table_health`, `list_recent_failures`, `trigger_weekly_report` as native MCP tools usable directly from Claude Desktop or Cursor
- **Deep Lineage Tracing** — Queries `/api/v1/lineage/table/name/{fqn}` to find every downstream Dashboard, ML Model, and Pipeline impacted by a failure
- **Governance & PII Awareness** — Tables tagged `PII`, `Tier1`, or `Sensitive` are auto-escalated to P1 Critical regardless of test type
- **Severity Scoring** — Schema tests → P1, data correctness tests → P2, null/uniqueness checks → P3
- **Week-over-Week Trends** — Compares current week failures against previous week per table
- **AI Root Cause Hypothesis** — LLM clusters failures sharing common upstream lineage ancestors and proposes probable root causes
---
 
## Setup & Installation
 
### Prerequisites
- Python 3.11+
- Docker Desktop (for OpenMetadata)
- A Google Cloud Service Account with Sheets API enabled
- A Slack Bot Token with `chat:write` scope
### Step 1 — Run OpenMetadata Locally
 
```bash
curl -sL https://github.com/open-metadata/OpenMetadata/releases/download/1.3.1-release/docker-compose.yml -o docker-compose.yml
docker compose up -d
# UI available at http://localhost:8585  (admin / admin)
```
 
### Step 2 — Clone and Install
 
```bash
git clone https://github.com/Photon079/Openmetaadatahack.git
cd Openmetaadatahack
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
 
### Step 3 — Configure Environment
 
Create a `.env` file in the project root:
 
```bash
# OpenMetadata (required)
OM_BASE_URL=http://localhost:8585
OM_USERNAME=admin
OM_PASSWORD=admin
 
# AI Summarization (required)
GEMINI_API_KEY=your_gemini_api_key
 
# Slack (optional — skip with --no-slack)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#data-alerts
 
# Google Sheets (optional — skip with --no-sheets)
SHEET_ID=your_google_sheet_id
```
 
Place your `gcp-sa.json` (Google Cloud Service Account) in the project root for Sheets access.
 
### Step 4 — Seed Sample Data (Recommended)
 
If your OpenMetadata instance has no DQ test data, run the seed script to populate realistic failures:
 
```bash
python data/seed_om.py
```
 
This creates sample tables, test cases, and injects failure results so you can see the full report immediately.
 
---
 
## Usage
 
### Option A — CLI (Quickest)
 
```bash
# Full run — fetch from OM, post to Slack + Sheets
python agent.py
 
# Filter by domain
python agent.py --domain finance
 
# Run with mock data (no live OM needed)
python agent.py --mock
 
# Disable external outputs (terminal only)
python agent.py --no-slack --no-sheets
 
# Mock mode with no external outputs (works offline, zero config)
python agent.py --mock --no-slack --no-sheets
```
 
### Option B — MCP with Cursor IDE
 
1. Open Cursor → Settings → Features → MCP → **+ Add New MCP Server**
2. Name: `DQ-Agent` | Type: `command`
3. Command: `/absolute/path/to/venv/bin/python /absolute/path/to/mcp_server.py`
4. Open Cursor Chat and type: `"Check table health for orders_daily"`
### Option C — MCP with Claude Desktop
 
Add to `claude_desktop_config.json`:
 
```json
{
  "mcpServers": {
    "DQ-Agent": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "SLACK_BOT_TOKEN": "your_token",
        "SHEET_ID": "your_sheet_id"
      }
    }
  }
}
```
 
Available MCP tools:
- `get_table_health` — returns health status for a specific table FQN
- `list_recent_failures` — lists all DQ failures from the past 7 days
- `trigger_weekly_report` — runs the full LangGraph pipeline and dispatches outputs
### Option D — MCP Inspector (Testing)
 
```bash
npx -y @modelcontextprotocol/inspector python mcp_server.py
```
 
---
 
## OpenMetadata APIs Used
 
| Endpoint | Purpose |
|---|---|
| `POST /api/v1/users/login` | Authentication |
| `GET /api/v1/dataQuality/testCases/testCaseResults` | Fetch failed test results |
| `GET /api/v1/dataQuality/testCases` | Get test case types for severity scoring |
| `GET /api/v1/tables/name/{fqn}` | Fetch owner, domain, tags per table |
| `GET /api/v1/lineage/table/name/{fqn}` | Downstream lineage for blast radius |
| `GET /api/v1/domains` | Domain filtering |
| `GET /api/v1/users` | Map owner emails to Slack handles |
 
---
 
## Project Structure
 
```
dq-agent/
├── agent.py              # CLI entry point (LangGraph trigger)
├── mcp_server.py         # MCP tool server (Claude/Cursor integration)
├── config.py             # Environment variable loading
├── requirements.txt
├── .env.example
│
├── om/                   # OpenMetadata API module
│   ├── client.py         # Auth + HTTP client
│   ├── dq.py             # Fetch test cases and results
│   ├── entities.py       # Fetch owners, domains, tags
│   └── lineage.py        # Downstream lineage traversal
│
├── core/                 # Business logic
│   ├── models.py         # Pydantic data models
│   ├── aggregator.py     # Deduplicate + group failures
│   ├── scorer.py         # P1/P2/P3 severity assignment
│   └── trend.py          # Week-over-week comparison
│
├── agents/
│   └── state_graph.py    # LangGraph 5-node DAG definition
│
├── ai/
│   └── summarizer.py     # Gemini LLM summarization
│
├── outputs/
│   ├── sheets.py         # Google Sheets multi-tab writer
│   └── slack.py          # Slack Block Kit dispatcher
│
└── data/
    └── seed_om.py        # Populate fresh OM with sample DQ data
```
 
---
 
## Judging Criteria — How We Address Each
 
| Criterion | How DQ-Agent Delivers |
|---|---|
| **Potential Impact** | Eliminates 3–5 hrs/week of manual DQ reporting for every data team |
| **Creativity & Innovation** | First combination of LangGraph agentic pipeline + MCP server for OpenMetadata |
| **Technical Excellence** | Modular 5-node DAG, PII/Tier1 auto-escalation, multi-tab styled Sheet output |
| **Best Use of OpenMetadata** | Uses DQ, Lineage, Ownership, Tags, and Domains APIs — not just one endpoint |
| **User Experience** | Works via CLI, Slack, Google Sheets, Claude Desktop, and Cursor — zero manual steps |
| **Presentation Quality** | Live working demo, clean README, deployed landing page |
 
---
 
## License
 
MIT License — All code and architecture © Team DQ-Agent, 2026
 
