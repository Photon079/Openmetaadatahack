"""
Severity scorer: assigns P1/P2/P3 to a test case based on its name / definition.

Rules (per PRD):
  P1 = schema tests  (column, schema, constraint)
  P2 = freshness / row count checks
  P3 = null checks, custom checks, everything else
"""

P1_KEYWORDS = ["schema", "column", "constraint", "type", "unique", "duplicate", "primary"]
P2_KEYWORDS = ["row", "count", "fresh", "inserted", "updated", "volume"]
P3_KEYWORDS = ["null", "not_null", "custom"]


def assign_severity(test_case: dict) -> str:
    """
    Given a raw test-case dict from the OM API, return 'P1', 'P2', or 'P3'.
    """
    name = (test_case.get("name", "") or "").lower()
    definition = (test_case.get("testDefinition", {}).get("name", "") or "").lower()
    combined = f"{name} {definition}"

    for kw in P1_KEYWORDS:
        if kw in combined:
            return "P1"

    for kw in P2_KEYWORDS:
        if kw in combined:
            return "P2"

    return "P3"


SEVERITY_EMOJI = {
    "P1": "🔴",
    "P2": "🟠",
    "P3": "🟡",
}
