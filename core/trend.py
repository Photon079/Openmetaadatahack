"""
Trend analysis: compare this week's failure counts to last week's.

Returns a dict { test_case_fqn: trend_direction }
where trend_direction is:  '↑' | '↓' | '→' | 'NEW'
"""

from om.client import OMClient
from om.dq import DQFetcher


TREND_UP = "↑ Worse"
TREND_DOWN = "↓ Better"
TREND_FLAT = "→ Same"
TREND_NEW = "🆕 New"


def compute_trend(
    client: OMClient,
    current_incidents: list,   # list of Incident from aggregator
    current_start_ts: int,
) -> dict:
    """
    Fetches the previous 7-day window's failures and returns a trend dict.

    Args:
        client:             authenticated OMClient
        current_incidents:  list of Incident objects from this week
        current_start_ts:   start of the current window (ms)

    Returns:
        { test_case_fqn: trend_string }
    """
    prev_end_ts = current_start_ts
    prev_start_ts = current_start_ts - (7 * 24 * 60 * 60 * 1000)

    fetcher = DQFetcher(client)
    try:
        prev_raw = fetcher.fetch_failed_tests(prev_start_ts, prev_end_ts)
    except Exception as e:
        print(f"Warning: Could not fetch previous week data for trend: {e}")
        return {i.test_case_fqn: TREND_NEW for i in current_incidents}

    # Count previous week failures per test case FQN
    prev_counts: dict[str, int] = {}
    for r in prev_raw:
        tc = r.get("testCase", {})
        fqn = tc.get("fullyQualifiedName", "unknown")
        prev_counts[fqn] = prev_counts.get(fqn, 0) + 1

    trend = {}
    for incident in current_incidents:
        fqn = incident.test_case_fqn
        curr = incident.failure_count
        prev = prev_counts.get(fqn, 0)

        if prev == 0:
            trend[fqn] = TREND_NEW
        elif curr > prev:
            trend[fqn] = TREND_UP
        elif curr < prev:
            trend[fqn] = TREND_DOWN
        else:
            trend[fqn] = TREND_FLAT

    return trend
