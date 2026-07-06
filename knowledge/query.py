from __future__ import annotations

from sqlalchemy.orm import Session, aliased

from knowledge.edge import KnowledgeEdge
from knowledge.node import KnowledgeNode


class KnowledgeQueryEngine:
    def devices_supporting_recovery(self, db: Session) -> list[str]:
        subject = aliased(KnowledgeNode)
        object_node = aliased(KnowledgeNode)
        rows = (
            db.query(subject.node_key)
            .join(KnowledgeEdge, KnowledgeEdge.subject_node_id == subject.id)
            .join(object_node, object_node.id == KnowledgeEdge.object_node_id)
            .filter(KnowledgeEdge.predicate == "supports_capability")
            .filter(object_node.node_key.like("%.recover"))
            .all()
        )
        return sorted({row[0] for row in rows})

    def simulations_failed(self, db: Session) -> list[dict]:
        subject = aliased(KnowledgeNode)
        rows = (
            db.query(subject.node_key, KnowledgeEdge.object_value, KnowledgeEdge.confidence)
            .join(KnowledgeEdge, KnowledgeEdge.subject_node_id == subject.id)
            .filter(KnowledgeEdge.predicate == "simulation_outcome")
            .filter(KnowledgeEdge.object_value.like("failed:%"))
            .all()
        )
        return [
            {"device": row[0], "outcome": row[1], "confidence": row[2]}
            for row in rows
        ]

    def capabilities_never_executed(self, db: Session) -> list[str]:
        capability_nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.node_type == "Capability"
        ).all()
        executed_edges = (
            db.query(KnowledgeEdge.object_node_id)
            .filter(KnowledgeEdge.predicate == "capability_executed")
            .all()
        )
        executed_ids = {row[0] for row in executed_edges if row[0] is not None}
        return sorted(
            [node.node_key for node in capability_nodes if node.id not in executed_ids]
        )

    def plugins_for_recommendation(self, db: Session, recommendation_key: str) -> list[str]:
        subject = aliased(KnowledgeNode)
        plugin_node = aliased(KnowledgeNode)
        rows = (
            db.query(plugin_node.node_key)
            .join(KnowledgeEdge, KnowledgeEdge.subject_node_id == subject.id)
            .join(plugin_node, plugin_node.id == KnowledgeEdge.object_node_id)
            .filter(subject.node_key == recommendation_key)
            .filter(KnowledgeEdge.predicate == "generated_by_plugin")
            .all()
        )
        return sorted({row[0] for row in rows})
