import re

from agents.llm import llm
from agents.state import GraphState


def suggest_chart_type(question: str) -> str:
    """Deterministically picks which chart_helpers function fits a question, based
    on keywords. This exists because leaving chart-type choice entirely up to the
    model doesn't work reliably in practice — a 7B model tends to default to
    plot_bar regardless of the question, since that's likely the most common
    pattern in its training data. Overriding this with a rule the model MUST
    follow (see coder_node) is far more reliable than a soft suggestion."""
    q = question.lower()

    scatter_kw = ["correlat", "relationship between", " vs ", "versus", "outlier",
                  "impact of", "effect of", "influence of", "association between"]
    if any(kw in q for kw in scatter_kw):
        return "plot_scatter"

    line_kw = ["trend", "over time", "time series", "monthly", "month-over-month",
               "month over month", "year-over-year", "year over year", "weekly",
               "daily", "yearly", "progression", "by month", "by quarter", "by year",
               "by week", "growth", "changed over", "each month", "each quarter"]
    if any(kw in q for kw in line_kw):
        return "plot_line"

    pie_kw = ["share of", "proportion", "percentage of", "breakdown of",
              "composition", "split between", "distribution of", "makeup of",
              "contribution of"]
    if any(kw in q for kw in pie_kw):
        return "plot_pie"

    return "plot_bar"


CODER_PROMPT = """You are a Python data analysis coder. Write pandas code implementing \
the plan below.

Rules:
- Two variables already exist in scope: `dataset_path` (str, CSV path) and `chart_path` \
(str, where the chart must be saved). Do NOT redefine them.
- Load the data with: df = pd.read_csv(dataset_path)
- pandas is already imported as pd. Only import numpy if you need it.
- Print the key numeric result(s) with print() so they can be captured as output.
- You MUST always create exactly one chart, by calling ONE of these pre-styled helper \
functions that are already available in scope. Do NOT write your own matplotlib code and \
do NOT import matplotlib — call one of these instead:

    plot_bar(categories, values, title, xlabel, ylabel, chart_path)
        For comparing a metric across categories. If `values` contains negative numbers \
(e.g. a change/difference), bars are automatically colored green (positive) / red \
(negative) with a zero line — you don't need to do any of that yourself.

    plot_line(x, y, title, xlabel, ylabel, chart_path)
        For a trend over time or any ordered sequence.

    plot_pie(labels, values, title, chart_path)
        For parts of a whole — only use this if there are 5 or fewer categories.

    plot_scatter(x, y, title, xlabel, ylabel, chart_path)
        For the relationship/correlation between two numeric variables, or for spotting \
outliers (e.g. one variable vs another, like compensation vs performance rating).

  THESE ARE THE ONLY FOUR CHART FUNCTIONS THAT EXIST. There is no plot_boxplot, plot_hist, \
plot_box, plot_heatmap, or anything else — do not call any function name other than the \
four listed above.
  FOR THIS SPECIFIC QUESTION, YOU MUST CALL {required_chart_fn} — this has already been \
determined to be the right chart type for this question, so use it even if you would \
otherwise have picked a different one.
  Always pass `chart_path` (the variable already in scope) as the last argument. If a \
value is a pandas Series/Index, convert it to a plain list first, e.g. list(my_series) \
or my_series.tolist().
- After groupby() or pivot(), aggregate/select only the numeric column(s) you actually \
need (e.g. df.groupby([...])['revenue'].sum(), not df.groupby([...]).sum()) — summing \
non-numeric columns like dates raises a TypeError.
- After pivot(columns=...), the resulting column labels keep the ORIGINAL dtype of that \
column. If you pivot on an integer column (e.g. a quarter column made with .dt.quarter), \
the resulting columns are integers like 1, 2 — not strings like 'Q1', 'Q2'. Don't assume \
string labels after a pivot unless you cast or rename the columns first.
- When bucketing/categorizing numeric values into groups (e.g. High/Medium/Low performance, \
or price tiers), use pd.cut() with explicit bins, or np.select() with explicit conditions \
and a default, or a plain function with if/elif/else that ends in a fallback else branch. \
Do NOT use next(... for ... if condition) to pick a matching category — if no condition \
matches (e.g. a NaN value, or a value outside every range you defined), next() with no \
default raises StopIteration and crashes the whole script. If you do use next(), always \
give it a default: next((...), default_value).
- Output ONLY the Python code, no markdown fences, no explanation.

Dataset schema:
{schema_info}

Plan:
{plan}
"""

RETRY_SUFFIX = """

Your previous attempt failed. Fix the bug — don't just restate the same approach.

Previous code:
{previous_code}

Error it produced:
{previous_error}
"""

HALLUCINATED_FUNCTION_HINT = """

IMPORTANT: the error above is a NameError for a plotting function that doesn't exist. \
Remember, the ONLY chart functions available are plot_bar, plot_line, plot_pie, and \
plot_scatter — nothing else. Re-read the plan and pick the closest match from those \
four (for correlations or outliers, use plot_scatter), instead of calling a function \
name that isn't one of those four.
"""

STOPITERATION_HINT = """

IMPORTANT: the error above is a StopIteration, almost always from using next(...) with no \
default to pick a category/bucket, where some value (often NaN or an edge case) didn't \
match any condition. Rewrite that logic using pd.cut() with explicit bins, np.select() with \
a default, or an if/elif/else chain with a final else — not a bare next(generator).
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def coder_node(state: GraphState) -> dict:
    required_chart_fn = suggest_chart_type(state["question"])
    prompt = CODER_PROMPT.format(
        schema_info=state["schema_info"], plan=state["plan"], required_chart_fn=required_chart_fn
    )

    is_retry = state.get("retry_count", 0) > 0
    if is_retry:
        error_text = state.get("execution_error") or state.get("critic_reason") or "unknown error"
        prompt += RETRY_SUFFIX.format(
            previous_code=state.get("code", ""), previous_error=error_text
        )
        if "NameError" in error_text and "plot_" in error_text:
            prompt += HALLUCINATED_FUNCTION_HINT
        elif "StopIteration" in error_text:
            prompt += STOPITERATION_HINT

    response = llm.invoke(prompt)
    code = _strip_code_fences(response.content)
    # Coder always needs pandas; guarantee the import is present even if the
    # model forgot it, since we told it pd "might already be imported".
    if "import pandas" not in code:
        code = "import pandas as pd\n" + code
    # Same guarantee for numpy: the model is told it CAN use np. but must
    # import it itself, and — as observed — sometimes uses np.where/np.select
    # and simply forgets the import. Add it automatically rather than relying
    # on a retry to catch a mistake we can just prevent outright.
    if re.search(r"\bnp\.", code) and not re.search(r"^\s*import numpy", code, re.MULTILINE):
        code = "import numpy as np\n" + code

    return {"code": code, "retry_count": state.get("retry_count", 0) + 1}
