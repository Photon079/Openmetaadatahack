import sys
import time
from mcp.server.fastmcp import FastMCP
from config import OM_HOST

# Import internal logic for tools
from om.client import OMClient
from om.dq import DQFetcher
from core.aggregator import aggregate

# Create an MCP server
mcp = FastMCP("DQ-Agent")

@mcp.tool()
def get_table_health(fqn: str, days_back: int = 7) -> str:
    """Gets the data quality health status of a specific table by its Fully Qualified Name (FQN)."""
    try:
        client = OMClient()
        fetcher = DQFetcher(client)
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - (days_back * 24 * 60 * 60 * 1000)
        
        # We fetch all failures and check if this table is among them.
        failures = fetcher.fetch_failed_tests(start_ts, end_ts)
        
        table_failures = []
        for fail in failures:
            tc = fail.get("testCase", {})
            tc_fqn = tc.get("fullyQualifiedName", "")
            # tc_fqn is like service.database.schema.table.test_name
            if fqn in tc_fqn:
                table_failures.append(tc.get("name", "Unknown Test"))
                
        if not table_failures:
            return f"Table {fqn} is healthy! No data quality failures found in the last 7 days."
        
        return f"Table {fqn} is experiencing failures in the following tests: {', '.join(table_failures)}."
    except Exception as e:
        return f"Error connecting to OpenMetadata: {e}"

@mcp.tool()
def list_recent_failures(domain: str = None, days_back: int = 7) -> str:
    """Lists recent data quality failures. Optionally filter by domain."""
    try:
        client = OMClient()
        fetcher = DQFetcher(client)
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - (days_back * 24 * 60 * 60 * 1000)
        
        raw_results = fetcher.fetch_failed_tests(start_ts, end_ts, domain=domain)

        if not raw_results:
            return f"No failures found recently{' for domain ' + domain if domain else ''}."
            
        report = aggregate(raw_results, om_base_url=OM_HOST)
        
        summary = []
        summary.append(f"Total Failures: {report.total_failures}")
        summary.append(f"P1: {report.p1_count} | P2: {report.p2_count} | P3: {report.p3_count}")
        
        for inc in report.incidents[:5]:
            summary.append(f"- {inc.table_fqn} failed {inc.test_case_name} ({inc.severity})")
            
        if len(report.incidents) > 5:
            summary.append(f"...and {len(report.incidents) - 5} more.")
            
        return "\n".join(summary)
    except Exception as e:
        return f"Error listing failures: {e}"

@mcp.tool()
def trigger_weekly_report(mock: bool = False, no_slack: bool = False, no_sheets: bool = False, days_back: int = 7) -> str:
    """Triggers the full LangGraph weekly report generation pipeline."""
    from langchain.messages import HumanMessage
    from agents.state_graph import dq_agent_workflow
    
    run_config = {
        "mock": mock,
        "domain": None,
        "om_base_url": OM_HOST,
        "no_sheets": no_sheets,
        "no_slack": no_slack,
        "days_back": days_back
    }
    
    initial_state = {
        "messages": [HumanMessage(content="Start weekly DQ check.")],
        "raw_failures": [],
        "classified_failures": [],
        "max_severity": "NONE",
        "lineage_data": {},
        "blast_radius": 0,
        "summary": "",
        "run_config": run_config
    }
    
    try:
        final_state = dq_agent_workflow.invoke(initial_state)
        return "Weekly Report successfully generated and dispatched! Final state summary: " + final_state.get("summary", "No summary generated.")
    except Exception as e:
        return f"Failed to generate weekly report: {e}"

if __name__ == "__main__":
    # Start the FastMCP server
    mcp.run(transport='stdio')
