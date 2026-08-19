from agents.llm import llm
from agents.state import GraphState

WRITER_PROMPT = """You are explaining a data analysis result to a non-technical person.

Original question: {question}

Raw output from the analysis:
{execution_result}

Write a short (2-4 sentence) plain-English summary answering the question, based only \
on the numbers above. Be specific with numbers where relevant. Do not mention pandas, \
code, or dataframes.
"""


def writer_node(state: GraphState) -> dict:
    if not state.get("critic_passed", True):
        attempts = state.get("retry_count", 1)
        return {
            "summary": (
                f"I tried {attempts} time(s) but couldn't get a working analysis. "
                f"Last error: {state.get('critic_reason') or state.get('execution_error')}"
            )
        }
    prompt = WRITER_PROMPT.format(
        question=state["question"], execution_result=state["execution_result"]
    )
    response = llm.invoke(prompt)
    return {"summary": response.content}
