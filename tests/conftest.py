"""Shared test fixtures for TraceAI."""

from __future__ import annotations

from pathlib import Path

import pytest

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_loader import load_engineering_dataset
from traceai.models import Requirement


@pytest.fixture
def valid_requirement_data() -> dict[str, object]:
    """Return a minimal requirement that passes every Day 1 rule."""
    return {
        "requirement_id": "REQ-999",
        "title": "Authentication interlock",
        "text": "The controller shall prevent power transfer when authentication fails.",
        "component": "Charging Controller",
        "classification": "CYBERSECURITY",
        "status": "APPROVED",
        "verification_method": "TEST",
        "source": "Cybersecurity Specification",
        "revision": 1,
    }


@pytest.fixture
def valid_requirement(valid_requirement_data: dict[str, object]) -> Requirement:
    return Requirement.model_validate(valid_requirement_data)


@pytest.fixture
def sample_data_path() -> Path:
    return Path(__file__).parents[1] / "data" / "requirements.csv"


@pytest.fixture
def engineering_data_path() -> Path:
    return Path(__file__).parents[1] / "data" / "engineering_data.json"


@pytest.fixture
def engineering_graph(engineering_data_path: Path) -> EngineeringGraph:
    return EngineeringGraph(load_engineering_dataset(engineering_data_path))
