"""Evidence collection, first-failure localization, and deterministic suspect ranking."""

from __future__ import annotations

from collections import defaultdict

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import STAGE_ORDER, EngineeringGraph
from traceai.engineering_models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    EngineeringIssueCategory,
    FailureAnalysis,
    FailureEvidencePackage,
    Suspect,
)

TEST_TYPES = {
    ArtifactType.UNIT_TEST,
    ArtifactType.COMPONENT_TEST,
    ArtifactType.INTEGRATION_TEST,
    ArtifactType.SOFTWARE_VERIFICATION_TEST,
}


class FailureAnalysisService:
    def __init__(self, graph: EngineeringGraph, configuration: ConfigurationEngine) -> None:
        self.graph = graph
        self.configuration = configuration

    def analyze(self, requirement_id: str) -> FailureAnalysis:
        evidence = self.collect_failure_evidence(requirement_id)
        failed = self._first_failed_test(requirement_id)
        propagated = self._propagate(requirement_id, failed)
        suspects = self.rank_suspect_components(requirement_id, failed)
        failure_level = _failure_level(failed.type) if failed else None
        if failed and failed.type is ArtifactType.INTEGRATION_TEST:
            summary = (
                "Failure appears localized to component interaction: unit and component "
                "verification pass, while integration verification fails."
            )
        elif failed:
            summary = f"The first failed mandatory verification is at {failure_level}."
        else:
            summary = "No failed mandatory verification was found in the connected thread."
        return FailureAnalysis(
            category=EngineeringIssueCategory.TEST_FAILURE if failed else None,
            first_failure_id=failed.id if failed else None,
            failure_level=failure_level,
            localization_summary=summary,
            propagated_statuses=propagated,
            suspects=suspects,
            evidence=evidence,
        )

    def collect_failure_evidence(self, requirement_id: str) -> FailureEvidencePackage:
        connected = self.graph.sorted_artifacts(self.graph.connected_ids(requirement_id))
        failed = self._first_failed_test(requirement_id)
        tests_by_status: dict[str, list[str]] = defaultdict(list)
        for artifact in connected:
            if artifact.type in TEST_TYPES:
                tests_by_status[artifact.status.value].append(artifact.id)

        interfaces = [a.id for a in connected if a.type is ArtifactType.ARCHITECTURE_INTERFACE]
        commits = [a for a in connected if a.type is ArtifactType.COMMIT]
        changed_files = sorted(
            {
                str(file_name)
                for commit in commits
                for file_name in commit.metadata.get("changed_files", [])
            }
        )
        executions = [a for a in connected if a.type is ArtifactType.TEST_EXECUTION]
        mismatches = self.configuration.find_mismatches(requirement_id)
        failed_metadata = failed.metadata if failed else {}
        return FailureEvidencePackage(
            requirement_id=requirement_id,
            architecture_ids=[
                a.id for a in connected if a.type is ArtifactType.ARCHITECTURE_COMPONENT
            ],
            software_unit_ids=[a.id for a in connected if a.type is ArtifactType.SOFTWARE_UNIT],
            tests_by_status={key: sorted(value) for key, value in sorted(tests_by_status.items())},
            failed_test_id=failed.id if failed else None,
            failure_level=_failure_level(failed.type) if failed else None,
            expected_value=_optional_string(failed_metadata.get("expected")),
            actual_value=_optional_string(failed_metadata.get("actual")),
            failure_message=_optional_string(failed_metadata.get("failure_message")),
            runtime_log=_optional_string(failed_metadata.get("runtime_log")),
            interface_ids=interfaces,
            commit_ids=[commit.id for commit in commits],
            changed_files=changed_files,
            previous_test_runs=[execution.id for execution in executions],
            configuration_mismatch_ids=sorted({mismatch.artifact_id for mismatch in mismatches}),
            defect_ids=[a.id for a in connected if a.type is ArtifactType.DEFECT],
            change_request_ids=[a.id for a in connected if a.type is ArtifactType.CHANGE_REQUEST],
            build_ids=[a.id for a in connected if a.type is ArtifactType.BUILD],
            baseline_ids=[a.id for a in connected if a.type is ArtifactType.BASELINE],
            release_ids=[a.id for a in connected if a.type is ArtifactType.RELEASE],
        )

    def rank_suspect_components(
        self, requirement_id: str, failed: Artifact | None
    ) -> list[Suspect]:
        mismatches = self.configuration.find_mismatches(requirement_id)
        suspects: list[Suspect] = []
        for mismatch in mismatches:
            artifact = self.graph.artifact(mismatch.artifact_id)
            if artifact.type is ArtifactType.ARCHITECTURE_INTERFACE:
                suspects.append(
                    Suspect(
                        artifact_id=artifact.id,
                        probability_percent=61,
                        reason=(
                            "A version mismatch exists at the first failing integration boundary."
                        ),
                        evidence_ids=mismatch.evidence_ids + ([failed.id] if failed else []),
                    )
                )
        if failed:
            components = self.graph.connected_by_type(
                failed.id, {ArtifactType.ARCHITECTURE_COMPONENT}, max_depth=5
            )
            remaining = 39 / max(1, len(components))
            suspects.extend(
                Suspect(
                    artifact_id=component.id,
                    probability_percent=round(remaining, 1),
                    reason="The component is connected to the failing integration path.",
                    evidence_ids=[failed.id, component.id],
                )
                for component in components
            )
        return sorted(
            suspects, key=lambda suspect: (-suspect.probability_percent, suspect.artifact_id)
        )

    def _first_failed_test(self, requirement_id: str) -> Artifact | None:
        tests = [
            artifact
            for artifact in self.graph.connected_by_type(requirement_id, TEST_TYPES)
            if artifact.status is ArtifactStatus.FAIL
        ]
        return min(tests, key=lambda artifact: STAGE_ORDER[artifact.type]) if tests else None

    def _propagate(self, requirement_id: str, failed: Artifact | None) -> dict[str, str]:
        if failed is None:
            return {}
        result: dict[str, str] = {failed.id: ArtifactStatus.FAIL.value}
        for artifact in self.graph.sorted_artifacts(self.graph.connected_ids(requirement_id)):
            if STAGE_ORDER[artifact.type] <= STAGE_ORDER[failed.type]:
                continue
            if artifact.type in {
                ArtifactType.BUILD,
                ArtifactType.BASELINE,
                ArtifactType.RELEASE,
            } and not artifact.metadata.get("target_requirement_failure", False):
                continue
            if artifact.type is ArtifactType.SOFTWARE_VERIFICATION_TEST:
                result[artifact.id] = ArtifactStatus.BLOCKED.value
            elif artifact.type is ArtifactType.BUILD:
                result[artifact.id] = "NOT_RELEASE_ELIGIBLE"
            elif artifact.type is ArtifactType.BASELINE:
                result[artifact.id] = ArtifactStatus.WARNING.value
            elif artifact.type is ArtifactType.RELEASE:
                result[artifact.id] = "AT_RISK"
        return result


def _failure_level(artifact_type: ArtifactType) -> str:
    return {
        ArtifactType.UNIT_TEST: "Software Unit Verification (SWE.4)",
        ArtifactType.COMPONENT_TEST: "Component Verification (SWE.5)",
        ArtifactType.INTEGRATION_TEST: "Integration Verification (SWE.5)",
        ArtifactType.SOFTWARE_VERIFICATION_TEST: "Software Verification (SWE.6)",
    }[artifact_type]


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)
