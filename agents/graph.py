import sys
from pathlib import Path
from typing import TypedDict, Any, Optional
from langgraph.graph import StateGraph, END

from agents.architect import ArchitectAgent
from agents.executor import run_demo_tests
from agents.observer import ObserverAgent


class HealixState(TypedDict):
    # Core workflow fields
    logs: str
    codebase_snapshot: str
    suggested_fix: str
    test_results: str
    retry_count: int
    is_resolved: bool
    
    # Structured input fields
    error_input: Optional[dict[str, Any]]
    error_type: str
    error_message: str
    error_file: str
    error_line: int
    stacktrace: str
    
    # Environment metadata
    service_name: str
    environment_metadata: dict[str, Any]
    context_code: str


def observer_node(state: HealixState):
    print("------OBSERVING LOGS-------")
    observer = ObserverAgent()
    
    # Check if structured error input is provided
    error_input = state.get("error_input")
    
    if error_input:
        # Use structured input to extract context
        context = observer.ingest_error(error_input)
        return {
            "logs": context["logs"],
            "codebase_snapshot": context["codebase_snapshot"],
            "context_code": context["context_code"],
            "error_type": context["error_type"],
            "error_message": context["error_message"],
            "error_file": context["error_file"],
            "error_line": context["error_line"],
            "stacktrace": context["stacktrace"],
            "service_name": context["service_name"],
            "environment_metadata": context["environment_metadata"],
            "retry_count": 0,
            "is_resolved": False,
            "test_results": "",
            "suggested_fix": "",
            "error_input": error_input,
        }
    else:
        # Fallback to default behavior for testing
        try:
            with open("demo_app/logic.py", "r", encoding="utf-8") as f:
                code = f.read()
        except FileNotFoundError:
            code = ""
        
        return {
            "logs": "IndexError: list index out of range at demo_app/logic.py:2",
            "codebase_snapshot": code,
            "context_code": code,
            "error_type": "IndexError",
            "error_message": "list index out of range",
            "error_file": "demo_app/logic.py",
            "error_line": 2,
            "stacktrace": "",
            "service_name": "demo_app",
            "environment_metadata": {},
            "retry_count": 0,
            "is_resolved": False,
            "test_results": "",
            "suggested_fix": "",
            "error_input": None,
        }


def architect_node(state: HealixState):
    print("------PLANNING FIX-------")
    agent = ArchitectAgent()
    result = agent.plan_fix(state)
    return {
        "suggested_fix": result["suggested_fix"],
    }


def executor_node(state: HealixState):
    print("----TESTING FIX------")
    project_root = Path(__file__).resolve().parent.parent
    result = run_demo_tests(project_root, suggested_fix=state.get("suggested_fix"))

    output = result["stdout"]
    if result["stderr"]:
        output += "\n" + result["stderr"]

    return {
        "test_results": output.strip(),
        "is_resolved": result["status"] == "passed",
        "retry_count": state.get("retry_count", 0) + 1,
    }


# Define routing logic
def should_retry(state: HealixState) -> str:
    """Route to architect for retry if not resolved and under max retries, else end."""
    max_retries = 3
    if not state.get("is_resolved", False) and state.get("retry_count", 0) < max_retries:
        return "architect"
    return "end"


# Build the Graph
workflow = StateGraph(HealixState)
workflow.add_node("observer", observer_node)
workflow.add_node("architect", architect_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("observer")
workflow.add_edge("observer", "architect")
workflow.add_edge("architect", "executor")
workflow.add_conditional_edges(
    "executor",
    should_retry,
    {"architect": "architect", "end": END}
)

app = workflow.compile()
