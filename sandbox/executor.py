"""
Executes LLM-generated pandas/matplotlib code in an isolated subprocess.

This is a *basic* sandbox for step 1: it runs in a separate process (so it
can't crash or hang the main app) with a timeout and an import allowlist.
It's deliberately not bulletproof yet — no filesystem/network jail, no
resource limits beyond the timeout. In step 2 this same logic moves behind
an MCP tool boundary, which is the natural place to tighten it further
(the spec's Risks & Mitigations table calls this out explicitly).
"""

import subprocess
import sys
import tempfile
import os
import re
import uuid

ALLOWED_IMPORTS = {"pandas", "numpy"}
TIMEOUT_SECONDS = 30

_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)", re.MULTILINE)


def _check_imports(code: str) -> str | None:
    """Returns an error string if the code imports anything not on the
    allowlist, else None."""
    for match in _IMPORT_RE.finditer(code):
        root_module = match.group(1).split(".")[0]
        full_module = match.group(1)
        if root_module not in {m.split(".")[0] for m in ALLOWED_IMPORTS} and \
           full_module not in ALLOWED_IMPORTS:
            return f"Disallowed import: '{match.group(1)}'. Allowed: {sorted(ALLOWED_IMPORTS)}"
    return None


def execute_python(code: str, dataset_path: str, chart_dir: str = "charts") -> dict:
    """
    Runs `code` in a subprocess. The code can assume two variables already
    exist: `dataset_path` (str, path to the CSV) and `chart_path` (str, where
    to save a matplotlib figure via plt.savefig(chart_path) if it makes one).

    Returns a dict: {"success": bool, "stdout": str, "error": str | None,
                      "chart_path": str | None}
    """
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, f"chart_{uuid.uuid4().hex[:8]}.png")

    import_error = _check_imports(code)
    if import_error:
        return {"success": False, "stdout": "", "error": import_error, "chart_path": None}

    preamble = (
        "import sys, os\n"
        f"sys.path.insert(0, {os.getcwd()!r})\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"  # headless backend, no display needed
        "from sandbox.chart_helpers import plot_bar, plot_line, plot_pie, plot_scatter\n"
        f"dataset_path = {dataset_path!r}\n"
        f"chart_path = {chart_path!r}\n"
    )
    full_code = preamble + "\n" + code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(full_code)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "stdout": result.stdout,
                "error": result.stderr[-2000:],  # keep it short for the prompt
                "chart_path": None,
            }
        chart_result = chart_path if os.path.exists(chart_path) else None
        return {
            "success": True,
            "stdout": result.stdout,
            "error": None,
            "chart_path": chart_result,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "error": f"Execution timed out after {TIMEOUT_SECONDS}s",
            "chart_path": None,
        }
    finally:
        os.unlink(script_path)
