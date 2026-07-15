"""
Titan Service — Phase 5 unified entry point.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger

from titan.dataset_builder import DatasetBuilder
from titan.evaluation import evaluation, quantization
from titan.experiments import experiment_tracker
from titan.finetune import finetune
from titan.registry import model_registry
from titan.tokenizer import tokenizer_engine

logger = get_logger(__name__)


class TitanService:
    def __init__(self) -> None:
        self.dataset_builder = DatasetBuilder()
        self.tokenizer = tokenizer_engine
        self.finetune = finetune
        self.evaluation = evaluation
        self.quantization = quantization
        self.registry = model_registry
        self.experiments = experiment_tracker

    def list_modules(self) -> list[str]:
        return [
            "dataset_builder",
            "tokenizer",
            "finetune",
            "evaluation",
            "quantization",
            "registry",
            "experiments",
        ]

    def execute_workflow(self, module_name: str, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if module_name == "dataset_builder":
            return self._dataset(workflow, payload)
        if module_name == "tokenizer":
            return self._tokenizer(workflow, payload)
        if module_name == "finetune":
            return self._finetune(workflow, payload)
        if module_name == "evaluation":
            return self._evaluation(workflow, payload)
        if module_name == "quantization":
            return self._quantization(workflow, payload)
        if module_name == "registry":
            return self._registry(workflow, payload)
        if module_name == "experiments":
            return self._experiments(workflow, payload)
        raise ValueError(f"Unknown Titan module: {module_name}")

    def _dataset(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "prepare":
            return self.dataset_builder.prepare(
                payload.get("source_path", ""),
                payload.get("name", "dataset"),
                payload.get("format", "jsonl"),
            )
        if workflow == "pipeline":
            return self.dataset_builder.build_pipeline(
                payload.get("dataset_id", ""), payload.get("steps", []), payload
            )
        if workflow == "get":
            return self.dataset_builder.get(payload.get("dataset_id", ""))
        raise ValueError(f"Unknown dataset workflow: {workflow}")

    def _tokenizer(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "encode":
            return self.tokenizer.encode(payload.get("text", ""))
        if workflow == "decode":
            return self.tokenizer.decode(payload.get("ids", []))
        if workflow == "add_special_tokens":
            return self.tokenizer.add_special_tokens(payload.get("tokens", []))
        raise ValueError(f"Unknown tokenizer workflow: {workflow}")

    def _finetune(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "submit":
            return self.finetune.submit(payload)
        if workflow == "get":
            return self.finetune.get(payload.get("job_id", ""))
        if workflow == "list":
            return {"jobs": self.finetune.list_jobs()}
        if workflow == "run":
            return self.finetune.run_simulated(payload.get("job_id", ""))
        raise ValueError(f"Unknown finetune workflow: {workflow}")

    def _evaluation(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "benchmark":
            return self.evaluation.run_benchmark(
                payload.get("model_id", ""), payload.get("benchmark", "mmlu"), payload
            )
        if workflow == "pipeline":
            return self.evaluation.run_pipeline(
                payload.get("model_id", ""), payload.get("benchmarks", []), payload
            )
        if workflow == "grade":
            return self.evaluation.grade(payload.get("eval_id", ""), payload.get("rubric", {}))
        raise ValueError(f"Unknown evaluation workflow: {workflow}")

    def _quantization(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "quantize":
            return self.quantization.quantize(
                payload.get("model_id", ""),
                payload.get("method", "INT8"),
                int(payload.get("bits", 8)),
                payload,
            )
        if workflow == "convert":
            return self.quantization.convert(
                payload.get("model_id", ""), payload.get("target_format", "gguf"), payload
            )
        raise ValueError(f"Unknown quantization workflow: {workflow}")

    def _registry(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "register":
            return self.registry.register(payload)
        if workflow == "get":
            return self.registry.get(payload.get("model_id", ""))
        if workflow == "list":
            return self.registry.list_models(payload)
        if workflow == "version":
            return self.registry.version(payload.get("model_id", ""), payload.get("version", ""))
        if workflow == "tag":
            return self.registry.tag(payload.get("model_id", ""), payload.get("tags", []))
        if workflow == "deploy":
            return self.registry.deploy(payload.get("model_id", ""), payload)
        if workflow == "register_as_provider":
            return self.registry.register_as_provider(payload.get("model_id", ""))
        raise ValueError(f"Unknown registry workflow: {workflow}")

    def _experiments(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        if workflow == "start":
            return self.experiments.start(payload)
        if workflow == "log_metrics":
            return self.experiments.log_metrics(
                payload.get("experiment_id", ""), payload.get("metrics", {})
            )
        if workflow == "log_checkpoint":
            return self.experiments.log_checkpoint(
                payload.get("experiment_id", ""), payload.get("checkpoint_path", "")
            )
        if workflow == "complete":
            return self.experiments.complete(payload.get("experiment_id", ""))
        if workflow == "compare":
            return self.experiments.compare(payload.get("experiment_ids", []))
        if workflow == "list":
            return self.experiments.list_experiments()
        raise ValueError(f"Unknown experiments workflow: {workflow}")
