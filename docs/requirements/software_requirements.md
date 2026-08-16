# TraceAI internal software requirements

These requirements govern the PoC implementation. They do not describe the vehicle product.

| ID | Requirement | Verification |
| --- | --- | --- |
| POC-SWR-001 | The system shall reconstruct a bidirectional engineering digital thread from a valid Software Requirement ID through system requirement, architecture, design, software unit, source, commit, verification, build, baseline, and release. | Automated verification |
| POC-SWR-002 | The system shall deterministically report missing mandatory engineering links with category, severity, affected artifact, and evidence IDs. | Automated verification |
| POC-SWR-003 | The system shall deterministically detect interface-version, build-to-requirement-baseline, and baseline-snapshot mismatches. | Automated verification |
| POC-SWR-004 | The system shall identify the first failed mandatory verification stage and distinguish it from traceability and configuration findings. | Automated verification |
| POC-SWR-005 | The system shall calculate downstream blocking impact without modifying persisted engineering artifacts. | Automated verification |
| POC-SWR-006 | The system shall generate advisory RCA only from a validated evidence package and cite used evidence IDs. | Automated verification |
| POC-SWR-007 | The system shall traverse a Change Request and group affected artifacts, highlighting artifacts that pre-date the change. | Automated verification |
| POC-SWR-008 | The system shall determine release eligibility from critical gaps, mandatory verification, blocking defects, and configuration consistency without LLM input. | Automated verification |
| POC-SWR-009 | The system shall record AI adapter, prompt contract, timestamp, confidence, evidence IDs, and human-review state for each recommendation. | Inspection and automated verification |
| POC-SWR-010 | The system shall provide CLI and Streamlit interfaces for Requirement-ID analysis using the same application service. | Integration test and demonstration |
| POC-SWR-011 | The original requirements-quality analysis shall remain runnable after the digital-thread revision. | Regression test |
| POC-SWR-012 | CI shall run format, lint, type, security, unit, integration, verification, coverage, build, smoke, and dependency checks without external LLM calls. | CI inspection |
| POC-AI-001 | The system shall support a real structured-output LLM for evidence-grounded root-cause hypotheses while rejecting citations outside the controlled evidence package. | Automated verification and mocked provider integration |
| POC-AI-002 | The system shall use an embedding model to rank candidate engineering trace links without automatically accepting or writing those links. | Automated verification |
| POC-AI-003 | The system shall use a structured-output LLM to identify semantic requirement-quality issues and propose measurable wording without approving the requirement. | Automated verification |
| POC-AI-004 | The system shall use a structured-output LLM to summarize a controlled engineering log, separate observations from hypotheses, and cite evidence IDs. | Automated verification |
| POC-AI-005 | The system shall use embeddings to retrieve similar controlled historical defects and shall state that similarity does not prove an identical root cause. | Automated verification |
| POC-AI-006 | The system shall use a structured-output LLM to propose traced verification cases that remain in `PROPOSED` review state and never claim execution or approval. | Automated verification |
