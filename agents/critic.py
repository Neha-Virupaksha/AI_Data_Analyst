"""
Critic agent: decides whether an execution result is good enough to hand to the
Writer, or whether the Coder should retry.

For now this is heuristic, not LLM-based: execution errors and obviously-empty
results are easy to catch deterministically and don't need to burn an extra LLM
call (important on 8GB RAM, where every call has real latency). The spec's
Risks table flags that Critic judgment can be inconsistent — if we later find
heuristics aren't catching "looks wrong but technically ran" cases (e.g. an
all-NaN column, a suspiciously empty groupby), the fix per the spec is to
hand-write 10-15 labeled (code, result, verdict) examples and test an
LLM-based Critic against them before trusting it live, rather than guessing.
"""

from agents.state import GraphState
from db.database import log_attempt

MAX_ATTEMPTS = 3


def critic_node(state: GraphState) -> dict:
    attempt_number = state["retry_count"]  # coder_node already incremented this
    code = state["code"]

    if state.get("execution_error"):
        passed = False
        reason = state["execution_error"]
    elif not (state.get("execution_result") or "").strip():
        passed = False
        reason = "Execution succeeded but printed no output — nothing to summarize."
    elif not state.get("chart_path"):
        passed = False
        reason = (
            "Execution succeeded but no chart was saved. You must call "
            "plt.savefig(chart_path) — add a chart (bar/line/etc, whatever fits the result)."
        )
    else:
        passed = True
        reason = ""

    log_attempt(
        run_id=state["run_id"],
        attempt_number=attempt_number,
        code=code,
        error=None if passed else reason,
        succeeded=passed,
    )

    return {"critic_passed": passed, "critic_reason": reason}


def route_after_critic(state: GraphState) -> str:
    if state["critic_passed"]:
        return "proceed"
    if state["retry_count"] >= MAX_ATTEMPTS:
        return "proceed"  # out of attempts — Writer will explain the failure
    return "retry"
