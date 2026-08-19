"""
Step 1 vertical slice test.

Usage:
    python run_slice.py "What's driving the drop in Q2?"

Runs Planner -> Coder -> Executor -> Writer once on data/sample_sales.csv
and prints each stage's output so you can see what each agent produced.
"""

import sys

from graph import build_graph
from sandbox.schema import get_schema
from db.database import init_db, upsert_dataset, create_run, finalize_run

DATASET_PATH = "data/sample_sales.csv"


def main():
    if len(sys.argv) < 2:
        question = "What's driving the drop in Q2 revenue?"
        print(f"No question given, using default: {question!r}\n")
    else:
        question = sys.argv[1]

    init_db()
    schema_info = get_schema(DATASET_PATH)
    dataset_id = upsert_dataset(DATASET_PATH, schema_info)
    run_id = create_run(dataset_id, question)

    app = build_graph()

    initial_state = {
        "question": question,
        "dataset_path": DATASET_PATH,
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

    print("Running graph (each Coder attempt calls the local model — this may take a "
          "few minutes on 8GB RAM if it needs to retry)...\n")

    final_state = app.invoke(initial_state)

    finalize_run(
        run_id=run_id,
        plan=final_state["plan"],
        final_code=final_state["code"],
        chart_path=final_state["chart_path"],
        summary=final_state["summary"],
        retry_count=final_state["retry_count"],
        status="success" if final_state.get("critic_passed") else "failed",
    )
    print(f"\n(Run logged to analyst.db — run_id: {run_id})")

    print("=" * 60)
    print("PLAN")
    print("=" * 60)
    print(final_state["plan"])

    print("\n" + "=" * 60)
    print("CODE")
    print("=" * 60)
    print(final_state["code"])

    print(f"\nAttempts used: {final_state['retry_count']}")

    print("\n" + "=" * 60)
    print("EXECUTION RESULT")
    print("=" * 60)
    if not final_state.get("critic_passed"):
        print(f"FAILED after {final_state['retry_count']} attempt(s): {final_state['critic_reason']}")
    else:
        print(final_state["execution_result"])
        if final_state["chart_path"]:
            print(f"\nChart saved to: {final_state['chart_path']}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(final_state["summary"])


if __name__ == "__main__":
    main()
