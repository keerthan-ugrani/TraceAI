"""Atomic persistence for validated AI enhancement reports."""

from pathlib import Path

from pydantic import BaseModel

from traceai.reporting import _atomic_write


def write_ai_report(report: BaseModel, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(output_path, report.model_dump_json(indent=2) + "\n")
    return output_path
