"""Shared test fixtures for TraceAI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from traceai.ai_gateway import SyntheticDemoGateway
    from traceai.ai_models import AIKnowledgeDataset
    from traceai.ai_services import AIEngineeringCopilot
    from traceai.engineering_graph import EngineeringGraph
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
    from traceai.models import Requirement

    return Requirement.model_validate(valid_requirement_data)


@pytest.fixture
def sample_data_path() -> Path:
    return Path(__file__).parents[1] / "data" / "requirements.csv"


@pytest.fixture
def engineering_data_path() -> Path:
    return Path(__file__).parents[1] / "data" / "engineering_data.json"


@pytest.fixture
def ai_knowledge_path() -> Path:
    return Path(__file__).parents[1] / "data" / "ai_knowledge.json"


@pytest.fixture
def ai_knowledge(ai_knowledge_path: Path) -> AIKnowledgeDataset:
    from traceai.ai_loader import load_ai_knowledge

    return load_ai_knowledge(ai_knowledge_path)


@pytest.fixture
def engineering_graph(engineering_data_path: Path) -> EngineeringGraph:
    from traceai.engineering_graph import EngineeringGraph
    from traceai.engineering_loader import load_engineering_dataset

    return EngineeringGraph(load_engineering_dataset(engineering_data_path))


@pytest.fixture
def demo_gateway() -> SyntheticDemoGateway:
    from traceai.ai_gateway import SyntheticDemoGateway

    return SyntheticDemoGateway()


@pytest.fixture
def ai_copilot(
    ai_knowledge: AIKnowledgeDataset,
    engineering_graph: EngineeringGraph,
    demo_gateway: SyntheticDemoGateway,
) -> AIEngineeringCopilot:
    from traceai.ai_services import AIEngineeringCopilot

    return AIEngineeringCopilot(ai_knowledge, engineering_graph, demo_gateway)
