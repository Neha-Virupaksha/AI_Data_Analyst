"""
API layer around the LangGraph pipeline. Run with:
    uvicorn main:app --reload

Endpoints (per the spec, section 8):
    POST /upload            - accepts a CSV, returns dataset_id + inferred schema
    POST /analyze            - accepts dataset_id + question, runs the graph, returns the result
    GET  /report/{run_id}     - returns the full stored run (plan, code, chart, summary)
    GET  /history?dataset_id= - returns past runs for a dataset
"""

import json
import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db.database import (
    init_db,
    create_dataset,
    get_dataset,
    create_run,
    finalize_run,
    get_run,
    list_runs,
    list_attempts,
)
from sandbox.schema import get_schema
from graph import build_graph

UPLOAD_DIR = "uploads"
CHART_DIR = "charts"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

app = FastAPI(title="AI Data Analyst")
app.mount("/charts", StaticFiles(directory=CHART_DIR), name="charts")

# Built once at startup and reused across requests — LangGraph graphs are
# stateless between invocations, so this is safe to share.
_graph = build_graph()


@app.on_event("startup")
def on_startup():
    init_db()


class AnalyzeRequest(BaseModel):
    dataset_id: str
    question: str


def _chart_url(chart_path: str | None) -> str | None:
    if not chart_path:
        return None
    return f"/charts/{os.path.basename(chart_path)}"


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are supported right now")

    dataset_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{dataset_id}.csv")

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        schema_info = get_schema(dest_path)
    except Exception as e:
        os.remove(dest_path)
        raise HTTPException(400, f"Couldn't read this as a CSV: {e}")

    create_dataset(dest_path, schema_info, dataset_id=dataset_id)

    return {"dataset_id": dataset_id, "schema": schema_info}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    dataset = get_dataset(req.dataset_id)
    if not dataset:
        raise HTTPException(404, "dataset_id not found — upload a CSV first via /upload")

    schema_info = json.loads(dataset["schema_json"])["raw"]
    run_id = create_run(req.dataset_id, req.question)

    initial_state = {
        "question": req.question,
        "dataset_path": dataset["filename"],
        "schema_info": schema_info,
        "plan": "",
        "code": "",
        "execution_result": None,
        "execution_error": None,
        "chart_path": None,
        "summary": "",
        "retry_count": 0,
        "critic_passed": None,
        "critic_reason": None,
        "run_id": run_id,
    }

    final_state = _graph.invoke(initial_state)

    status = "success" if final_state.get("critic_passed") else "failed"
    finalize_run(
        run_id=run_id,
        plan=final_state["plan"],
        final_code=final_state["code"],
        chart_path=final_state["chart_path"],
        summary=final_state["summary"],
        retry_count=final_state["retry_count"],
        status=status,
    )

    return {
        "run_id": run_id,
        "status": status,
        "plan": final_state["plan"],
        "code": final_state["code"],
        "summary": final_state["summary"],
        "chart_url": _chart_url(final_state["chart_path"]),
        "retry_count": final_state["retry_count"],
    }


@app.get("/report/{run_id}")
def report(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "run_id not found")

    return {
        **run,
        "chart_url": _chart_url(run.get("chart_path")),
        "attempts": list_attempts(run_id),
    }


@app.get("/history")
def history(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(404, "dataset_id not found")

    return list_runs(dataset_id)
