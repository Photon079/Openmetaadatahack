"""
AI Summarizer: calls Anthropic Claude to generate an executive summary
from the aggregated DQ report data.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY
from core.aggregator import AggregatedReport


def _build_prompt(report: AggregatedReport, trend: dict) -> str:
    # Build a compact JSON blob for the model
    data = {
        "total_failures": report.total_failures,
        "p1_critical": report.p1_count,
        "p2_high": report.p2_count,
        "p3_low": report.p3_count,
        "most_impacted_domain": report.most_impacted_domain,
        "top_incidents": [
            {
                "table": i.table_name,
                "test": i.test_case_name,
                "severity": i.severity,
                "failures": i.failure_count,
                "owner": i.owner,
                "trend": trend.get(i.test_case_fqn, ""),
            }
            for i in report.incidents[:5]
        ],
    }

    return (
        f"You are a data quality analyst assistant. "
        f"Below is a JSON summary of the past 7 days of data quality test failures "
        f"from our data platform. Write a concise 3-sentence executive summary "
        f"suitable for a Slack message and a Google Sheet. "
        f"Be specific about critical issues, mention owners when available, "
        f"and highlight whether things are getting better or worse. "
        f"Do not use markdown headers. Keep it under 80 words.\n\n"
        f"Data: {json.dumps(data, indent=2)}"
    )


def generate_summary(report: AggregatedReport, trend: dict) -> str:
    """
    Returns a 3-sentence AI executive summary string.
    Falls back to a rule-based summary if the API call fails.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_summary(report, trend)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": _build_prompt(report, trend)}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Warning: AI summarization failed ({e}). Using rule-based summary.")
        return _fallback_summary(report, trend)


def _fallback_summary(report: AggregatedReport, trend: dict) -> str:
    """Simple rule-based fallback when Claude is unavailable."""
    top = report.incidents[0] if report.incidents else None
    top_line = (
        f"The most critical issue is `{top.table_name}` with {top.failure_count} failures ({top.severity})."
        if top
        else "No critical failures detected this week."
    )
    trend_summary = ""
    new_count = sum(1 for v in trend.values() if "New" in v)
    worse_count = sum(1 for v in trend.values() if "Worse" in v)
    if worse_count:
        trend_summary = f" {worse_count} issue(s) are trending worse than last week."
    if new_count:
        trend_summary += f" {new_count} new issue(s) appeared this week."

    return (
        f"This week's DQ report recorded {report.total_failures} total failures — "
        f"{report.p1_count} critical (P1), {report.p2_count} high (P2), {report.p3_count} low (P3). "
        f"{top_line}{trend_summary}"
    )
