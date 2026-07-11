import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from backend.main import knowledge_graph


def _make_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine), path


def _seed(engine, session_factory, count):
    from knowledge.node import KnowledgeNode
    from knowledge.edge import KnowledgeEdge

    node_objs = [
        KnowledgeNode(node_key=f"n{i}", node_type="concept", label=f"Node {i}")
        for i in range(count)
    ]
    session = session_factory()
    session.bulk_save_objects(node_objs)
    session.commit()

    edge_objs = [
        KnowledgeEdge(
            subject_node_id=i + 1,
            predicate="related_to",
            object_node_id=(i % (count - 1)) + 1,
            source="scaling-test",
        )
        for i in range(count)
    ]
    session.bulk_save_objects(edge_objs)
    session.commit()
    session.close()


def test_graph_truncates_over_limit():
    engine, session_factory, path = _make_session()
    try:
        _seed(engine, session_factory, 30000)
        session = session_factory()
        result = knowledge_graph(db=session, container=object())
        session.close()

        assert len(result["nodes"]) <= 10000
        assert len(result["edges"]) <= 10000
        assert result["truncated"] is True
        assert result["truncated_total"] == 30000
    finally:
        engine.dispose()
        os.remove(path)


def test_graph_not_truncated_at_limit():
    engine, session_factory, path = _make_session()
    try:
        _seed(engine, session_factory, 10000)
        session = session_factory()
        result = knowledge_graph(db=session, container=object())
        session.close()

        assert len(result["nodes"]) == 10000
        assert result["truncated"] is False
        assert result["truncated_total"] == 10000
    finally:
        engine.dispose()
        os.remove(path)
