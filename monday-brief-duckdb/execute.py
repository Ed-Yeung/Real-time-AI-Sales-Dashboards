import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    success: bool
    stderr: str
    figure_json: str = ""
    records: list = field(default_factory=list)


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|attach|copy|create|alter|read_csv|to_csv)\b",
    re.IGNORECASE,
)


def check_script(code: str) -> str:
    if "read_only=True" not in code.replace(" ", ""):
        return "The script must open DuckDB with read_only=True."
    if "sales" not in code:
        return "The script must query the sales table."
    found = _FORBIDDEN.search(code)
    if found:
        return f"The script is not allowed to use {found.group(0)}."
    return ""


def run_generated_code(code: str, db_path: str, timeout: int = 30) -> ExecutionResult:
    blocked = check_script(code)
    if blocked:
        return ExecutionResult(False, blocked)

    workdir = tempfile.mkdtemp(prefix="brief_run_")
    script_path = os.path.join(workdir, "analysis.py")
    try:
        with open(script_path, "w", encoding="utf-8") as handle:
            handle.write(code)
        try:
            proc = subprocess.run(
                [sys.executable, script_path, os.path.abspath(db_path)],
                cwd=workdir,
                env={"PATH": os.environ.get("PATH", "")},
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(False, f"Timed out after {timeout}s")

        if proc.returncode != 0:
            return ExecutionResult(False, proc.stderr or proc.stdout or "Script failed")

        figure_path = os.path.join(workdir, "fig0.json")
        result_path = os.path.join(workdir, "result.json")
        if not os.path.exists(figure_path) or not os.path.exists(result_path):
            return ExecutionResult(False, "Script did not write fig0.json and result.json")

        with open(figure_path, encoding="utf-8") as handle:
            figure_json = handle.read()
        with open(result_path, encoding="utf-8") as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            return ExecutionResult(False, "result.json must be a list of rows")
        return ExecutionResult(True, "", figure_json, records[:50])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
