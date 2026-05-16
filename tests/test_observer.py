import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.observer import ObserverAgent


def test_observer_ingest_error_basic():
    """Test basic error ingestion with structured input."""
    observer = ObserverAgent()
    
    error_input = {
        "error_type": "IndexError",
        "message": "list index out of range",
        "file": "demo_app/logic.py",
        "line": 2,
        "service_name": "demo_app",
    }
    
    result = observer.ingest_error(error_input)
    
    assert result["error_type"] == "IndexError"
    assert result["error_message"] == "list index out of range"
    assert result["error_file"] == "demo_app/logic.py"
    assert result["error_line"] == 2
    assert result["service_name"] == "demo_app"
    assert "IndexError" in result["logs"]
    assert "list index out of range" in result["logs"]


def test_observer_extracts_code_context():
    """Test that observer extracts code context around error line."""
    observer = ObserverAgent(context_lines=2)
    
    error_input = {
        "error_type": "IndexError",
        "message": "list index out of range",
        "file": "demo_app/logic.py",
        "line": 2,
    }
    
    result = observer.ingest_error(error_input)
    
    # Should have context code with line markers
    assert ">>>" in result["context_code"]  # Error line should be marked
    assert len(result["codebase_snapshot"]) > 0  # Should have code content
    assert result["error_file"] == "demo_app/logic.py"


def test_observer_captures_environment():
    """Test that environment metadata is captured."""
    observer = ObserverAgent()
    
    error_input = {
        "error_type": "RuntimeError",
        "message": "test error",
        "file": "demo_app/logic.py",
        "line": 1,
    }
    
    result = observer.ingest_error(error_input)
    
    metadata = result["environment_metadata"]
    assert "python_version" in metadata
    assert "platform" in metadata
    assert "working_directory" in metadata
    assert metadata["python_version"].count(".") == 2  # Should be X.Y.Z format


def test_observer_format_logs():
    """Test log formatting."""
    observer = ObserverAgent()
    
    logs = observer._format_logs(
        error_type="TypeError",
        message="unsupported operand type(s)",
        file_path="app/utils.py",
        error_line=42,
        stacktrace="Traceback: ..."
    )
    
    assert "TypeError" in logs
    assert "unsupported operand" in logs
    assert "app/utils.py:42" in logs
    assert "Traceback" in logs


def test_observer_format_for_architect():
    """Test formatting context for the architect agent."""
    observer = ObserverAgent()
    
    context = {
        "service_name": "payment_service",
        "error_type": "ValueError",
        "error_message": "invalid literal for int()",
        "error_file": "services/payment.py",
        "error_line": 15,
        "context_code": "15 >>>     amount = int(user_input)",
        "environment_metadata": {
            "python_version": "3.12.0",
            "platform": "linux",
        }
    }
    
    formatted = observer.format_for_architect(context)
    
    assert "payment_service" in formatted
    assert "ValueError" in formatted
    assert "services/payment.py:15" in formatted
    assert "3.12.0" in formatted


def test_observer_handles_missing_file():
    """Test observer gracefully handles missing files."""
    observer = ObserverAgent()
    
    error_input = {
        "error_type": "FileNotFoundError",
        "message": "file not found",
        "file": "nonexistent/file.py",
        "line": 1,
    }
    
    result = observer.ingest_error(error_input)
    
    assert "File not found" in result["context_code"]
    assert "Error extracting context" in result["context_code"] or "File not found" in result["context_code"]


def test_observer_context_lines_boundary():
    """Test that context extraction respects file boundaries."""
    observer = ObserverAgent(context_lines=10)
    
    error_input = {
        "error_type": "IndexError",
        "message": "list index out of range",
        "file": "demo_app/logic.py",
        "line": 1,  # First line - should not have lines before
    }
    
    result = observer.ingest_error(error_input)
    
    # Should handle gracefully without errors
    assert "context_code" in result
    assert len(result["context_code"]) > 0
