import os
import sys
from pathlib import Path
from typing import Any, Optional

from agents.config import DEFAULT_CONTEXT_LINES


class ObserverAgent:
    """Observability agent that ingests structured error input and extracts context."""
    
    def __init__(self, context_lines: int = DEFAULT_CONTEXT_LINES):
        """Initialize the observer agent.

        Args:
            context_lines: Number of lines to include before and after error line
        """
        self.context_lines = context_lines
    
    def ingest_error(self, error_input: dict[str, Any]) -> dict[str, Any]:
        """
        Ingest structured error input and extract context.
        
        Expected input schema:
        {
            "error_type": "IndexError",
            "message": "list index out of range",
            "file": "demo_app/logic.py",
            "line": 2,
            "stacktrace": "...",
            "service_name": "demo_app",  # optional
            "timestamp": "2026-05-16T10:00:00Z"  # optional
        }
        
        Returns:
            dict with formatted logs, code context, and metadata
        """
        error_type = error_input.get("error_type", "Unknown")
        message = error_input.get("message", "")
        file_path = error_input.get("file", "")
        error_line = error_input.get("line", 1)
        stacktrace = error_input.get("stacktrace", "")
        service_name = error_input.get("service_name", "unknown_service")
        
        # Format logs
        logs = self._format_logs(error_type, message, file_path, error_line, stacktrace)
        
        # Extract code context
        context_code = self._extract_code_context(file_path, error_line)
        codebase_snapshot = self._read_full_file(file_path)
        
        # Capture environment metadata
        environment_metadata = self._capture_environment()
        
        return {
            "logs": logs,
            "codebase_snapshot": codebase_snapshot,
            "context_code": context_code,
            "error_type": error_type,
            "error_message": message,
            "error_file": file_path,
            "error_line": error_line,
            "stacktrace": stacktrace,
            "service_name": service_name,
            "environment_metadata": environment_metadata,
        }
    
    def _format_logs(
        self,
        error_type: str,
        message: str,
        file_path: str,
        error_line: int,
        stacktrace: str
    ) -> str:
        """Format error logs in a structured way."""
        logs = f"{error_type}: {message}\n"
        logs += f"File: {file_path}:{error_line}\n"
        if stacktrace:
            logs += f"Stacktrace:\n{stacktrace}\n"
        return logs.strip()
    
    def _extract_code_context(self, file_path: str, error_line: int) -> str:
        """Extract code lines around the error location."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return f"File not found: {file_path}"
            
            with open(file_path_obj, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Convert to 0-indexed
            error_line_idx = max(0, error_line - 1)
            start_idx = max(0, error_line_idx - self.context_lines)
            end_idx = min(len(lines), error_line_idx + self.context_lines + 1)
            
            context = ""
            for i in range(start_idx, end_idx):
                line_num = i + 1
                marker = " >>> " if i == error_line_idx else "     "
                context += f"{line_num:4d}{marker}{lines[i]}"
            
            return context
        except Exception as e:
            return f"Error extracting context: {str(e)}"
    
    def _read_full_file(self, file_path: str) -> str:
        """Read the full content of the file."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return f"File not found: {file_path}"
            
            with open(file_path_obj, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _capture_environment(self) -> dict[str, Any]:
        """Capture environment metadata."""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "working_directory": os.getcwd(),
        }
    
    def format_for_architect(self, context: dict[str, Any]) -> str:
        """
        Format the extracted context into a readable format for the architect.
        
        This provides additional context beyond just the logs and codebase.
        """
        formatted = f"""
            Service: {context.get('service_name', 'unknown')}
            Error: {context.get('error_type', 'Unknown')} - {context.get('error_message', '')}
            File: {context.get('error_file', 'unknown')}:{context.get('error_line', '?')}
            Code Context (lines around error): {context.get('context_code', 'N/A')}
            Environment: 
                - Python: {context.get('environment_metadata', {}).get('python_version', 'unknown')}
                - Platform: {context.get('environment_metadata', {}).get('platform', 'unknown')}
        """
        return formatted.strip()
