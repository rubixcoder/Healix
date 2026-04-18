from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, END

from agents.architect import ArchitectAgent
from agents.executor import run_demo_tests


class HealixState(TypedDict):
    logs: str
    codebase_snapshot: str
    suggested_fix: str
    test_results: str
    retry_count: int
    is_resolved: bool


def observer_node(state: HealixState):
    print("------OBSERVING LOGS-------")
    try:
        with open("demo_app/logic.py", "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        code = ""

    return {
        "logs": "IndexError: list index out of range at demo_app/logic.py:1",
        "codebase_snapshot": code,
        "retry_count": 0,
        "is_resolved": False,
        "test_results": "",
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
    }


# Build the Graph
workflow = StateGraph(HealixState)
workflow.add_node("observer", observer_node)
workflow.add_node("architect", architect_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("observer")
workflow.add_edge("observer", "architect")
workflow.add_edge("architect", "executor")
workflow.add_edge("executor", END)

app = workflow.compile()
