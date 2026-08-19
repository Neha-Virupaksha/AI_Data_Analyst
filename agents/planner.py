from agents.llm import llm
from agents.state import GraphState

PLANNER_PROMPT = """You are a data analysis planner. Given a user's question and the \
schema of a CSV dataset, break the question into a short, concrete step-by-step plan \
a data analyst could follow with pandas. Do not write code — just the plan.

Question: {question}

Dataset schema:
{schema_info}

Respond with a numbered list of 2-5 concrete steps (e.g. "1. Parse date column and \
extract quarter. 2. Group by quarter and region, sum revenue. 3. Compare Q1 vs Q2 totals \
per region."). Be specific about which columns to use.
"""


def planner_node(state: GraphState) -> dict:
    prompt = PLANNER_PROMPT.format(
        question=state["question"], schema_info=state["schema_info"]
    )
    response = llm.invoke(prompt)
    return {"plan": response.content}
