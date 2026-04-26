import os
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field

from langchain.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

import time
import json
from om.client import OMClient
from om.dq import DQFetcher
from om.lineage import LineageFetcher

# Import the standalone LLM Agent component
from agents.llm_ import GeminiAgent

# Initialize the shared Gemini client for nodes that need reasoning
llm_agent = GeminiAgent()

# --- 1. STATE DEFINITION (Based on PRD) ---
class GraphState(TypedDict):
    """The central state object holding data as it moves through the graph nodes."""
    messages: Annotated[list, operator.add]
    raw_failures: List[Dict[str, Any]]
    classified_failures: List[Dict[str, Any]]
    max_severity: str  # Expected: "P1", "P2", "P3", or "NONE"
    lineage_data: Dict[str, Any]
    blast_radius: int
    summary: str
    run_config: Dict[str, Any] # For passing mock/domain/etc

# --- 2. PYDANTIC SCHEMAS FOR LLM EXPECTED OUTPUTS ---
class ClassifiedFailure(BaseModel):
    table_name: str = Field(description="The name of the table")
    fqn: str = Field(description="The fully qualified name (entityFQN) of the table")
    test_case: str = Field(description="The name of the test case that failed")
    severity: str = Field(description="Assigned severity: 'P1', 'P2', or 'P3'")
    reasoning: str = Field(description="Reasoning for the assigned severity")

class ClassificationOutput(BaseModel):
    max_severity: str = Field(description="The highest severity among all failures: 'P1', 'P2', 'P3', or 'NONE'")
    classified_failures: List[ClassifiedFailure] = Field(description="List of failures with assigned severities and reasoning")

class SummaryOutput(BaseModel):
    summary: str = Field(description="Executive summary and root-cause hypothesis")

# --- 3. NODE DEFINITIONS ---
def IngestorNode(state: GraphState):
    """Connects to OpenMetadata REST API. Fetches all failed test cases."""
    print("--- INGESTOR NODE ---")
    
    config = state.get("run_config", {})
    mock = config.get("mock", False)
    domain = config.get("domain")
    
    if mock:
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mock_failures.json")
        try:
            with open(path) as f:
                raw_results = json.load(f)
        except Exception as e:
            raw_results = []
            print(f"Failed to load mock data: {e}")
    else:
        try:
            client = OMClient()
            fetcher = DQFetcher(client)
            end_ts = int(time.time() * 1000)
            days_back = config.get("days_back", 7)
            start_ts = end_ts - (days_back * 24 * 60 * 60 * 1000)
            raw_results = fetcher.fetch_failed_tests(start_ts, end_ts, domain=domain or None)
        except Exception as e:
            print(f"Failed to fetch real data: {e}")
            raw_results = []

    return {
        "raw_failures": raw_results,
        "messages": [f"Fetched {len(raw_results)} raw failures from OpenMetadata."]
    }

def ClassifierNode(state: GraphState):
    """Uses LLM to categorize failures into P1, P2, and P3 based on business logic."""
    print("--- CLASSIFIER NODE ---")
    if not state.get("raw_failures"):
        return {"max_severity": "NONE", "messages": ["No failures to classify."]}

    system_prompt = """
    You are a Data Quality engineer. Classify the following data quality test failures.
    
    CRITICAL COMPLIANCE RULE:
    If a table has any tags containing "PII", "Tier1", or "Sensitive" (in the `table_tags` list), you MUST escalate its failure to P1 (Critical), regardless of what the failure actually is.
    
    P1 (Critical): Freshness failures on fact tables, revenue-related data, or any failures on PII/Tier1 tagged tables.
    P2 (High): Null checks on important dimension tables (e.g., users, products).
    P3 (Low): Minor format issues.
    Determine the maximum severity across all failures.
    """
    
    # Pass data to the generic process function
    result = llm_agent.process(
        system_prompt=system_prompt,
        user_input=state["raw_failures"],
        output_schema=ClassificationOutput
    )
    
    return {
        "classified_failures": result.classified_failures,
        "max_severity": result.max_severity,
        "messages": [f"Classified failures. Max severity: {result.max_severity}"]
    }

def InvestigatorNode(state: GraphState):
    """Autonomously fetches downstream/upstream lineage and calculates Blast Radius."""
    print("--- INVESTIGATOR NODE (Agent) ---")
    
    config = state.get("run_config", {})
    mock = config.get("mock", False)
    
    lineage_data = {}
    blast_radius = 0
    
    if mock:
        # Match keys to the mock_failures.json FQNs (or their parent tables)
        lineage_data = {
            "sample_ecommerce.ecommerce_db.public.orders_daily": [
                {"name": "Exec_Revenue_Dash", "type": "dashboard", "fqn": "dash.exec_revenue"},
                {"name": "Marketing_ROI", "type": "dashboard", "fqn": "dash.marketing_roi"}
            ],
            "sample_ecommerce.ecommerce_db.public.users": [
                {"name": "daily_user_sync", "type": "pipeline", "fqn": "pipe.user_sync"}
            ]
        }
        blast_radius = sum(len(assets) for assets in lineage_data.values())
    else:
        try:
            client = OMClient()
            lineage_fetcher = LineageFetcher(client)
            
            for failure in state.get("classified_failures", []):
                # Ensure we handle either Pydantic models or dicts depending on LLM parsing
                failure_dict = failure.dict() if hasattr(failure, "dict") else failure
                fqn = failure_dict.get("fqn")
                if fqn and fqn not in lineage_data:
                    res = lineage_fetcher.fetch_downstream_assets("table", fqn)
                    lineage_data[fqn] = res.get("impacted_assets", [])
                    blast_radius += res.get("blast_radius", 0)
        except Exception as e:
            print(f"Failed to fetch real lineage: {e}")
    
    return {
        "lineage_data": lineage_data,
        "blast_radius": blast_radius,
        "messages": [f"Investigated lineage. Blast radius calculated at {blast_radius} impacted assets."]
    }

def SummarizerNode(state: GraphState):
    """Feeds enriched data to LLM to generate executive summaries."""
    print("--- SUMMARIZER NODE ---")
    
    data_payload = {
        "failures": state.get("classified_failures", []),
        "lineage": state.get("lineage_data", {}),
        "blast_radius": state.get("blast_radius", 0)
    }
    
    system_prompt = "You are an Executive Data Engineer. Summarize the current data quality incidents, their blast radius, and provide a root-cause hypothesis."
    
    result = llm_agent.process(
        system_prompt=system_prompt,
        user_input=data_payload,
        output_schema=SummaryOutput
    )
    
    return {
        "summary": result.summary,
        "messages": ["Generated executive summary."]
    }

def DispatcherNode(state: GraphState):
    """Executes the outputs: Writes to Google Sheets, posts to Slack, creates Jira tickets."""
    print("--- DISPATCHER NODE ---")
    
    config = state.get("run_config", {})
    om_base_url = config.get("om_base_url", "http://localhost:8585")
    no_slack = config.get("no_slack", False)
    no_sheets = config.get("no_sheets", False)
    
    # 1. Aggregate raw failures
    from core.aggregator import aggregate
    report = aggregate(state.get("raw_failures", []), om_base_url=om_base_url)
    
    # 2. Override severity with LLM's classification
    llm_severities = {}
    for cf in state.get("classified_failures", []):
        cf_dict = cf.dict() if hasattr(cf, "dict") else cf
        fqn = cf_dict.get("fqn")
        if fqn:
            llm_severities[fqn] = cf_dict.get("severity")
            
    for incident in report.incidents:
        if incident.table_fqn in llm_severities:
            incident.severity = llm_severities[incident.table_fqn]
            
    # Recalculate max severity counts
    report.p1_count = sum(1 for i in report.incidents if i.severity == "P1")
    report.p2_count = sum(1 for i in report.incidents if i.severity == "P2")
    report.p3_count = sum(1 for i in report.incidents if i.severity == "P3")
    
    # 3. Post to Google Sheets
    sheet_url = "#"
    if not no_sheets:
        from outputs.sheets import write_report
        try:
            # We don't have trend in the state yet, pass empty dict
            sheet_url = write_report(report, trend={}, ai_summary=state.get("summary", ""))
            print(f"✅ Report written to Google Sheets: {sheet_url}")
        except Exception as e:
            print(f"⚠️ Failed to write to Google Sheets: {e}")
            
    # 4. Post to Slack
    if not no_slack:
        from outputs.slack import post_digest
        try:
            post_digest(report, trend={}, sheet_url=sheet_url, om_base_url=om_base_url, ai_summary=state.get("summary", ""))
            print("✅ Alert posted to Slack.")
        except Exception as e:
            print(f"⚠️ Failed to post to Slack: {e}")

    return {
        "messages": ["Dispatched alerts to Slack and Sheets."]
    }

# --- 4. ROUTING LOGIC ---
def routing_logic(state: GraphState) -> str:
    """Decides the execution path based on the highest calculated severity."""
    severity = state.get("max_severity", "NONE")
    
    # P1/P2 require full investigation via InvestigatorNode
    if severity in ["P1", "P2"]:
        return "investigate"
    # P3 skips lineage tracing and goes straight to summary
    elif severity == "P3":
        return "summarize"
    # End graph execution if no issues
    else:
        return "end"

# --- 5. GRAPH CONSTRUCTION ---
builder = StateGraph(GraphState)

# Add Nodes
builder.add_node("ingestor", IngestorNode)
builder.add_node("classifier", ClassifierNode)
builder.add_node("investigator", InvestigatorNode)
builder.add_node("summarizer", SummarizerNode)
builder.add_node("dispatcher", DispatcherNode)

# Add Edges (Following the PRD Flow)
builder.add_edge(START, "ingestor")
builder.add_edge("ingestor", "classifier")

# Conditional Routing after Classification
builder.add_conditional_edges(
    "classifier", 
    routing_logic,
    {
        "investigate": "investigator",
        "summarize": "summarizer",
        "end": END
    }
)

# Linear flow for the remaining steps
builder.add_edge("investigator", "summarizer")
builder.add_edge("summarizer", "dispatcher")
builder.add_edge("dispatcher", END)

# Compile the final graph
dq_agent_workflow = builder.compile()

if __name__ == "__main__":
    # Test execution harness
    initial_state = {
        "messages": [HumanMessage(content="Start weekly DQ check.")],
        "raw_failures": [],
        "classified_failures": [],
        "max_severity": "NONE",
        "lineage_data": {},
        "blast_radius": 0,
        "summary": ""
    }
    
    try:
        print("Starting LangGraph Workflow...")
        # Invoke processes the graph from START until it hits an END node
        final_state = dq_agent_workflow.invoke(initial_state)
        
        print("\n--- FINAL STATE MESSAGES ---")
        for msg in final_state["messages"]:
            if isinstance(msg, HumanMessage):
                print(f"Trigger: {msg.content}")
            else:
                print(f"Action: {msg}")
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        print("Ensure 'llm_agent.py' is in the same directory and GEMINI_API_KEY is exported.")