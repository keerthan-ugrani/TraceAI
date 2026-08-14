"""Unit tests for non-generative configuration mismatch detection."""

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph


def test_detects_interface_contract_version_mismatch(
    engineering_graph: EngineeringGraph,
) -> None:
    mismatches = ConfigurationEngine(engineering_graph).find_mismatches("SWE-REQ-014")

    interface = next(item for item in mismatches if item.artifact_id == "ARCH-IF-006")
    assert interface.expected_version == "2.0"
    assert interface.actual_version == "2.1"
    assert "REL-005" in interface.evidence_ids


def test_detects_build_requirements_baseline_mismatch(
    engineering_graph: EngineeringGraph,
) -> None:
    mismatches = ConfigurationEngine(engineering_graph).find_mismatches("SWE-REQ-014")

    assert any(
        item.expected_version == "REQ-BL-13"
        and item.actual_version == "REQ-BL-12"
        and "BUILD-158" in item.evidence_ids
        for item in mismatches
    )


def test_fully_releasable_thread_has_no_configuration_mismatch(
    engineering_graph: EngineeringGraph,
) -> None:
    assert ConfigurationEngine(engineering_graph).find_mismatches("SWE-REQ-030") == []
