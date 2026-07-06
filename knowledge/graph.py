from __future__ import annotations

import json

from sqlalchemy.orm import Session

from knowledge.edge import KnowledgeEdge
from knowledge.node import KnowledgeNode
from knowledge.provenance import Provenance


class KnowledgeGraph:
    def get_or_create_node(
        self,
        db: Session,
        node_key: str,
        node_type: str,
        label: str,
        metadata: dict | None = None,
    ) -> KnowledgeNode:
        node = db.query(KnowledgeNode).filter(KnowledgeNode.node_key == node_key).first()
        if node is not None:
            return node
        node = KnowledgeNode(
            node_key=node_key,
            node_type=node_type,
            label=label,
            metadata_json=json.dumps(metadata or {}),
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return node

    def add_edge(
        self,
        db: Session,
        subject_node: KnowledgeNode,
        predicate: str,
        provenance: Provenance,
        confidence: float = 1.0,
        object_node: KnowledgeNode | None = None,
        object_value: str | None = None,
        supersedes_edge_id: int | None = None,
    ) -> KnowledgeEdge:
        edge = KnowledgeEdge(
            subject_node_id=subject_node.id,
            predicate=predicate,
            object_node_id=object_node.id if object_node else None,
            object_value=object_value,
            confidence=confidence,
            source=provenance.source,
            rationale=provenance.rationale,
            evidence_json=json.dumps(provenance.evidence),
            supersedes_edge_id=supersedes_edge_id,
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge

    def query_edges(
        self,
        db: Session,
        subject_key: str | None = None,
        predicate: str | None = None,
    ) -> list[KnowledgeEdge]:
        query = db.query(KnowledgeEdge).join(
            KnowledgeNode, KnowledgeNode.id == KnowledgeEdge.subject_node_id
        )
        if subject_key:
            query = query.filter(KnowledgeNode.node_key == subject_key)
        if predicate:
            query = query.filter(KnowledgeEdge.predicate == predicate)
        return query.order_by(KnowledgeEdge.created_at.asc()).all()
