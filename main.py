from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agents.graph import app as workflow

load_dotenv()

app = FastAPI()


class ErrorInput(BaseModel):
    """Structured error input schema."""
    error_type: str = Field(..., description="Type of error (e.g., IndexError, TypeError)")
    message: str = Field(..., description="Error message")
    file: str = Field(..., description="File path where error occurred")
    line: int = Field(..., description="Line number where error occurred")
    stacktrace: str = Field(default="", description="Full stacktrace if available")
    service_name: str = Field(default="unknown_service", description="Service or module name")
    timestamp: str = Field(default="", description="ISO timestamp of error")


class PipelinePayload(BaseModel):
    """Pipeline request payload."""
    error: ErrorInput = Field(default=None, description="Structured error input")
    test_mode: bool = Field(default=False, description="If true, use default demo error")
    use_docker: bool = Field(default=False, description="If true, run tests inside a Docker sandbox image")


@app.post("/run-pipeline")
def run_pipeline(payload: PipelinePayload | None = None):
    """Run the healing pipeline with structured input or defaults."""
    try:
        # Prepare the initial state
        initial_state = {}
        
        if payload and payload.error:
            # Convert Pydantic model to dict for the workflow
            error_dict = payload.error.dict(exclude_none=True)
            initial_state["error_input"] = error_dict
        else:
            # Use default/test mode
            initial_state["error_input"] = None

        initial_state["use_docker"] = bool(payload.use_docker) if payload else False
        
        result = workflow.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}