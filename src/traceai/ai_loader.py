"""Validated persistence adapter for the synthetic AI knowledge dataset."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from traceai.ai_models import AIKnowledgeDataset
from traceai.exceptions import DataValidationError


def load_ai_knowledge(path: Path) -> AIKnowledgeDataset:
    if not path.is_file():
        raise DataValidationError(f"AI knowledge dataset does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return AIKnowledgeDataset.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"AI knowledge dataset is not valid JSON: {exc}") from exc
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise DataValidationError(f"AI knowledge validation failed: {details}") from exc
