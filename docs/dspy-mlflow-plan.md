# DSPy + MLflow Integration Plan

This plan covers Option C (DSPy pipeline for Q&A with sources) and Option D (tracking DSPy optimization runs in MLflow), with a staged path that can execute DSPy alone or as a combined approach with MLflow tracking and registry support. The goal is to maximize transparency, reproducibility, and operational clarity.

## Executive Summary
**Objectives**
- Introduce DSPy programs to formalize retrieval → reasoning → verification flows and enable self-improvement.
- Use MLflow to track DSPy experimentation, store artifacts, and optionally register tuned pipelines for controlled rollout.
- Maintain operational guardrails (observability, rollback, and documentation) across both approaches.

**Tasks**
- Prototype a DSPy Q&A pipeline using existing retrieval/search and verification components.
- Instrument DSPy training/evaluation runs with MLflow logging of params, metrics, and serialized programs.
- Package the best-performing DSPy program as an artifact (and optionally register it) for API consumption behind a feature flag.
- Document workflows, configuration, and rollback procedures.

**Dependencies**
- Existing retrieval/search services, evaluation datasets, and FastAPI runtime in `apps/api/`.
- Python tooling (poetry/uv) and access to any LLM/provider credentials already used by the service.
- MLflow backend (local `mlruns/` or remote server) for Option D; optional object store/DB if using registry.

**Deliverables**
- DSPy prototype module(s) with runnable scripts/tests for Q&A evaluation.
- MLflow-integrated training/evaluation scripts and logged artifacts for DSPy runs.
- Feature-flagged API integration path to toggle DSPy pipelines and load MLflow-produced artifacts.
- Updated diagrams and documentation describing architecture, data flows, and ops runbooks.

## Updates to Architecture

### Objectives
- Clarify how DSPy modules fit into the existing retrieval and chat API stack.
- Show where MLflow tracks experiments and where the API loads DSPy artifacts from the registry or filesystem.
- Keep rollback and baseline paths explicit.

### Tasks
- Define DSPy pipeline boundaries (retriever, reasoning, verifier) aligned with current search/vector store utilities.
- Add MLflow tracking and artifact storage touchpoints to the experimentation loop.
- Extend the FastAPI service to resolve DSPy artifacts (local or MLflow registry) behind a feature flag.
- Update diagrams to reflect data flow with and without MLflow involvement.

### Dependencies
- Current service topology (FastAPI, vector search, LLM providers) and evaluation harness.
- MLflow tracking URI and registry backend if used.

### Deliverables
- Updated architecture diagram (below) and supporting text in docs.

### Architecture & Data Flow Diagram
```mermaid
graph TD
    subgraph Client
        U[User]
    end

    subgraph API[FastAPI Service]
        FF[Feature Flag<br/>Baseline vs DSPy]
        ORCH[Query Orchestrator]
        DSPY[Optional DSPy Program<br/>(Retrieve -> Reason -> Verify)]
        BASE[Baseline Pipeline]
    end

    subgraph Retrieval
        VS[Vector Store / Search]
        IDX[Index Docs]
    end

    subgraph LLMs[LLM Providers]
        GEN[Generator]
        VERIFY[Verifier]
    end

    subgraph Eval[Evaluation Harness]
        DATA[Eval Datasets]
    end

    subgraph MLflow
        TRACK[Tracking Server]
        ART[Artifacts / Registry]
    end

    U -->|Query| API
    API --> FF
    FF -->|DSPy enabled| DSPY
    FF -->|DSPy disabled| BASE

    DSPY --> VS
    DSPY --> GEN
    DSPY --> VERIFY

    BASE --> VS
    BASE --> GEN
    BASE --> VERIFY

    VS --> IDX
    ORCH -->|Log runs| TRACK
    DSPY -->|Log artifacts (program, prompts)| TRACK
    TRACK --> ART
    ORCH -->|Load DSPy artifact
(local or registry)| DSPY

    EvalHarness((CLI/Tests)) -->|Run eval
+ log metrics| TRACK
    EvalHarness -->|Use DSPy program| DSPY
    EvalHarness -->|Use baseline| BASE
```

## Detailed Development Phase

### Phase 1: DSPy Prototype (Option C foundation)
- **Objectives**
  - Build a minimal DSPy pipeline for core Q&A journeys with explicit input/output schemas and source citations.
  - Validate functional parity with the baseline pipeline using existing evaluation datasets.
- **Tasks**
  - Add dependency `dspy-ai` and create `pipelines/dspy/` (or similar) with modules: Retriever (wraps vector search), Reasoner (ReAct-style or chain-of-thought), and Verifier (leveraging existing verification logic).
  - Translate 1–2 canonical flows (e.g., rental income queries, compliance lookup) into DSPy `Program` classes with unit-style tests or CLI runner.
  - Add configuration/feature flag scaffolding in `apps/api/` to toggle DSPy per-request or per-tenant; ensure observability hooks (structured logging with prompt/model IDs, sources, latencies).
  - Run baseline evaluation harness against DSPy prototype to collect accuracy/latency metrics; document findings.
- **Dependencies**
  - Existing retrieval utilities and evaluation datasets.
  - Access to LLM provider credentials used in production.
- **Deliverables**
  - DSPy module(s) checked into the repo with runnable examples/tests.
  - Evaluation results comparing baseline vs DSPy prototype, captured in docs.
  - Feature-flag wiring allowing safe opt-in for DSPy in the API.

### Phase 2: MLflow-Tracked DSPy Experiments (Option D core)
- **Objectives**
  - Make DSPy experimentation reproducible with MLflow logging and artifact storage.
  - Capture metrics (accuracy, latency, hallucination rate) and program artifacts for each optimization run.
- **Tasks**
  - Add `mlflow` dependency and configure tracking URI (local `mlruns/` default). Parameterize via env vars for CI/local parity.
  - Wrap DSPy training/evaluation scripts with `mlflow.start_run()`; log params (LLM/model IDs, prompt templates, module configs), metrics, and serialized DSPy program artifacts (`mlflow.log_artifact`).
  - Emit error-case bundles (misclassified examples, hallucination traces) as artifacts for post-mortem analysis.
  - Document how to launch runs (commands, env vars) and where artifacts live.
- **Dependencies**
  - Phase 1 DSPy prototype runnable end-to-end.
  - MLflow accessible locally or remotely (file store is acceptable initially).
- **Deliverables**
  - MLflow-instrumented DSPy training/eval scripts or notebooks.
  - Logged runs with metrics and artifacts stored under `mlruns/` (or configured backend).
  - Documentation for running and inspecting experiments.

### Phase 3: Registry & API Integration (Option D extended)
- **Objectives**
  - Enable the API to load the best-performing DSPy program from MLflow artifacts/registry with staged promotion.
  - Provide rollback to baseline or last-known-good DSPy artifact.
- **Tasks**
  - Decide artifact resolution order: explicit file path (for local dev) → MLflow Registry Production stage (for deployed envs).
  - Implement loader in `apps/api/` that fetches the DSPy program via `mlflow.pyfunc.load_model()` or artifact download, deserializes, and injects into the feature-flagged DSPy path.
  - Add smoke tests in CI to ensure the API can load the current Production artifact; include fallback to bundled baseline if registry unreachable.
  - Document promotion/runbook: how to register a run as Staging, perform eval, and promote to Production; how to rollback.
- **Dependencies**
  - MLflow server/registry backend (SQLite+filesystem for starter or Postgres+S3/MinIO for shared envs).
  - Stable DSPy serialization/deserialization path from Phase 2.
- **Deliverables**
  - API code path that conditionally loads DSPy artifacts from MLflow.
  - CI smoke test coverage for artifact loading.
  - Runbook for promotion and rollback.

### Phase 4: Operations & Observability (applies to both C and D)
- **Objectives**
  - Ensure production readiness with monitoring, drift detection, and clear documentation.
- **Tasks**
  - Standardize structured logging for both baseline and DSPy paths (prompts, model IDs, sources, latencies, error codes) with PII scrubbing.
  - Add evaluation thresholds and alerts: fail builds or block promotions if metrics regress; monitor live metrics for drift vs. MLflow baselines.
  - Maintain "last-known-good" DSPy artifact reference and automated rollback switch in feature flag config.
  - Consolidate documentation (diagrams, runbooks, config examples) in `docs/` and keep change log entries for each rollout.
- **Dependencies**
  - Observability stack currently used by the service (logging/metrics backend).
  - Feature flag mechanism from earlier phases.
- **Deliverables**
  - Logging/metrics instrumentation parity between DSPy and baseline paths.
  - Alerting thresholds and rollback procedures codified.
  - Updated documentation and diagrams reflecting operational flows.

## Notes on Sequencing (C vs D)
- **Do Option C first for functional coverage**, then layer Option D for reproducibility and lifecycle control. Option D depends on having a runnable DSPy pipeline.
- **Parallelizable work:** docs/diagram updates and feature-flag scaffolding can start early; MLflow environment setup can proceed while DSPy prototype is built.
- **Minimal viable path:** Phase 1 (DSPy) → Phase 2 (MLflow logging) → Phase 3 (registry integration) → Phase 4 (ops hardening).

