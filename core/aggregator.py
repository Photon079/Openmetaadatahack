"""
Aggregation engine: deduplicates raw test case results, applies severity,
and groups failures by table, owner, and domain.

Input:  list of raw result dicts (each has a nested 'testCase' dict injected by dq.py)
Output: AggregatedReport dataclass
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .scorer import assign_severity, SEVERITY_EMOJI


@dataclass
class Incident:
    test_case_name: str
    test_case_fqn: str
    table_fqn: str
    table_name: str
    owner: Optional[str]
    domain: Optional[str]
    tags: List[str]          # New field for governance tags
    severity: str            # P1 / P2 / P3
    failure_count: int
    latest_timestamp: int    # Unix ms of most recent failure
    om_deep_link: str        # http://localhost:8585/... URL to OM entity


@dataclass
class AggregatedReport:
    incidents: List[Incident] = field(default_factory=list)
    total_failures: int = 0
    p1_count: int = 0
    p2_count: int = 0
    p3_count: int = 0
    most_impacted_domain: Optional[str] = None
    by_owner: dict = field(default_factory=dict)    # owner -> List[Incident]
    by_domain: dict = field(default_factory=dict)   # domain -> List[Incident]
    by_table: dict = field(default_factory=dict)    # table_fqn -> List[Incident]


def _extract_owner(test_case: dict) -> Optional[str]:
    """Pull a display name from the nested owner field."""
    owners = test_case.get("owners") or []
    if owners:
        return owners[0].get("displayName") or owners[0].get("name")
    owner = test_case.get("owner")
    if owner:
        return owner.get("displayName") or owner.get("name")
    return None


def _extract_domain(test_case: dict) -> Optional[str]:
    domain = test_case.get("domain")
    if domain:
        return domain.get("displayName") or domain.get("name") or domain.get("fullyQualifiedName")
    return None


def _extract_table_name(fqn: str) -> str:
    """Get the last component of a dotted FQN, e.g. 'public.orders_daily' → 'orders_daily'."""
    parts = fqn.split(".")
    # Test case FQN is: service.db.schema.table.test_name
    # Table FQN is the first 4 parts for most cases
    if len(parts) >= 2:
        return parts[-2]  # second-to-last is the table, last is the test name
    return parts[0]


def _table_fqn_from_test_fqn(test_fqn: str) -> str:
    """Strip the test-case name suffix to get the table FQN."""
    parts = test_fqn.rsplit(".", 1)
    return parts[0] if len(parts) == 2 else test_fqn


def _om_link(base_url: str, table_fqn: str) -> str:
    encoded = table_fqn.replace(".", "/")
    return f"{base_url}/table/{encoded}"


def aggregate(raw_results: list, om_base_url: str = "http://localhost:8585") -> AggregatedReport:
    """
    Takes a list of raw test result dicts (each with a nested 'testCase')
    and returns an AggregatedReport.
    """
    # Deduplicate by test case FQN — collapse multiple failures into one Incident
    incidents_map: dict[str, dict] = {}   # test_case_fqn -> accumulator

    for result in raw_results:
        tc = result.get("testCase", {})
        tc_fqn = tc.get("fullyQualifiedName", result.get("id", "unknown"))
        ts = result.get("timestamp", 0)

        if tc_fqn not in incidents_map:
            table_fqn = _table_fqn_from_test_fqn(tc_fqn)
            incidents_map[tc_fqn] = {
                "test_case_name": tc.get("name", tc_fqn),
                "test_case_fqn": tc_fqn,
                "table_fqn": table_fqn,
                "table_name": _extract_table_name(tc_fqn),
                "owner": _extract_owner(tc),
                "domain": _extract_domain(tc),
                "tags": tc.get("table_tags", []),
                "severity": assign_severity(tc),
                "failure_count": 0,
                "latest_timestamp": 0,
                "om_deep_link": _om_link(om_base_url, table_fqn),
            }

        incidents_map[tc_fqn]["failure_count"] += 1
        if ts > incidents_map[tc_fqn]["latest_timestamp"]:
            incidents_map[tc_fqn]["latest_timestamp"] = ts

    # Build Incident objects
    incidents = [Incident(**v) for v in incidents_map.values()]

    # Sort: P1 first, then by failure count descending
    severity_order = {"P1": 0, "P2": 1, "P3": 2}
    incidents.sort(key=lambda i: (severity_order[i.severity], -i.failure_count))

    # Build summary stats
    report = AggregatedReport(incidents=incidents)
    report.total_failures = sum(i.failure_count for i in incidents)
    report.p1_count = sum(1 for i in incidents if i.severity == "P1")
    report.p2_count = sum(1 for i in incidents if i.severity == "P2")
    report.p3_count = sum(1 for i in incidents if i.severity == "P3")

    # Group by domain
    domain_counts: dict[str, int] = {}
    for i in incidents:
        domain = i.domain or "Unknown"
        report.by_domain.setdefault(domain, []).append(i)
        domain_counts[domain] = domain_counts.get(domain, 0) + i.failure_count

    if domain_counts:
        report.most_impacted_domain = max(domain_counts, key=domain_counts.get)

    # Group by owner
    for i in incidents:
        owner = i.owner or "Unowned"
        report.by_owner.setdefault(owner, []).append(i)

    # Group by table
    for i in incidents:
        report.by_table.setdefault(i.table_fqn, []).append(i)

    return report
