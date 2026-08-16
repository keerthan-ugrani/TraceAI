"""Tests for the validated synthetic AI knowledge adapter."""

from pathlib import Path

import pytest

from traceai.ai_loader import load_ai_knowledge
from traceai.exceptions import DataValidationError


def test_loads_complete_synthetic_ai_knowledge(ai_knowledge_path: Path) -> None:
    dataset = load_ai_knowledge(ai_knowledge_path)

    assert dataset.data_classification == "SYNTHETIC"
    assert dataset.requirement("SWE-REQ-014").status == "APPROVED"
    assert dataset.engineering_log("LOG-IT-045").test_id == "IT-045"
    assert dataset.test_context("SWE-REQ-014").interface_contracts


def test_rejects_missing_ai_knowledge_file(tmp_path: Path) -> None:
    with pytest.raises(DataValidationError, match="does not exist"):
        load_ai_knowledge(tmp_path / "missing.json")


def test_rejects_invalid_ai_knowledge_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(DataValidationError, match="not valid JSON"):
        load_ai_knowledge(path)
