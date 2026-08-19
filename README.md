# AI Data Analyst — Step 2: Critic + Retry Loop

Planner → Coder → Executor → Critic → (retry Coder up to 3 attempts, or) → Writer.
Every attempt (code, error, success/fail) is logged to `analyst.db` (SQLite) in the
`run_attempts` table.

If the Coder writes buggy code — like forgetting to select a column before summing,
which produces `TypeError: datetime64 type does not support operation 'sum'` — the
Critic catches the error, feeds it back to the Coder along with the broken code, and
the Coder gets another shot at fixing it. Up to 3 attempts total before giving up and
explaining the failure instead.

Still no API layer or dashboard yet — this step is still `run_slice.py` on the
command line. That's next.

## Setup

**1. Install Ollama** (if you haven't already)

```bash
brew install ollama
```

**2. Start Ollama and pull the model** (in a separate terminal tab, leave it running)

```bash
ollama serve
```

In your main terminal:

```bash
ollama pull qwen2.5-coder:7b
```

This is a ~4.7GB download. If it feels slow or your Mac struggles once we're running
the full graph, switch to the lighter quantization mentioned in the spec:

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_0
```

and change the `model=` line in `agents/llm.py` to match.

**3. Create a virtual environment and install dependencies**

```bash
cd ai-data-analyst
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run it

Make sure `ollama serve` is running in its own terminal tab, then:

```bash
python run_slice.py "What's driving the drop in Q2 revenue?"
```

This will:
1. Call the Planner to break the question into steps
2. Call the Coder to write pandas/matplotlib code
3. Run that code in a sandboxed subprocess
4. Call the Writer to summarize the result in plain English
5. Print every stage's output to your terminal, and save a chart to `charts/`

The sample dataset (`data/sample_sales.csv`) has revenue dropping in Q2 across all
regions, so this question should give the model something real to find.

## What to expect / how to debug

- First run will be slow (model loading + 3 LLM calls). Later runs should be faster
  once Ollama has the model warm.
- If the Coder writes code that errors out, you'll see `EXECUTION RESULT: FAILED: ...`
  printed — that's expected right now, since there's no retry loop yet. That's exactly
  what step 2 (Critic + retry) fixes.
- If you get an import error on `langchain_ollama`, double check `ollama serve` is
  actually running (`curl http://localhost:11434` should respond).

## Once this works

Report back what you see — especially if the Coder's code is failing a lot, since
that tells us whether qwen2.5-coder:7b needs prompt tightening before we build the
retry loop around it. Then we move to step 2: Critic node + retry loop (max 3
attempts), logging each attempt.
