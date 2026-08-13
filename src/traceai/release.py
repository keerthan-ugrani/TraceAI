"""Deterministic release eligibility for an ASPICE-oriented candidate baseline."""

from __future__ import annotations

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import (
    ArtifactStatus,
    ArtifactType,
    FindingSeverity,
    ReleaseEligibility,
    ReleaseStatus,
)
from traceai.traceability import TraceabilityEngine


class ReleaseEligibilityEngine:
    def __init__(
        self,
        graph: EngineeringGraph,
        traceability: TraceabilityEngine,
        configuration: ConfigurationEngine,
    ) -> None:
        self.graph = graph
        self.traceability = traceability
        self.configuration = configuration

    def evaluate(self, requirement_id: str, release_id: str) -> ReleaseEligibility:
        release = self.graph.artifact(release_id)
        reasons: list[str] = []
        evidence_ids: set[str] = {release_id}

        critical_gaps = [
            gap
            for gap in self.traceability.find_missing_links(requirement_id)
            if gap.severity is FindingSeverity.CRITICAL
        ]
        if critical_gaps:
            reasons.append(f"{len(critical_gaps)} critical traceability gap(s) remain open.")
            evidence_ids.update(gap.artifact_id for gap in critical_gaps)

        failing_tests = [
            artifact
            for artifact in self.graph.connected_by_type(
                requirement_id,
                {
                    ArtifactType.UNIT_TEST,
                    ArtifactType.COMPONENT_TEST,
                    ArtifactType.INTEGRATION_TEST,
                    ArtifactType.SOFTWARE_VERIFICATION_TEST,
                },
            )
            if artifact.status in {ArtifactStatus.FAIL, ArtifactStatus.BLOCKED}
            and artifact.metadata.get("mandatory", True)
        ]
        if failing_tests:
            reasons.append(
                "Mandatory verification is not successful: "
                + ", ".join(artifact.id for artifact in failing_tests)
                + "."
            )
            evidence_ids.update(artifact.id for artifact in failing_tests)

        blocking_defects = [
            artifact
            for artifact in self.graph.connected_by_type(requirement_id, {ArtifactType.DEFECT})
            if artifact.status is ArtifactStatus.OPEN and artifact.metadata.get("blocking", False)
        ]
        if blocking_defects:
            reasons.append(
                "Blocking defects are unresolved: "
                + ", ".join(artifact.id for artifact in blocking_defects)
                + "."
            )
            evidence_ids.update(artifact.id for artifact in blocking_defects)

        mismatches = self.configuration.find_mismatches(requirement_id)
        release_mismatches = [
            mismatch
            for mismatch in mismatches
            if release_id in mismatch.evidence_ids
            or any(
                evidence_id in self.graph.connected_ids(release.id, max_depth=3)
                for evidence_id in mismatch.evidence_ids
            )
        ]
        if release_mismatches:
            reasons.append(
                f"{len(release_mismatches)} configuration mismatch(es) affect the release."
            )
            for mismatch in release_mismatches:
                evidence_ids.update(mismatch.evidence_ids)

        return ReleaseEligibility(
            release_id=release_id,
            status=ReleaseStatus.BLOCKED if reasons else ReleaseStatus.ELIGIBLE,
            blocking_reasons=reasons,
            evidence_ids=sorted(evidence_ids),
        )
