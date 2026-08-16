"""Streamlit entry point for the Engineering Intelligence Copilot demo."""

from pathlib import Path

import streamlit as st

from traceai.ai_gateway import OpenAIModelGateway, SyntheticDemoGateway
from traceai.ai_loader import load_ai_knowledge
from traceai.ai_services import AIEngineeringCopilot
from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_loader import load_engineering_dataset
from traceai.intelligence import EngineeringIntelligenceService

DATA_PATH = Path(__file__).parent / "data" / "engineering_data.json"
AI_DATA_PATH = Path(__file__).parent / "data" / "ai_knowledge.json"


@st.cache_resource
def build_service() -> EngineeringIntelligenceService:
    return EngineeringIntelligenceService(EngineeringGraph(load_engineering_dataset(DATA_PATH)))


def build_ai_copilot(provider: str) -> AIEngineeringCopilot:
    gateway = OpenAIModelGateway() if provider == "openai" else SyntheticDemoGateway()
    return AIEngineeringCopilot(
        load_ai_knowledge(AI_DATA_PATH),
        EngineeringGraph(load_engineering_dataset(DATA_PATH)),
        gateway,
    )


def main() -> None:
    st.set_page_config(page_title="Engineering Intelligence Copilot", layout="wide")
    st.title("Engineering Intelligence Copilot")
    st.caption(
        "AI-assisted ASPICE digital thread, configuration management, failure localization "
        "and evidence-backed root-cause analysis"
    )

    requirement_id = st.text_input(
        "Analyse Requirement ID",
        value="SWE-REQ-014",
        help="Try SWE-REQ-014 for the failure scenario or SWE-REQ-030 for a healthy thread.",
    )
    if st.button("Analyse", type="primary"):
        st.session_state["analyzed_requirement_id"] = requirement_id.strip()
    if "analyzed_requirement_id" not in st.session_state:
        st.info("Enter a controlled software requirement ID and select Analyse.")
        return
    analyzed_requirement_id = str(st.session_state["analyzed_requirement_id"])

    try:
        report = build_service().analyze_requirement(analyzed_requirement_id)
    except Exception as exc:  # UI boundary converts domain errors to a user-visible message.
        st.error(str(exc))
        return

    st.subheader(f"{report.requirement.artifact_id} — {report.requirement.name}")
    columns = st.columns(6)
    columns[0].metric("Overall Health", report.overall_health)
    columns[1].metric("Traceability", f"{report.metrics.overall_coverage_percent:.1f}%")
    columns[2].metric("Verification", f"{report.metrics.verification_percent:.1f}%")
    columns[3].metric(
        "Configuration",
        "WARNING" if report.configuration_mismatches else "CONSISTENT",
    )
    columns[4].metric("Open Defects", len(report.open_defect_ids))
    columns[5].metric("Release", report.release_eligibility.status)

    st.subheader("Engineering Digital Thread")
    st.dataframe(
        [
            {
                "Stage": step.artifact_type,
                "Artifact ID": step.artifact_id,
                "Name": step.name,
                "Version": step.version,
                "Status": report.failure_analysis.propagated_statuses.get(
                    step.artifact_id, step.status
                ),
                "Baseline": step.baseline_id or "—",
            }
            for step in report.digital_thread
        ],
        width="stretch",
        hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Missing Links")
        if report.missing_links:
            for gap in report.missing_links:
                st.warning(f"{gap.severity} · {gap.artifact_id}: {gap.message}")
        else:
            st.success("No deterministic traceability gaps detected.")

    with right:
        st.subheader("Configuration")
        if report.configuration_mismatches:
            for mismatch in report.configuration_mismatches:
                st.error(
                    f"{mismatch.artifact_id}: expected {mismatch.expected_version}, "
                    f"actual {mismatch.actual_version} — {mismatch.context}"
                )
        else:
            st.success("Configuration is consistent.")

    st.subheader("Failure Analysis")
    st.write(f"**First failure:** {report.failure_analysis.first_failure_id or 'None'}")
    st.write(f"**Level:** {report.failure_analysis.failure_level or 'None'}")
    st.write(report.failure_analysis.localization_summary)

    st.subheader("AI Root-Cause Analysis")
    st.info(report.root_cause_analysis.probable_root_cause)
    st.write(f"**Confidence:** {report.root_cause_analysis.confidence}")
    st.write("**Evidence:** " + ", ".join(report.root_cause_analysis.evidence_ids))
    st.write("**Recommended checks:**")
    for check in report.root_cause_analysis.recommended_checks:
        st.write(f"- {check}")
    st.caption(
        f"Advisory output · {report.root_cause_analysis.model_name} · "
        f"review state {report.root_cause_analysis.review_decision}"
    )

    if report.change_impact:
        st.subheader("Change Impact")
        st.write(report.change_impact.summary)
        st.json(report.change_impact.affected_by_type, expanded=False)
        st.write(
            "**Requires review/re-verification:** "
            + ", ".join(report.change_impact.stale_artifact_ids)
        )

    st.subheader("Release Impact")
    if report.release_eligibility.blocking_reasons:
        st.error(f"{report.release_eligibility.release_id}: {report.release_eligibility.status}")
        for reason in report.release_eligibility.blocking_reasons:
            st.write(f"- {reason}")
    else:
        st.success(f"{report.release_eligibility.release_id} is eligible.")

    st.divider()
    st.subheader("AI Enhancements 1-6")
    st.caption(
        "Run the offline demo without an API key, or select OpenAI to invoke real structured "
        "generation and embedding models. Every result remains PROPOSED."
    )
    provider = st.radio(
        "AI provider",
        options=("demo", "openai"),
        horizontal=True,
        help="demo is deterministic and not AI; openai makes real model API calls.",
    )
    inputs = st.columns(2)
    quality_requirement_id = inputs[0].text_input(
        "Draft requirement for quality review", value="SWE-REQ-031"
    )
    log_id = inputs[1].text_input("Engineering log", value="LOG-IT-045")
    if not st.button("Run AI Suite"):
        return

    try:
        with st.spinner("Running six governed AI workflows..."):
            copilot = build_ai_copilot(provider)
            rca = copilot.analyze_root_cause(analyzed_requirement_id)
            links = copilot.recommend_trace_links(analyzed_requirement_id)
            quality = copilot.review_requirement(quality_requirement_id.strip())
            logs = copilot.analyze_log(log_id.strip())
            defects = copilot.retrieve_similar_defects(log_id.strip())
            tests = copilot.generate_tests(analyzed_requirement_id)
    except Exception as exc:  # UI boundary converts provider/domain errors to a safe message.
        st.error(str(exc))
        return

    st.warning(
        f"Provider: {rca.provenance.provider} · live model: "
        f"{rca.provenance.live_model_used} · review state: PROPOSED"
    )
    tabs = st.tabs(
        [
            "1 · RCA",
            "2 · Trace links",
            "3 · Requirement",
            "4 · Logs",
            "5 · Defects",
            "6 · Tests",
        ]
    )
    with tabs[0]:
        st.write(rca.analysis.summary)
        st.json(rca.analysis.model_dump(mode="json"), expanded=False)
    with tabs[1]:
        st.dataframe(
            [item.model_dump(mode="json") for item in links.recommendations],
            width="stretch",
            hide_index=True,
        )
    with tabs[2]:
        st.write(quality.review.summary)
        st.code(quality.review.rewritten_requirement)
        st.json(quality.review.model_dump(mode="json"), expanded=False)
    with tabs[3]:
        st.write(logs.analysis.summary)
        st.json(logs.analysis.model_dump(mode="json"), expanded=False)
    with tabs[4]:
        st.dataframe(
            [item.model_dump(mode="json") for item in defects.matches],
            width="stretch",
            hide_index=True,
        )
    with tabs[5]:
        st.write(tests.plan.coverage_summary)
        st.dataframe(
            [item.model_dump(mode="json") for item in tests.plan.test_cases],
            width="stretch",
            hide_index=True,
        )


if __name__ == "__main__":
    main()
