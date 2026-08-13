"""Evidence-grounded engineering reasoning behind a replaceable AI abstraction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from traceai.engineering_models import FailureAnalysis, RootCauseAnalysis


class EngineeringReasoningService(Protocol):
    """External LLM adapters must implement this validated, evidence-only boundary."""

    def explain_failure(
        self, failure: FailureAnalysis, *, generated_at: datetime | None = None
    ) -> RootCauseAnalysis:
        """Create advisory hypotheses from an already retrieved evidence package."""
        ...


class DeterministicReasoningFallback:
    """Offline fallback that keeps the interview demo reliable and auditable."""

    model_name = "deterministic-evidence-fallback"
    prompt_version = "rca-v1"

    def explain_failure(
        self, failure: FailureAnalysis, *, generated_at: datetime | None = None
    ) -> RootCauseAnalysis:
        evidence = failure.evidence
        top_suspect = failure.suspects[0] if failure.suspects else None
        if (
            failure.first_failure_id
            and failure.failure_level
            and evidence.configuration_mismatch_ids
            and evidence.interface_ids
        ):
            probable = (
                "Evidence indicates a probable interface-contract inconsistency between "
                "AlignmentController and ChargingStateMachine. The connected software units "
                "pass earlier verification, while the first failure occurs during integration."
            )
            confidence = "High"
        elif failure.first_failure_id:
            probable = (
                "A probable cause exists on the connected path, but the available evidence is "
                "insufficient to isolate one component conclusively."
            )
            confidence = "Medium"
        else:
            probable = "Root cause cannot be determined because no failed verification was found."
            confidence = "Low"

        observations = [failure.localization_summary]
        if evidence.expected_value is not None and evidence.actual_value is not None:
            observations.append(
                f"The failing test expected {evidence.expected_value!r} but observed "
                f"{evidence.actual_value!r}."
            )
        if evidence.configuration_mismatch_ids:
            observations.append(
                "Deterministic configuration checks identified version inconsistencies at: "
                + ", ".join(evidence.configuration_mismatch_ids)
                + "."
            )
        return RootCauseAnalysis(
            title="Probable root cause",
            probable_root_cause=probable,
            confidence=confidence,
            suspected_component_ids=[
                suspect.artifact_id
                for suspect in failure.suspects
                if suspect.artifact_id not in evidence.interface_ids
            ][:3],
            suspected_interface_ids=[
                suspect.artifact_id
                for suspect in failure.suspects
                if suspect.artifact_id in evidence.interface_ids
            ][:3],
            observations=observations,
            evidence_ids=sorted(
                {
                    *([failure.first_failure_id] if failure.first_failure_id else []),
                    *evidence.interface_ids,
                    *evidence.commit_ids,
                    *evidence.configuration_mismatch_ids,
                    *([top_suspect.artifact_id] if top_suspect else []),
                }
            ),
            recommended_checks=[
                "Compare the ARCH-IF-006 v2.0 and v2.1 enumeration contracts.",
                "Inspect the downstream status mapping in charging_state_machine.py.",
                "Re-run IT-045 against the corrected, baselined interface version.",
            ],
            model_name=self.model_name,
            prompt_version=self.prompt_version,
            generated_at=generated_at or datetime.now(UTC),
        )
