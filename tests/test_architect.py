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
        "retry_count": 0,
        "test_results": "",
    }

    result = agent.plan_fix(state)

    assert result["suggested_fix"] == "fixed code suggestion"


def test_architect_includes_failure_context_on_retry():
    """Test that retry attempts include prior failure information."""
    agent = ArchitectAgent(api_key="sk-test")
    
    captured_prompts = []
    
    class CapturingLLM:
        def invoke(self, prompt_value, **kwargs):
            captured_prompts.append(str(prompt_value))
            return DummyResponse("fixed code suggestion")
    
    agent.llm = CapturingLLM()

    # First attempt
    state_first = {
        "logs": "IndexError: list index out of range",
        "codebase_snapshot": "def get_item(items, index):\n    return items[index]\n",
        "retry_count": 0,
        "test_results": "",
    }
    
    agent.plan_fix(state_first)
    first_prompt = captured_prompts[0]
    
    # Verify first prompt doesn't mention retry or prior failure
    assert "RETRY ATTEMPT" not in first_prompt
    assert "Previous attempt failed" not in first_prompt

    # Retry attempt
    state_retry = {
        "logs": "IndexError: list index out of range",
        "codebase_snapshot": "def get_item(items, index):\n    return items[index]\n",
        "retry_count": 1,
        "test_results": "AssertionError: expected None but got IndexError",
    }
    
    agent.plan_fix(state_retry)
    retry_prompt = captured_prompts[1]
    
    # Verify retry prompt includes context
    assert "RETRY ATTEMPT 1" in retry_prompt
    assert "Previous attempt failed" in retry_prompt
    assert "AssertionError" in retry_prompt
    assert "Why might the previous fix have failed?" in retry_prompt

