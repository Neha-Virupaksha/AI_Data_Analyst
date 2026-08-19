from typing import TypedDict, Optional


class GraphState(TypedDict):
    question: str
    dataset_path: str
    schema_info: str          # column names + dtypes + sample rows, as a string for the prompt
    plan: str
    code: str
    execution_result: Optional[str]
    execution_error: Optional[str]
    chart_path: Optional[str]
    summary: str
    retry_count: int          # number of Coder attempts made so far
    critic_passed: Optional[bool]
    critic_reason: Optional[str]
    run_id: str
