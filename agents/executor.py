from agents.state import GraphState
from sandbox.executor import execute_python


def executor_node(state: GraphState) -> dict:
    result = execute_python(state["code"], state["dataset_path"])
    if result["success"]:
        return {
            "execution_result": result["stdout"],
            "execution_error": None,
            "chart_path": result["chart_path"],
        }
    else:
        return {
            "execution_result": None,
            "execution_error": result["error"],
            "chart_path": None,
        }
