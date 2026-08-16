"""CLI adapter for the six governed AI enhancement workflows."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pydantic import BaseModel

from traceai.ai_gateway import AIModelGateway, OpenAIModelGateway, SyntheticDemoGateway
from traceai.ai_loader import load_ai_knowledge
from traceai.ai_models import AIEnhancementSuiteReport
from traceai.ai_reporting import write_ai_report
from traceai.ai_services import AIEngineeringCopilot
from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_loader import load_engineering_dataset
from traceai.exceptions import AIProviderError

CAPABILITIES = (
    "rca",
    "trace-links",
    "requirement-review",
    "log-analysis",
    "similar-defects",
    "test-generation",
    "suite",
)


def add_ai_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ai = subparsers.add_parser(
        "ai", help="Run governed real-model or offline-demo AI Enhancements 1-6"
    )
    ai.add_argument("capability", choices=CAPABILITIES)
    ai.add_argument(
        "subject_id",
        help="Requirement ID, or LOG ID for log-analysis and similar-defects",
    )
    ai.add_argument(
        "--provider",
        choices=("demo", "openai"),
        default="demo",
        help="demo is offline and not AI; openai invokes real models",
    )
    ai.add_argument(
        "--knowledge",
        type=Path,
        default=Path("data/ai_knowledge.json"),
        help="Validated synthetic AI knowledge dataset",
    )
    ai.add_argument(
        "--engineering-data",
        type=Path,
        default=Path("data/engineering_data.json"),
        help="Validated deterministic engineering graph dataset",
    )
    ai.add_argument("--generation-model", default="gpt-5.6")
    ai.add_argument("--embedding-model", default="text-embedding-3-small")
    ai.add_argument("--top-k", type=int, default=3)
    ai.add_argument(
        "--quality-requirement-id",
        default="SWE-REQ-031",
        help="Draft requirement used by the suite quality-review step",
    )
    ai.add_argument(
        "--log-id",
        default="LOG-IT-045",
        help="Synthetic log used by suite log/defect steps",
    )
    ai.add_argument("--output", type=Path, help="JSON output path")


def run_ai_command(args: argparse.Namespace) -> None:
    knowledge = load_ai_knowledge(args.knowledge)
    graph = EngineeringGraph(load_engineering_dataset(args.engineering_data))
    gateway: AIModelGateway
    if args.provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise AIProviderError(
                "OPENAI_API_KEY is not set. Set it in your shell; never commit it to Git."
            )
        gateway = OpenAIModelGateway(
            generation_model=args.generation_model,
            embedding_model=args.embedding_model,
        )
    else:
        gateway = SyntheticDemoGateway()
    copilot = AIEngineeringCopilot(knowledge, graph, gateway)

    capability = str(args.capability)
    subject_id = str(args.subject_id)
    report: BaseModel
    if capability == "rca":
        report = copilot.analyze_root_cause(subject_id)
    elif capability == "trace-links":
        report = copilot.recommend_trace_links(subject_id, top_k=args.top_k)
    elif capability == "requirement-review":
        report = copilot.review_requirement(subject_id)
    elif capability == "log-analysis":
        report = copilot.analyze_log(subject_id)
    elif capability == "similar-defects":
        report = copilot.retrieve_similar_defects(subject_id, top_k=args.top_k)
    elif capability == "test-generation":
        report = copilot.generate_tests(subject_id)
    else:
        report = AIEnhancementSuiteReport(
            root_cause=copilot.analyze_root_cause(subject_id),
            trace_links=copilot.recommend_trace_links(subject_id, top_k=args.top_k),
            requirement_quality=copilot.review_requirement(args.quality_requirement_id),
            log_analysis=copilot.analyze_log(args.log_id),
            similar_defects=copilot.retrieve_similar_defects(args.log_id, top_k=args.top_k),
            test_generation=copilot.generate_tests(subject_id),
        )

    output = args.output or Path("outputs/ai") / f"{capability}-{subject_id}.json"
    path = write_ai_report(report, output)
    print(f"AI capability: {capability}")
    print(f"Provider: {gateway.provider_name}")
    print(f"Live model used: {gateway.live_model_used}")
    print(f"Generation model: {gateway.generation_model}")
    print(f"Embedding model: {gateway.embedding_model}")
    print("Review decision: PROPOSED")
    print(f"Wrote {path}")
