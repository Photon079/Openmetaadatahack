import os
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field

from langchain.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

# Import the standalone LLM Agent component
from llm_ import GeminiAgent

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

# --- 2. PYDANTIC SCHEMAS FOR LLM EXPECTED OUTPUTS ---
class ClassificationOutput(BaseModel):
    max_severity: str = Field(description="The highest severity among all failures: 'P1', 'P2', 'P3', or 'NONE'")
    classified_failures: List[Dict[str, str]] = Field(description="List of failures with assigned severities and reasoning")

class SummaryOutput(BaseModel):
    summary: str = Field(description="Executive summary and root-cause hypothesis")

# --- 3. NODE DEFINITIONS ---
def IngestorNode(state: GraphState):
    """Connects to OpenMetadata REST API. Fetches all failed test cases."""
    print("--- INGESTOR NODE ---")
    
    # Mocking an OpenMetadata fetch for the workflow
    mock_failures = [
        {"table": "dim_users", "test": "null_check_email", "status": "failed"},
        {"table": "fact_sales", "test": "freshness", "status": "failed"}
    ]
    return {
        "raw_failures": mock_failures,
        "messages": ["Fetched raw failures from OpenMetadata."]
    }

def ClassifierNode(state: GraphState):
    """Uses LLM to categorize failures into P1, P2, and P3 based on business logic."""
    print("--- CLASSIFIER NODE ---")
    if not state.get("raw_failures"):
        return {"max_severity": "NONE", "messages": ["No failures to classify."]}

    system_prompt = """
    You are a Data Quality engineer. Classify the following data quality test failures.
    P1 (Critical): Freshness failures on fact tables, revenue-related data.
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
    
    # Mocking Lineage check
    mock_lineage = {
        "fact_sales": {"downstream_dashboards": ["Exec_Revenue_Dash", "Marketing_ROI"]},
        "dim_users": {"downstream_pipelines": ["daily_user_sync"]}
    }
    
    # Calculate blast radius based on downstream dependencies
    blast_radius = sum(len(deps) for items in mock_lineage.values() for deps in items.values())
    
    return {
        "lineage_data": mock_lineage,
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
    
    # Mock API calls to external services
    print(f"\n[SLACK BLOCK KIT PREVIEW]\nAlert Level: {state.get('max_severity')}\nImpact: {state.get('blast_radius')} assets\nSummary: {state.get('summary')}\n")
    return {
        "messages": ["Dispatched alerts to Slack and Jira."]
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