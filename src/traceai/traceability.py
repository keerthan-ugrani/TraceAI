"""Deterministic Requirement-to-Release traversal and completeness analysis."""

from __future__ import annotations

from collections import Counter

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    FindingSeverity,
    TraceabilityGap,
    TraceabilityMetrics,
    TraceStep,
)
from traceai.exceptions import TraceAIError

CORE_THREAD_TYPES = {
    ArtifactType.SYSTEM_REQUIREMENT,
    ArtifactType.SOFTWARE_REQUIREMENT,
    ArtifactType.ARCHITECTURE_COMPONENT,
    ArtifactType.ARCHITECTURE_INTERFACE,
    ArtifactType.DETAILED_DESIGN,
    ArtifactType.SOFTWARE_UNIT,
    ArtifactType.SOURCE_FILE,
    ArtifactType.COMMIT,
    ArtifactType.UNIT_TEST,
    ArtifactType.COMPONENT_TEST,
    ArtifactType.INTEGRATION_TEST,
    ArtifactType.SOFTWARE_VERIFICATION_TEST,
    ArtifactType.BUILD,
    ArtifactType.BASELINE,
    ArtifactType.RELEASE,
}


class TraceabilityEngine:
    """Own all graph truth; generative services consume but never replace it."""

    def __init__(self, graph: EngineeringGraph) -> None:
        self.graph = graph

    def get_full_trace(self, requirement_id: str) -> list[TraceStep]:
        requirement = self._software_requirement(requirement_id)
        artifacts = self.graph.connected_by_type(requirement.id, CORE_THREAD_TYPES)
        return [_to_trace_step(artifact) for artifact in artifacts]

    def find_missing_links(self, requirement_id: str) -> list[TraceabilityGap]:
        requirement = self._software_requirement(requirement_id)
        artifacts = self.graph.artifacts(self.graph.connected_ids(requirement.id))
        gaps: list[TraceabilityGap] = []

        rules: dict[ArtifactType, list[tuple[set[ArtifactType], FindingSeverity, str]]] = {
            ArtifactType.SOFTWARE_REQUIREMENT: [
                (
                    {ArtifactType.SYSTEM_REQUIREMENT},
                    FindingSeverity.MAJOR,
                    "Software requirement has no upstream system requirement.",
                ),
                (
                    {ArtifactType.ARCHITECTURE_COMPONENT},
                    FindingSeverity.CRITICAL,
                    "Software requirement has no architecture allocation.",
                ),
                (
                    {ArtifactType.SOFTWARE_VERIFICATION_TEST},
                    FindingSeverity.CRITICAL,
                    "Software requirement has no SWE.6 verification evidence.",
                ),
            ],
            ArtifactType.ARCHITECTURE_COMPONENT: [
                (
                    {ArtifactType.DETAILED_DESIGN},
                    FindingSeverity.MAJOR,
                    "Architecture component has no detailed-design realization.",
                )
            ],
            ArtifactType.DETAILED_DESIGN: [
                (
                    {ArtifactType.SOFTWARE_UNIT},
                    FindingSeverity.MAJOR,
                    "Detailed design has no implementing software unit.",
                )
            ],
            ArtifactType.SOFTWARE_UNIT: [
                (
                    {ArtifactType.DETAILED_DESIGN},
                    FindingSeverity.MAJOR,
                    "Software unit has no detailed-design link.",
                ),
                (
                    {ArtifactType.SOURCE_FILE},
                    FindingSeverity.CRITICAL,
                    "Software unit has no source-file implementation.",
                ),
                (
                    {ArtifactType.UNIT_TEST},
                    FindingSeverity.CRITICAL,
                    "Software unit has no unit-verification evidence.",
                ),
            ],
            ArtifactType.SOURCE_FILE: [
                (
                    {ArtifactType.COMMIT},
                    FindingSeverity.MAJOR,
                    "Source file has no controlling commit.",
                )
            ],
            ArtifactType.BUILD: [
                (
                    {ArtifactType.BASELINE},
                    FindingSeverity.CRITICAL,
                    "Build has no configuration baseline.",
                )
            ],
            ArtifactType.RELEASE: [
                (
                    {ArtifactType.BASELINE},
                    FindingSeverity.CRITICAL,
                    "Release has no approved configuration baseline.",
                )
            ],
        }

        for artifact in artifacts:
            for expected_types, severity, message in rules.get(artifact.type, []):
                if self.graph.has_neighbor(artifact.id, artifact_types=expected_types):
                    continue
                gaps.append(
                    TraceabilityGap(
                        severity=severity,
                        artifact_id=artifact.id,
                        message=message,
                        expected_artifact_type=sorted(expected_types, key=str)[0],
                        evidence_ids=[artifact.id],
                    )
                )
        return sorted(gaps, key=lambda gap: (_severity_order(gap.severity), gap.artifact_id))

    def find_failed_nodes(self, requirement_id: str) -> list[TraceStep]:
        self._software_requirement(requirement_id)
        artifacts = self.graph.artifacts(self.graph.connected_ids(requirement_id))
        return [
            _to_trace_step(artifact)
            for artifact in artifacts
            if artifact.status in {ArtifactStatus.FAIL, ArtifactStatus.BLOCKED}
        ]

    def calculate_traceability_coverage(self, requirement_id: str) -> TraceabilityMetrics:
        trace = self.get_full_trace(requirement_id)
        gaps = self.find_missing_links(requirement_id)
        present_types = {step.artifact_type for step in trace}
        expected_stage_groups = {
            "requirement_to_architecture": {ArtifactType.ARCHITECTURE_COMPONENT},
            "architecture_to_design": {ArtifactType.DETAILED_DESIGN},
            "design_to_software_unit": {ArtifactType.SOFTWARE_UNIT},
            "software_unit_to_unit_verification": {ArtifactType.UNIT_TEST},
            "requirement_to_software_verification": {ArtifactType.SOFTWARE_VERIFICATION_TEST},
            "requirement_to_release": {
                ArtifactType.BUILD,
                ArtifactType.BASELINE,
                ArtifactType.RELEASE,
            },
        }
        stage_coverage = {
            name: round(100 * len(types & present_types) / len(types), 1)
            for name, types in expected_stage_groups.items()
        }

        connected_ids = self.graph.connected_ids(requirement_id)
        controlled_links = sum(
            relationship.source_id in connected_ids and relationship.target_id in connected_ids
            for relationship in self.graph.dataset.relationships
        )
        overall = (
            100.0
            if controlled_links + len(gaps) == 0
            else 100 * controlled_links / (controlled_links + len(gaps))
        )

        verification = [
            step
            for step in trace
            if step.artifact_type
            in {
                ArtifactType.UNIT_TEST,
                ArtifactType.COMPONENT_TEST,
                ArtifactType.INTEGRATION_TEST,
                ArtifactType.SOFTWARE_VERIFICATION_TEST,
            }
        ]
        status_counts = Counter(step.status for step in verification)
        verification_percent = (
            100.0 * status_counts[ArtifactStatus.PASS] / len(verification) if verification else 0.0
        )
        return TraceabilityMetrics(
            overall_coverage_percent=round(overall, 1),
            verification_percent=round(verification_percent, 1),
            stage_coverage_percent=stage_coverage,
            missing_link_count=len(gaps),
        )

    def calculate_release_impact(self, requirement_id: str) -> list[str]:
        self._software_requirement(requirement_id)
        return [
            artifact.id
            for artifact in self.graph.connected_by_type(
                requirement_id, {ArtifactType.BUILD, ArtifactType.BASELINE, ArtifactType.RELEASE}
            )
        ]

    def calculate_change_impact(self, change_request_id: str) -> list[Artifact]:
        change_request = self.graph.artifact(change_request_id)
        if change_request.type is not ArtifactType.CHANGE_REQUEST:
            raise TraceAIError(f"{change_request_id} is not a change request")
        return self.graph.sorted_artifacts(self.graph.connected_ids(change_request_id))

    def _software_requirement(self, requirement_id: str) -> Artifact:
        requirement = self.graph.artifact(requirement_id)
        if requirement.type is not ArtifactType.SOFTWARE_REQUIREMENT:
            raise TraceAIError(f"{requirement_id} is not a software requirement")
        return requirement


def _to_trace_step(artifact: Artifact) -> TraceStep:
    return TraceStep(
        artifact_id=artifact.id,
        artifact_type=artifact.type,
        name=artifact.name,
        version=artifact.version,
        status=artifact.status,
        baseline_id=artifact.baseline_id,
    )


def _severity_order(severity: FindingSeverity) -> int:
    return {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.MAJOR: 1,
        FindingSeverity.MINOR: 2,
        FindingSeverity.INFO: 3,
    }[severity]
