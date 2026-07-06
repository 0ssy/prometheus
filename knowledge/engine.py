from __future__ import annotations

from sqlalchemy.orm import Session

from knowledge.graph import KnowledgeGraph
from knowledge.learning import LearningStore
from knowledge.ontology import OntologyRegistry
from knowledge.provenance import Provenance
from knowledge.query import KnowledgeQueryEngine


def _infer_node_type(node_key: str) -> str:
    if node_key.startswith("device.") or node_key.startswith("sim_") or node_key.startswith(
        "virtual::"
    ):
        return "Device"
    if node_key.startswith("plugin.") or node_key == "echo":
        return "Plugin"
    if node_key.startswith("agent."):
        return "Agent"
    if node_key.startswith("capability.") or ".recover" in node_key:
        return "Capability"
    return "Entity"


class KnowledgeEngine:
    def __init__(self):
        self.graph = KnowledgeGraph()
        self.query = KnowledgeQueryEngine()
        self.ontology = OntologyRegistry()
        self.learning = LearningStore()

    def record_fact(
        self,
        db: Session,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
        provenance: Provenance | None = None,
    ):
        provenance = provenance or Provenance(
            source="system", rationale="fact assertion", evidence={}
        )
        subject_node = self.graph.get_or_create_node(
            db,
            node_key=subject,
            node_type=_infer_node_type(subject),
            label=subject,
        )
        object_node = None
        object_value = obj
        if "." in obj or obj.startswith("virtual::"):
            object_node = self.graph.get_or_create_node(
                db,
                node_key=obj,
                node_type=_infer_node_type(obj),
                label=obj,
            )
            object_value = None
        return self.graph.add_edge(
            db,
            subject_node=subject_node,
            predicate=predicate,
            object_node=object_node,
            object_value=object_value,
            confidence=confidence,
            provenance=provenance,
        )

    def record_capability_support(self, db: Session, device_id: str, capability_name: str):
        device_key = f"device.{device_id}"
        capability_key = capability_name
        return self.record_fact(
            db,
            subject=device_key,
            predicate="supports_capability",
            obj=capability_key,
            confidence=0.95,
            provenance=Provenance(
                source="capability_manager",
                rationale="capability registered for device",
                evidence={"device_id": device_id, "capability_name": capability_name},
            ),
        )

    def record_capability_execution(
        self, db: Session, device_id: str, capability_name: str, success: bool
    ):
        device_key = f"device.{device_id}"
        cap_node = capability_name
        self.record_fact(
            db,
            subject=device_key,
            predicate="capability_executed",
            obj=cap_node,
            confidence=1.0 if success else 0.6,
            provenance=Provenance(
                source="capability_manager",
                rationale="capability execution observed",
                evidence={"success": success},
            ),
        )

    def record_simulation(
        self, db: Session, device_id: str, failure_mode: str, risk: str, recommended: str
    ):
        outcome = "failed" if risk == "high" else "passed"
        self.record_fact(
            db,
            subject=f"device.{device_id}",
            predicate="simulation_outcome",
            obj=f"{outcome}:{failure_mode}:{risk}",
            confidence=0.9,
            provenance=Provenance(
                source="simulation_engine",
                rationale="simulation result",
                evidence={"failure_mode": failure_mode, "risk": risk},
            ),
        )
        self.record_fact(
            db,
            subject=f"recommendation.{device_id}.{failure_mode}",
            predicate="recommended_capability",
            obj=recommended,
            confidence=0.85,
            provenance=Provenance(
                source="reasoning_pipeline",
                rationale="recommended action from workflow",
                evidence={"device_id": device_id, "failure_mode": failure_mode},
            ),
        )
        self.record_fact(
            db,
            subject=f"recommendation.{device_id}.{failure_mode}",
            predicate="generated_by_plugin",
            obj="plugin.reasoning_pipeline",
            confidence=0.9,
            provenance=Provenance(
                source="reasoning_pipeline",
                rationale="recommendation provenance",
                evidence={"pipeline": "reasoning.pipeline"},
            ),
        )

    def record_learning(
        self, db: Session, scenario_key: str, outcome: str, confidence: float, context: dict
    ):
        return self.learning.record(
            db,
            scenario_key=scenario_key,
            outcome=outcome,
            confidence=confidence,
            context=context,
        )
