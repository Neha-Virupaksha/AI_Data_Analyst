🤖 AI Data Analyst

Ask questions about a CSV in plain English — get the analysis, code, chart, and explanation.

An end-to-end agentic data analysis application that converts natural-language questions into executable Python/pandas analysis using a local LLM.

✨ How it works

User Question
     ↓
  Planner
     ↓
   Coder
     ↓
  Executor
     ↓
   Critic ──→ Retry (up to 3 attempts)
     ↓
   Writer
     ↓
Chart + Plain-English Answer

The workflow is orchestrated with LangGraph and uses Ollama + Qwen2.5-Coder 7B for local LLM inference.

🚀 Key Features

🧠 Multi-agent analysis — Planner, Coder, Executor, Critic & Writer

🔄 Self-correcting workflow — failed generated code is retried with execution feedback

📊 Automatic visualizations — bar, line, pie and scatter charts

🛡️ Basic execution isolation — subprocess execution, import allowlist and 30s timeout

🗃️ Run history — SQLite stores datasets, analyses, attempts and results

🖥️ Web UI + API — Gradio dashboard backed by FastAPI

🔒 Local inference — CSV analysis can run without an external LLM API

🛠️ Tech Stack

Python · LangGraph · LangChain · Ollama · Qwen2.5-Coder · Pandas · NumPy · Matplotlib · FastAPI · Gradio · SQLite

📁 Project Structure

ai-data-analyst/
├── agents/       # Planner, Coder, Executor, Critic, Writer
├── sandbox/      # Code execution + chart helpers + schema inference
├── db/           # SQLite database layer
├── data/         # Sample CSV
├── graph.py      # LangGraph workflow
├── main.py       # FastAPI backend
├── app.py        # Gradio UI
└── run_slice.py  # CLI workflow runner

⚙️ Run Locally

git clone <YOUR_REPOSITORY_URL>
cd ai-data-analyst

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn gradio requests pillow pydantic python-multipart

Install and start Ollama, then pull the model:

ollama serve
ollama pull qwen2.5-coder:7b

Start the API:

uvicorn main:app --reload --port 8001

In another terminal:

python app.py

Then open the Gradio URL shown in the terminal.

🔌 API

Endpoint

Purpose

POST /upload

Upload a CSV and infer its schema

POST /analyze

Ask a natural-language analysis question

GET /report/{run_id}

Retrieve a completed analysis

GET /history?dataset_id=...

View previous analyses

🎯 Why this project?

The goal is to move beyond a simple "LLM → answer" application and build a traceable agentic workflow where the system:

plans → generates code → executes → validates → retries → explains.

Note: The current subprocess sandbox is a basic execution boundary, not a production-grade security sandbox.
