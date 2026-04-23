# 📊 DQ-Reporter — Automated Data Quality Reporting Pipeline

> **WeMakeDevs × OpenMetadata Hackathon 2026**  
> Transform raw DQ alert noise into actionable weekly reports in under 60 seconds.

---

## 🎯 What It Does

DQ-Reporter connects to your [OpenMetadata](https://open-metadata.org) instance, pulls all data quality test failures from the past 7 days, and produces:

- **Google Sheets** report with 4 tabs (Summary, All Failures, Owner Tasks, WoW Trend)
- **Slack Block Kit** digest with severity badges, @owner mentions, and deep links
- **AI executive summary** via Anthropic Claude

### Before DQ-Reporter
❌ Dozens of raw Slack alerts with no context  
❌ 3–5 hours of manual weekly spreadsheet work  
❌ No trend data, no owner mapping, no priority  

### After DQ-Reporter
✅ Full report generated in **< 60 seconds**  
✅ P1/P2/P3 severity scoring + week-over-week trend  
✅ Owners automatically surfaced and notified  

---

## ⚠️ Honest Architecture Note

**This is a pipeline, not an agent.**

The name "DQ-Agent" was aspirational. In reality this is a **linear Python pipeline** — every step runs sequentially, top to bottom, with no autonomous decision-making, no tool-calling loop, and no MCP integration.

```
fetch → aggregate → score → trend → AI summary → output
```

Claude is called **once**, at the end, only to write a plain-text summary paragraph. It has no control over the pipeline, no tool access, and no ability to act on what it reads.

What it actually is:
- ✅ A useful **automation script** that saves hours of manual work
- ✅ **AI-assisted** — Claude writes the executive summary
- ❌ Not an agent (no decision loop, no tool use)
- ❌ No MCP (Model Context Protocol) integration

---

## 🗺️ Improvements Needed (Next Steps)

### Make it a real agent
- [ ] Wrap the pipeline steps as **LLM tools** (fetch, score, summarize, post)
- [ ] Let Claude **decide** which tools to call and in what order
- [ ] Add a **feedback loop** — Claude reads the output and decides if re-fetching or re-scoring is needed

### Add MCP
- [ ] Expose OpenMetadata fetch, Sheets write, and Slack post as **MCP tools**
- [ ] Let any MCP-compatible client (Claude Desktop, etc.) drive the report generation

### Better scoring
- [ ] Current P1/P2/P3 rules are hardcoded — make them configurable per team
- [ ] Add ML-based anomaly detection instead of simple threshold rules

### Trend analysis
- [ ] Currently compares only this week vs. last week (mock data)
- [ ] Persist results to a database for real historical trending

### Scheduling
- [ ] No scheduler exists — currently must be run manually
- [ ] Add cron job / GitHub Actions workflow to auto-run every Monday morning

### Tests
- [ ] Zero unit tests currently
- [ ] Add pytest coverage for aggregator, scorer, and trend modules

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/dq-reporter && cd dq-reporter

# 2. Set up environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Copy and fill in your config
cp .env.example .env

# 4. Run in mock mode — no live services needed
python agent.py --mock
```

---

## ⚙️ Configuration

| Variable | Description | Required |
|---|---|---|
| `OM_BASE_URL` | OpenMetadata URL (default: `http://localhost:8585`) | ✅ |
| `OM_USERNAME` | OM username (default: `admin`) | ✅ |
| `OM_PASSWORD` | OM password (default: `admin`) | ✅ |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to GCP service account JSON | Google Sheets |
| `SHEET_ID` | Google Spreadsheet ID | Google Sheets |
| `SLACK_BOT_TOKEN` | Slack bot token (`xoxb-...`) | Slack |
| `SLACK_CHANNEL` | Channel to post to (e.g. `#data-quality`) | Slack |
| `ANTHROPIC_API_KEY` | Anthropic API key | AI Summary |

---

## 🐳 OpenMetadata Setup

```bash
# Download and start OpenMetadata via Docker
curl -sL https://github.com/open-metadata/OpenMetadata/releases/download/1.3.1-release/docker-compose.yml -o docker-compose.yml
docker compose up -d

# Wait ~2 minutes, then open:
# http://localhost:8585   (Login: admin / admin)
```

---

## 💻 Usage

```bash
# Full run (requires live OM + configured .env)
python agent.py

# Mock mode — no credentials needed
python agent.py --mock

# Filter by domain
python agent.py --domain finance

# Skip individual outputs
python agent.py --no-sheets --no-slack --no-ai

# Combine flags
python agent.py --mock --no-sheets
```

---

## 🏗️ Architecture

```
OpenMetadata API
      ↓
  om/dq.py         — fetch test failures (last 7 days)
      ↓
  core/aggregator  — group by table / owner / domain
      ↓
  core/scorer      — assign P1 / P2 / P3 severity
      ↓
  core/trend       — week-over-week comparison
      ↓
  ai/summarizer    — Claude writes executive summary (one call)
      ↓
  ┌──────────────────┐   ┌──────────────────────────────┐
  │  outputs/sheets  │   │  outputs/slack               │
  │  4-tab report    │   │  Block Kit digest + mentions  │
  └──────────────────┘   └──────────────────────────────┘
```

```
dq-reporter/
├── agent.py          # Main orchestrator + CLI entry point
├── config.py         # Environment variable loading
│
├── om/
│   ├── client.py     # Auth + HTTP client for OM REST API
│   └── dq.py         # Fetch test cases + failures
│
├── core/
│   ├── aggregator.py # Group and deduplicate failures
│   ├── scorer.py     # P1/P2/P3 severity rules
│   └── trend.py      # Week-over-week comparison
│
├── ai/
│   └── summarizer.py # Claude summary + rule-based fallback
│
└── outputs/
    ├── sheets.py     # Google Sheets 4-tab report
    └── slack.py      # Slack Block Kit digest
```

### Severity Rules

| Severity | Rule | Emoji |
|---|---|---|
| **P1 Critical** | Schema, column, constraint, type tests | 🔴 |
| **P2 High** | Row count, freshness, volume tests | 🟠 |
| **P3 Low** | Null checks, custom checks | 🟡 |

---

## 🔌 OpenMetadata APIs Used

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/users/login` | Authentication |
| `GET /api/v1/dataQuality/testCases` | List all test cases |
| `GET /api/v1/dataQuality/testCases/{fqn}/testCaseResult` | Per-test failure results |
| `GET /api/v1/domains` | Domain listing |
| `GET /api/v1/users` | Owner lookup |

---

## 📦 Dependencies

```
requests                  # OpenMetadata REST API calls
python-dotenv             # .env configuration
slack-sdk                 # Slack Block Kit messages
google-api-python-client  # Google Sheets API v4
google-auth               # GCP service account auth
anthropic                 # Claude AI summarization
```

---

## 🏆 Hackathon Submission

- **Event**: WeMakeDevs × OpenMetadata Hackathon 2026
- **Submission**: https://forms.gle/JHc3YGmaPhsDeiHXA

---
