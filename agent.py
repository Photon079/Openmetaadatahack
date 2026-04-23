"""
DQ-Agent — Main entry point.

Usage:
  python agent.py                         # Full run against live OpenMetadata
  python agent.py --domain finance        # Filter by domain
  python agent.py --mock                  # Offline run with mock data (no live services needed)
  python agent.py --no-sheets             # Skip Google Sheets output
  python agent.py --no-slack              # Skip Slack output
"""

import argparse
import json
import time
import os

from config import OM_HOST


def parse_args():
    parser = argparse.ArgumentParser(description="DQ-Agent: Weekly Data Quality Report Generator")
    parser.add_argument("--prompt", type=str, help="Natural-language prompt (for demo)")
    parser.add_argument("--domain", type=str, default=None, help="Filter results by domain name")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of live OpenMetadata")
    parser.add_argument("--no-sheets", action="store_true", help="Skip Google Sheets output")
    parser.add_argument("--no-slack", action="store_true", help="Skip Slack output")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI summarization")
    return parser.parse_args()


def load_mock_data() -> list:
    mock_path = os.path.join(os.path.dirname(__file__), "data", "mock_failures.json")
    with open(mock_path) as f:
        return json.load(f)


def fetch_live_data(domain: str = None):
    from om.client import OMClient
    from om.dq import DQFetcher

    print("🔌 Connecting to OpenMetadata...")
    client = OMClient()
    print("✅ Authenticated.")

    fetcher = DQFetcher(client)
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (7 * 24 * 60 * 60 * 1000)

    print(f"📡 Fetching failed DQ tests for the last 7 days{' (domain: ' + domain + ')' if domain else ''}...")
    raw_results = fetcher.fetch_failed_tests(start_ts, end_ts, domain=domain)
    print(f"   Found {len(raw_results)} raw failure records.")
    return raw_results, client, start_ts


def main():
    args = parse_args()

    print("\n" + "═" * 60)
    print("  🛡️  DQ-Agent  |  Weekly Data Quality Report")
    print("═" * 60 + "\n")

    # ── Step 1: Fetch data ────────────────────────────────────────
    client = None
    start_ts = int(time.time() * 1000) - (7 * 24 * 60 * 60 * 1000)

    if args.mock:
        print("🧪 Running in MOCK mode — no live services required.\n")
        raw_results = load_mock_data()
    else:
        raw_results, client, start_ts = fetch_live_data(domain=args.domain)

    if not raw_results:
        print("🎉 No failures found in the last 7 days. Nothing to report!")
        return

    # ── Step 2: Aggregate ─────────────────────────────────────────
    print("\n📊 Aggregating and scoring failures...")
    from core.aggregator import aggregate
    report = aggregate(raw_results, om_base_url=OM_HOST)
    print(f"   Incidents: {len(report.incidents)} unique | "
          f"P1: {report.p1_count} | P2: {report.p2_count} | P3: {report.p3_count}")

    # ── Step 3: Trend analysis ────────────────────────────────────
    print("\n📈 Computing week-over-week trend...")
    if args.mock or client is None:
        trend = {i.test_case_fqn: "🆕 New" for i in report.incidents}
        print("   (Mock mode: all incidents marked as New)")
    else:
        from core.trend import compute_trend
        trend = compute_trend(client, report.incidents, start_ts)
        print(f"   Trend computed for {len(trend)} incidents.")

    # ── Step 4: AI Summary ────────────────────────────────────────
    ai_summary = ""
    if not args.no_ai:
        print("\n🤖 Generating AI executive summary...")
        from ai.summarizer import generate_summary
        ai_summary = generate_summary(report, trend)
        print(f"   Summary: {ai_summary[:100]}...")

    # ── Step 5: Google Sheets ─────────────────────────────────────
    sheet_url = "#"
    if not args.no_sheets:
        from config import SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON
        if not SHEET_ID or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
            print("\n⚠️  Google Sheets skipped (SHEET_ID or gcp-sa.json not configured).")
            args.no_sheets = True
        else:
            print("\n📋 Writing Google Sheets report...")
            from outputs.sheets import write_report
            sheet_url = write_report(report, trend, ai_summary)

    # ── Step 6: Slack ─────────────────────────────────────────────
    if not args.no_slack:
        from config import SLACK_BOT_TOKEN
        if not SLACK_BOT_TOKEN:
            print("\n⚠️  Slack skipped (SLACK_BOT_TOKEN not configured).")
            args.no_slack = True
        else:
            print("\n💬 Posting Slack digest...")
            from outputs.slack import post_digest
            post_digest(report, trend, sheet_url, om_base_url=OM_HOST, ai_summary=ai_summary)

    # ── Done ──────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("✅  DQ-Agent run complete!")
    print(f"   Total Failures : {report.total_failures}")
    print(f"   P1 Critical    : {report.p1_count}")
    print(f"   P2 High        : {report.p2_count}")
    print(f"   P3 Low         : {report.p3_count}")
    print(f"   Most Impacted  : {report.most_impacted_domain or 'N/A'}")
    if sheet_url != "#":
        print(f"   Sheet URL      : {sheet_url}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
