"""
Gradio dashboard on top of the FastAPI backend (main.py). Run the API first:
    uvicorn main:app --reload
Then, in a separate terminal tab (same venv):
    python app.py

Note on "streaming" (spec section 9): the current /analyze endpoint is a single
blocking call that returns the final result, not incremental stage updates. True
step-by-step streaming ("Planning... Writing code... Running...") would need
/analyze to stream via Server-Sent Events using LangGraph's .stream() method
instead of .invoke(). I kept this simpler for now — Gradio shows its own
built-in loading spinner while the request is in flight — and flagging this as
a good candidate for a later pass rather than silently downgrading the spec.
"""

import gradio as gr
import requests
from io import BytesIO
from PIL import Image

API_BASE = "http://localhost:8001"


def _fetch_chart(chart_url: str | None):
    """Downloads the chart ourselves and returns a PIL Image, rather than handing
    gr.Image a localhost URL — Gradio 5's built-in SSRF protection (safehttpx)
    rejects 'localhost' as a hostname, so passing the URL directly fails with
    'Hostname localhost failed validation'."""
    if not chart_url:
        return None
    try:
        resp = requests.get(chart_url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None


def upload_csv(file):
    if file is None:
        return None, "No file uploaded.", "No dataset uploaded yet."

    with open(file, "rb") as f:
        filename = file.split("/")[-1]
        resp = requests.post(f"{API_BASE}/upload", files={"file": (filename, f, "text/csv")})

    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        return None, f"Upload failed: {detail}", "No dataset uploaded yet."

    data = resp.json()
    status = f"Uploaded successfully. dataset_id: {data['dataset_id']}"
    return data["dataset_id"], data["schema"], status


def ask_question(dataset_id, question):
    if not dataset_id:
        return "Upload a CSV first (Upload tab).", "", None, ""
    if not question or not question.strip():
        return "Type a question first.", "", None, ""

    try:
        resp = requests.post(
            f"{API_BASE}/analyze",
            json={"dataset_id": dataset_id, "question": question},
            timeout=600,  # generous — local 7B models can be slow, especially with retries
        )
    except requests.exceptions.ConnectionError:
        return ("Couldn't reach the API. Is `uvicorn main:app --reload` running "
                "in another terminal tab?"), "", None, ""

    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text)
        return f"Error: {detail}", "", None, ""

    data = resp.json()
    chart = _fetch_chart(f"{API_BASE}{data['chart_url']}") if data.get("chart_url") else None
    plan_display = f"{data['plan']}\n\n(attempts used: {data['retry_count']}, status: {data['status']})"
    return plan_display, data["code"], chart, data["summary"]


def refresh_history(dataset_id):
    if not dataset_id:
        return []
    resp = requests.get(f"{API_BASE}/history", params={"dataset_id": dataset_id})
    if resp.status_code != 200:
        return []
    runs = resp.json()
    rows = []
    for r in runs:
        # created_at is stored as ISO 8601; show just date + time, not the
        # full microsecond timestamp — easier to scan at a glance
        ts = r["created_at"].split(".")[0].replace("T", " ")
        has_chart = "Yes" if r.get("chart_path") else "No"
        rows.append([ts, r["question"], r["status"], r["retry_count"], has_chart, r["id"]])
    return rows


def view_run(evt: gr.SelectData, table_data):
    # gr.Dataframe passes callbacks a pandas DataFrame, not the list of lists
    # refresh_history() returned — indexing it like a list (table_data[i]) looks
    # up a *column* named i and throws a KeyError, which is why row clicks did
    # nothing before. Handle both shapes defensively.
    row_idx = evt.index[0]
    try:
        if hasattr(table_data, "iloc"):
            run_id = str(table_data.iloc[row_idx, 5])
        else:
            run_id = table_data[row_idx][5]
    except Exception:
        return "Couldn't identify which run was clicked.", "", None, ""

    resp = requests.get(f"{API_BASE}/report/{run_id}")
    if resp.status_code != 200:
        return "Couldn't load this run.", "", None, ""
    data = resp.json()
    chart = _fetch_chart(f"{API_BASE}{data['chart_url']}") if data.get("chart_url") else None
    return data["plan"], data["final_code"], chart, data["summary"]


with gr.Blocks(title="AI Data Analyst") as demo:
    gr.Markdown("# AI Data Analyst")
    gr.Markdown("Upload a CSV, ask a question in plain English, get a chart and an explanation.")

    dataset_id_state = gr.State(None)

    with gr.Tab("Upload"):
        file_input = gr.File(label="CSV file", file_types=[".csv"])
        upload_btn = gr.Button("Upload", variant="primary")
        upload_status = gr.Textbox(label="Status", value="No dataset uploaded yet.", interactive=False)
        schema_output = gr.Textbox(label="Detected schema", lines=10, interactive=False)

        upload_btn.click(
            fn=upload_csv,
            inputs=[file_input],
            outputs=[dataset_id_state, schema_output, upload_status],
        )

    with gr.Tab("Chat"):
        question_input = gr.Textbox(
            label="Your question", placeholder="e.g. What's driving the drop in Q2 revenue?"
        )
        ask_btn = gr.Button("Analyze", variant="primary")
        with gr.Row():
            with gr.Column():
                plan_output = gr.Textbox(label="Plan", lines=6, interactive=False)
                code_output = gr.Code(label="Generated code", language="python", interactive=False)
            with gr.Column():
                chart_output = gr.Image(label="Chart", interactive=False)
                summary_output = gr.Textbox(label="Summary", lines=4, interactive=False)

        ask_btn.click(
            fn=ask_question,
            inputs=[dataset_id_state, question_input],
            outputs=[plan_output, code_output, chart_output, summary_output],
        )

    with gr.Tab("History") as history_tab:
        refresh_btn = gr.Button("Refresh history")
        history_table = gr.Dataframe(
            headers=["Created at", "Question", "Status", "Retries", "Has chart", "Run ID"],
            interactive=False,
            wrap=True,
        )
        gr.Markdown("Click a row above to load that run's details below.")
        with gr.Row():
            with gr.Column():
                hist_plan = gr.Textbox(label="Plan", lines=6, interactive=False)
                hist_code = gr.Code(label="Code", language="python", interactive=False)
            with gr.Column():
                hist_chart = gr.Image(label="Chart", interactive=False)
                hist_summary = gr.Textbox(label="Summary", lines=4, interactive=False)

        refresh_btn.click(fn=refresh_history, inputs=[dataset_id_state], outputs=[history_table])
        history_tab.select(fn=refresh_history, inputs=[dataset_id_state], outputs=[history_table])
        history_table.select(
            fn=view_run, inputs=[history_table], outputs=[hist_plan, hist_code, hist_chart, hist_summary]
        )


if __name__ == "__main__":
    demo.launch()
