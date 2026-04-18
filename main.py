from typing import Any

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from agents.graph import app as workflow

load_dotenv()

app = FastAPI()

@app.post("/run-pipeline")
def run_pipeline(payload: dict[str, Any] | None = None):
    try:
        result = workflow.invoke(payload or {})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result