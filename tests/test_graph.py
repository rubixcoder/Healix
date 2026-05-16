import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.graph import HealixState, should_retry, observer_node, architect_node, executor_node


def create_test_state(**overrides):
    """Create a complete test state with all required fields."""
    state = {
        "logs": "error",
        "codebase_snapshot": "code",
        "suggested_fix": "fix",
        "test_results": "failed",
        "retry_count": 0,
        "is_resolved": False,
        "error_input": None,
        "error_type": "IndexError",
        "error_message": "list index out of range",
        "error_file": "test.py",
        "error_line": 1,
        "stacktrace": "",
        "service_name": "test_service",
        "environment_metadata": {},
        "context_code": "code",
    }
    state.update(overrides)
    return state


def test_should_retry_returns_architect_when_not_resolved_and_under_max_retries():
    """Test that graph routes back to architect on test failure if under max retries."""
    state = create_test_state(retry_count=1, is_resolved=False)
    result = should_retry(state)
    assert result == "architect"


def test_should_retry_returns_end_when_resolved():
    """Test that graph ends when fix is resolved."""
    state = create_test_state(retry_count=1, is_resolved=True)
    result = should_retry(state)
    assert result == "end"


def test_should_retry_returns_end_when_max_retries_exceeded():
    """Test that graph ends when max retries (3) are exceeded."""
    state = create_test_state(retry_count=3, is_resolved=False)
    result = should_retry(state)
    assert result == "end"


def test_executor_node_increments_retry_count():
    """Test that executor increments the retry counter."""
    state = create_test_state(
        suggested_fix="def fixed(): pass",
        test_results="",
        retry_count=1,
        is_resolved=False
    )
    
    with patch("agents.graph.run_demo_tests") as mock_run_tests:
        mock_run_tests.return_value = {
            "status": "failed",
            "stdout": "FAILED test",
            "stderr": "",
        }
        
        result = executor_node(state)
        
        # retry_count should be incremented from 1 to 2
        assert result["retry_count"] == 2
        assert result["is_resolved"] is False
        assert "FAILED test" in result["test_results"]


def test_observer_node_initializes_state():
    """Test that observer node initializes the state correctly."""
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "code content"
        
        result = observer_node({"error_input": None})
        
        assert result["retry_count"] == 0
        assert result["is_resolved"] is False
        assert result["test_results"] == ""
        assert "IndexError" in result["logs"]


def test_observer_node_with_structured_input():
    """Test that observer node uses structured input when provided."""
    error_input = {
        "error_type": "TypeError",
        "message": "unsupported operand type",
        "file": "demo_app/logic.py",
        "line": 5,
        "service_name": "test_service",
    }
    
    state = create_test_state(error_input=error_input)
    result = observer_node(state)
    
    assert result["error_type"] == "TypeError"
    assert result["error_message"] == "unsupported operand type"
    assert result["error_line"] == 5
    assert result["service_name"] == "test_service"
    assert "TypeError" in result["logs"]

