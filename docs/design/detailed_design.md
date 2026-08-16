# Detailed design

## Engineering graph

- Dictionary lookup provides artifact resolution.
- Incoming and outgoing adjacency indexes enable bidirectional navigation.
- Breadth-first search reconstructs the connected thread.
- Stage-order metadata produces deterministic V-model presentation.

## Traceability engine

The engine filters connected artifacts into the core thread and runs type-specific mandatory
link rules. Findings use a separate `TRACEABILITY_GAP` category.

## Configuration engine

The engine compares edge-level version expectations, current requirement baseline versus
build baseline, and explicitly selected baseline snapshots. It performs exact string
comparison for the PoC.

## Failure analysis

Failed mandatory tests are ordered by verification level. The calculated propagation view is
not written back to the dataset. Evidence collection returns a Pydantic model before advisory
reasoning begins.

## Reasoning

`EngineeringReasoningService` is a protocol. The offline fallback is deterministic and
ensures reproducible demonstration/CI. TraceAI v2 adds `OpenAIModelGateway`, which uses the
Responses API structured-output helper for real LLM drafts and the Embeddings API for semantic
retrieval. `AIEngineeringCopilot` checks classification, validates every generated evidence ID,
and adds immutable provenance after generation.

## Semantic retrieval

Candidate trace documents and historical defects are embedded in one batch with the query.
Application-owned cosine similarity ranks the candidates. The model does not write graph edges;
trace recommendations remain `PROPOSED`. Similarity is evidence for review, not proof of an
identical relationship or root cause.

## AI-assisted test generation

The model receives only a validated `TestGenerationContext`: requirement text, architecture,
interface contracts, acceptance criteria, design constraints, existing tests, safety notes, and
allowed evidence IDs. Generated IDs must begin `AI-TC-`, be unique, cite the target requirement,
use allowed evidence, and remain `PROPOSED`. No generated test is treated as executed evidence.

## Release eligibility

Release eligibility is a pure deterministic decision. Reasons and evidence IDs remain visible
to the UI and report.
