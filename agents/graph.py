import sys
from pathlib import Path
from typing import TypedDict, Any, Optional
from langgraph.graph import StateGraph, END

from agents.architect import ArchitectAgent
from agents.config import MAX_RETRIES
from agents.executor import run_demo_tests
from agents.memory import save_incident, get_similar_incidents
from agents.observer import ObserverAgent


class HealixState(TypedDict):
    # Core workflow fields
    logs: str
    codebase_snapshot: str
    suggested_fix: str
    test_results: str
    retry_count: int
    is_resolved: bool
    patch_diff: str
    patch_target_file: str
    use_docker: bool
    incident_id: Optional[int]
    similar_incidents: list[dict[str, Any]]
    
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


def _default_observer_context(use_docker: bool) -> HealixState:
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
        "patch_diff": "",
        "patch_target_file": "demo_app/logic.py",
        "incident_id": None,
        "similar_incidents": [],
        "use_docker": use_docker,
        "error_input": None,
    }


def observer_node(state: HealixState):
    print("------OBSERVING LOGS-------")
    observer = ObserverAgent()
    
    # Check if structured error input is provided
    error_input = state.get("error_input")
    
    if error_input:
        # Use structured input to extract context
        context = observer.ingest_error(error_input)
        incident_id = None
        try:
            incident_id = save_incident(
                error_input,
                context["logs"],
                context["codebase_snapshot"],
                context["environment_metadata"],
            )
        except Exception as exc:
            print(f"Memory persistence skipped: {exc}")

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
            "patch_diff": "",
            "patch_target_file": context["error_file"],
            "incident_id": incident_id,
            "similar_incidents": [],
            "use_docker": state.get("use_docker", False),
            "error_input": error_input,
        }

    return _default_observer_context(state.get("use_docker", False))


def architect_node(state: HealixState):
    print("------PLANNING FIX-------")
    similar_incidents = []
    try:
        similar_incidents = get_similar_incidents(
            state.get("error_type", ""),
            state.get("service_name", ""),
            limit=3,
        )
    except Exception as exc:
        print(f"Memory retrieval skipped: {exc}")

    state["similar_incidents"] = similar_incidents
    agent = ArchitectAgent()
    result = agent.plan_fix(state)
    return {
        "suggested_fix": result["suggested_fix"],
        "similar_incidents": similar_incidents,
    }


def executor_node(state: HealixState):
    print("----TESTING FIX------")
    project_root = Path(__file__).resolve().parent.parent
    target_file = state.get("error_file") or state.get("patch_target_file") or "demo_app/logic.py"
    use_docker = state.get("use_docker", False)
    result = run_demo_tests(
        project_root,
        suggested_fix=state.get("suggested_fix"),
        target_file=target_file,
        use_docker=use_docker,
    )

    output = result["stdout"]
    if result["stderr"]:
        output += "\n" + result["stderr"]

    return {
        "test_results": output.strip(),
        "is_resolved": result["status"] == "passed",
        "retry_count": state.get("retry_count", 0) + 1,
        "patch_diff": result.get("patch_diff", ""),
        "patch_target_file": result.get("patch_target_file", target_file),
        "use_docker": use_docker,
    }


# Define routing logic

def should_retry(state: HealixState) -> str:
    """Route to architect for retry if not resolved and under max retries, else end."""
    if not state.get("is_resolved", False) and state.get("retry_count", 0) < MAX_RETRIES:
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
