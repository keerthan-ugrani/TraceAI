"""Unit tests for bidirectional graph traversal."""

import pytest

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import ArtifactType, RelationshipType
from traceai.exceptions import ArtifactNotFoundError


def test_traversal_is_bidirectional(engineering_graph: EngineeringGraph) -> None:
    downstream = engineering_graph.neighbors(
        "SWE-REQ-014",
        relationship_types={RelationshipType.DERIVED_FROM},
    )
    upstream = engineering_graph.neighbors(
        "SYS-REQ-004",
        relationship_types={RelationshipType.DERIVED_FROM},
    )

    assert [item.id for item in downstream] == ["SYS-REQ-004"]
    assert [item.id for item in upstream] == ["SWE-REQ-014"]


def test_connected_thread_does_not_cross_unrelated_release(
    engineering_graph: EngineeringGraph,
) -> None:
    connected = engineering_graph.connected_ids("SWE-REQ-014")

    assert "REL-1.4.0" in connected
    assert "REL-1.5.0" not in connected


def test_connected_by_type_returns_stable_stage_order(
    engineering_graph: EngineeringGraph,
) -> None:
    artifacts = engineering_graph.connected_by_type(
        "SWE-REQ-014",
        {ArtifactType.SYSTEM_REQUIREMENT, ArtifactType.RELEASE},
    )

    assert artifacts[0].id == "SYS-REQ-004"
    assert {item.id for item in artifacts[1:]} == {"REL-1.4.0", "REL-1.4.1"}


def test_unknown_artifact_is_actionable(engineering_graph: EngineeringGraph) -> None:
    with pytest.raises(ArtifactNotFoundError, match="UNKNOWN-001"):
        engineering_graph.artifact("UNKNOWN-001")


def test_invalid_neighbor_direction_is_rejected(engineering_graph: EngineeringGraph) -> None:
    with pytest.raises(ValueError, match="direction"):
        engineering_graph.neighbors("SWE-REQ-014", direction="sideways")
