"""Deterministic version, baseline, and interface-contract consistency checks."""

from __future__ import annotations

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import (
    ArtifactType,
    ConfigurationMismatch,
    Relationship,
)


class ConfigurationEngine:
    """Detect configuration mismatches without delegating truth to an LLM."""

    def __init__(self, graph: EngineeringGraph) -> None:
        self.graph = graph

    def find_mismatches(self, requirement_id: str) -> list[ConfigurationMismatch]:
        connected_ids = self.graph.connected_ids(requirement_id)
        mismatches: list[ConfigurationMismatch] = []

        for relationship in self.graph.dataset.relationships:
            if (
                relationship.source_id not in connected_ids
                or relationship.target_id not in connected_ids
            ):
                continue
            mismatches.extend(self._relationship_mismatches(relationship))

        requirement = self.graph.artifact(requirement_id)
        for build in self.graph.connected_by_type(requirement_id, {ArtifactType.BUILD}):
            build_requirement_baseline = build.metadata.get("requirement_baseline")
            if (
                requirement.baseline_id
                and build_requirement_baseline
                and requirement.baseline_id != build_requirement_baseline
            ):
                mismatches.append(
                    ConfigurationMismatch(
                        artifact_id=requirement.id,
                        context=f"{build.id} uses a stale requirements baseline",
                        expected_version=requirement.baseline_id,
                        actual_version=str(build_requirement_baseline),
                        evidence_ids=[requirement.id, build.id, str(build_requirement_baseline)],
                    )
                )

        for baseline in self.graph.connected_by_type(requirement_id, {ArtifactType.BASELINE}):
            if not baseline.metadata.get("compare_to_current", False):
                continue
            artifact_versions = baseline.metadata.get("artifact_versions", {})
            if not isinstance(artifact_versions, dict):
                continue
            for artifact_id, baseline_version in artifact_versions.items():
                if artifact_id not in connected_ids:
                    continue
                current_version = self.graph.artifact(artifact_id).version
                if current_version == str(baseline_version):
                    continue
                mismatches.append(
                    ConfigurationMismatch(
                        artifact_id=artifact_id,
                        context=f"{baseline.id} contains a different controlled version",
                        expected_version=current_version,
                        actual_version=str(baseline_version),
                        evidence_ids=[artifact_id, baseline.id],
                    )
                )
        return _deduplicate(mismatches)

    def _relationship_mismatches(self, relationship: Relationship) -> list[ConfigurationMismatch]:
        source = self.graph.artifact(relationship.source_id)
        target = self.graph.artifact(relationship.target_id)
        mismatches: list[ConfigurationMismatch] = []
        expected_target = relationship.metadata.get("expected_target_version")
        if expected_target is not None and str(expected_target) != target.version:
            mismatches.append(
                ConfigurationMismatch(
                    artifact_id=target.id,
                    context=f"{source.id} expects another version of {target.id}",
                    expected_version=str(expected_target),
                    actual_version=target.version,
                    evidence_ids=[source.id, target.id, relationship.id],
                )
            )
        expected_source = relationship.metadata.get("expected_source_version")
        if expected_source is not None and str(expected_source) != source.version:
            mismatches.append(
                ConfigurationMismatch(
                    artifact_id=source.id,
                    context=f"{target.id} traces to another version of {source.id}",
                    expected_version=str(expected_source),
                    actual_version=source.version,
                    evidence_ids=[source.id, target.id, relationship.id],
                )
            )
        return mismatches


def _deduplicate(items: list[ConfigurationMismatch]) -> list[ConfigurationMismatch]:
    unique: dict[tuple[str, str, str, str], ConfigurationMismatch] = {}
    for item in items:
        key = (item.artifact_id, item.context, item.expected_version, item.actual_version)
        unique[key] = item
    return sorted(unique.values(), key=lambda item: (item.artifact_id, item.context))
