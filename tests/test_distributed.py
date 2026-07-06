from __future__ import annotations

from omega.distributed import (
    CapabilitySynchronizer,
    DistributedRuntime,
    KnowledgeSynchronizer,
    NodeRegistry,
)
from omega.distributed.node import NodeInfo, NodeStatus
from omega.distributed.sync import SyncDirection


def test_node_registry_register_and_list():
    registry = NodeRegistry()
    info = NodeInfo(node_id="n1", name="n1", host="localhost", port=8000, capabilities=["cap1"])
    registry.register(info)
    assert registry.get("n1") is info
    assert len(registry.list_online()) == 1
    assert registry.unregister("n1") is True
    assert registry.get("n1") is None


def test_node_registry_find_by_capability():
    registry = NodeRegistry()
    a = NodeInfo(node_id="a", name="a", host="h", port=1, capabilities=["compute", "storage"])
    b = NodeInfo(node_id="b", name="b", host="h", port=2, capabilities=["storage"])
    registry.register(a)
    registry.register(b)
    compute_nodes = registry.find_by_capability("compute")
    assert [n.node_id for n in compute_nodes] == ["a"]
    storage_nodes = registry.find_by_capability("storage")
    assert set(n.node_id for n in storage_nodes) == {"a", "b"}


def test_distributed_runtime_register_node():
    runtime = DistributedRuntime()
    node = runtime.register_node("n1", "localhost", 8000, ["cap1"])
    assert node.node_id == "n1"
    assert runtime.get_cluster_status()["online_nodes"] == 1
    assert runtime.get_cluster_status()["nodes"] == ["n1"]


def test_distributed_runtime_broadcast():
    runtime = DistributedRuntime()
    runtime.register_node("n1", "h", 1, [])
    runtime.register_node("n2", "h", 2, [])
    delivered = runtime.broadcast("task.assigned", {"payload": 1})
    assert set(delivered) == {"n1", "n2"}


def test_distributed_runtime_elect_leader():
    runtime = DistributedRuntime()
    assert runtime.elect_leader() is None
    runtime.register_node("leader", "h", 1, [])
    runtime.register_node("follower", "h", 2, [])
    assert runtime.elect_leader() == "leader"


def test_knowledge_synchronizer_sync():
    sync = KnowledgeSynchronizer()
    record = sync.sync("src", "dst", SyncDirection.BIDIRECTIONAL)
    assert record.source_node == "src"
    assert record.target_node == "dst"
    assert record.direction == SyncDirection.BIDIRECTIONAL
    assert len(sync._completed) == 1


def test_capability_synchronizer_sync():
    sync = CapabilitySynchronizer()
    result = sync.sync_capabilities("src", "dst")
    assert result["source"] == "src"
    assert result["target"] == "dst"
    sync.register_remote_capability("dst", {"name": "cap-x"})
    assert sync._remote_capabilities["dst"][0]["name"] == "cap-x"
