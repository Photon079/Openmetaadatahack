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


def main():
    args = parse_args()

    print("\n" + "═" * 60)
    print("  🛡️  DQ-Agent (LangGraph)  |  Weekly Data Quality Report")
    print("═" * 60 + "\n")

    from langchain.messages import HumanMessage
    from agents.state_graph import dq_agent_workflow
    
    # Configure the run
    run_config = {
        "mock": args.mock,
        "domain": args.domain,
        "om_base_url": OM_HOST,
        "no_sheets": args.no_sheets,
        "no_slack": args.no_slack
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
        print("Starting LangGraph Workflow...")
        final_state = dq_agent_workflow.invoke(initial_state)
        
        print("\n--- FINAL STATE MESSAGES ---")
        for msg in final_state["messages"]:
            if isinstance(msg, HumanMessage):
                print(f"Trigger: {msg.content}")
            else:
                print(f"Action: {msg}")
                
        print("\n" + "═" * 60)
        print("✅  DQ-Agent LangGraph run complete!")
        print("═" * 60 + "\n")
                
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")



if __name__ == "__main__":
    main()
