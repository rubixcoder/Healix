import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.architect import ArchitectAgent


class DummyResponse:
    def __init__(self, content: str):
        self.content = content


class DummyLLM:
    def invoke(self, prompt_value, **kwargs):
        return DummyResponse("  fixed code suggestion  \n")


def test_architect_plan_fix_returns_stripped_content():
    agent = ArchitectAgent(api_key="sk-test")
    agent.llm = DummyLLM()

    state = {
        "logs": "IndexError: list index out of range",
        "codebase_snapshot": "def get_item(items, index):\n    return items[index]\n",
    }

    result = agent.plan_fix(state)

    assert result["suggested_fix"] == "fixed code suggestion"
