# Phase 5 — Titan AI Platform

**Status:** Not started  
**Languages:** Python, Rust, C++, CUDA  
**Boundary:** Aether runs inference. Titan trains/fine-tunes/evaluates models. Phase 6 provides shared Rust tensor primitives.

## Ordered Tasks

### 5.1 Dataset Builder
- Create `titan/dataset_builder.py` with prepare/clean/validate/augment pipeline.
- REST API: `POST /titan/datasets`, `GET /titan/datasets/{id}`.
- Register in `ServiceContainer` as `titan_dataset_builder`.

### 5.2 Tokenizer Engine
- Rust crate `crates/titan-tokenizer` with encode/decode/special-tokens.
- Python bindings via `pyo3`.
- Register as Aether provider capability.

### 5.3 Fine-Tuning Pipelines
- `titan/finetune.py`: SFT, DPO, RLHF, PPO orchestration.
- CUDA kernel dispatch via `crates/titan-engine` (Phase 6 stub).
- REST API: `POST /titan/finetune`, `GET /titan/finetune/{job_id}`.

### 5.4 Evaluation & Quantization
- `titan/evaluation.py`: benchmark runners, graders, eval pipelines.
- `titan/quantization.py`: INT8/INT4, GPTQ, AWQ, GGUF conversion wrappers.
- Store results in knowledge graph.

### 5.5 Model Registry
- `titan/registry.py`: register, version, tag, deploy fine-tuned models.
- Integration with Aether provider layer: Titan registers completed models as new providers.
- REST API: `POST /titan/models`, `GET /titan/models`.

### 5.6 Experiment Tracking
- PostgreSQL + file storage for metrics, checkpoints, comparisons.
- `titan/experiments.py`: log metrics, compare runs.

## Validation
- Fine-tune a small model, evaluate, quantize, register, and serve via Aether.
- `pytest tests/test_titan_*.py` passes.
- Rust `cargo test` in `crates/titan-tokenizer` passes.

## Dependencies
- Phase 3 (Aether) complete — inference runtime available.
- Phase 6 (High Performance Engine) starts in parallel for tensor primitives.
