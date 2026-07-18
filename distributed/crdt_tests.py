from __future__ import annotations

from distributed.crdt import (
    CrdtNode,
    GCounter,
    GSet,
    LWWRegister,
    ORSet,
    PNCounter,
    VectorClock,
)


class TestVectorClock:
    def test_increment_and_get(self):
        vc = VectorClock()
        vc.increment("a")
        assert vc.get("a") == 1
        vc.increment("a")
        assert vc.get("a") == 2

    def test_merge(self):
        vc1 = VectorClock()
        vc1.increment("a")
        vc2 = VectorClock()
        vc2.increment("b")
        vc1.merge(vc2)
        assert vc1.get("a") == 1
        assert vc1.get("b") == 1

    def test_merge_preserves_max(self):
        vc1 = VectorClock()
        vc1.increment("a")
        vc1.increment("a")
        vc2 = VectorClock()
        vc2.increment("a")
        vc1.merge(vc2)
        assert vc1.get("a") == 2

    def test_serialization(self):
        vc = VectorClock()
        vc.increment("a")
        vc.increment("b")
        data = vc.to_dict()
        restored = VectorClock.from_dict(data)
        assert restored.get("a") == 1
        assert restored.get("b") == 1


class TestGCounter:
    def test_increment_and_value(self):
        counter = GCounter()
        counter.increment("a", 3)
        counter.increment("b", 2)
        assert counter.value() == 5

    def test_merge(self):
        c1 = GCounter()
        c1.increment("a", 5)
        c2 = GCounter()
        c2.increment("a", 3)
        c2.increment("b", 4)
        c1.merge(c2)
        assert c1.value() == 9
        assert c1._counts["a"] == 5
        assert c1._counts["b"] == 4

    def test_merge_is_commutative(self):
        c1 = GCounter()
        c1.increment("a", 5)
        c2 = GCounter()
        c2.increment("a", 3)
        c2.increment("b", 4)
        c3 = GCounter()
        c3.merge(c1)
        c3.merge(c2)
        c4 = GCounter()
        c4.merge(c2)
        c4.merge(c1)
        assert c3.value() == c4.value()

    def test_serialization(self):
        counter = GCounter()
        counter.increment("a", 2)
        data = counter.to_dict()
        restored = GCounter.from_dict(data)
        assert restored.value() == 2
        assert restored._counts["a"] == 2


class TestPNCounter:
    def test_increment_decrement(self):
        counter = PNCounter()
        counter.increment("a", 5)
        counter.decrement("a", 2)
        assert counter.value() == 3

    def test_merge(self):
        c1 = PNCounter()
        c1.increment("a", 5)
        c1.decrement("a", 2)
        c2 = PNCounter()
        c2.increment("a", 3)
        c2.decrement("b", 1)
        c1.merge(c2)
        assert c1.value() == 5 - 3

    def test_serialization(self):
        counter = PNCounter()
        counter.increment("a", 3)
        counter.decrement("b", 1)
        data = counter.to_dict()
        restored = PNCounter.from_dict(data)
        assert restored.value() == 2

    def test_negative_value(self):
        counter = PNCounter()
        counter.decrement("a", 5)
        assert counter.value() == -5


class TestGSet:
    def test_add_and_has(self):
        gset = GSet()
        gset.add("x")
        gset.add("y")
        assert gset.has("x") is True
        assert gset.has("z") is False

    def test_remove_is_noop(self):
        gset = GSet()
        gset.add("x")
        gset.remove("x")
        assert gset.has("x") is True

    def test_merge(self):
        gset1 = GSet()
        gset1.add("a")
        gset2 = GSet()
        gset2.add("b")
        gset1.merge(gset2)
        assert gset1.has("a") is True
        assert gset1.has("b") is True

    def test_serialization(self):
        gset = GSet()
        gset.add("a")
        gset.add("b")
        data = gset.to_dict()
        restored = GSet.from_dict(data)
        assert restored.has("a") is True
        assert restored.has("b") is True

    def test_elements(self):
        gset = GSet()
        gset.add("a")
        gset.add("b")
        assert gset.elements() == {"a", "b"}


class TestLWWRegister:
    def test_set_and_get(self):
        reg = LWWRegister()
        reg.set("hello", timestamp=100.0, node_id="a")
        assert reg.get() == "hello"

    def test_last_write_wins(self):
        reg = LWWRegister()
        reg.set("first", timestamp=100.0, node_id="a")
        reg.set("second", timestamp=200.0, node_id="b")
        assert reg.get() == "second"

    def test_same_timestamp_node_id_tiebreak(self):
        reg = LWWRegister()
        reg.set("first", timestamp=100.0, node_id="b")
        reg.set("second", timestamp=100.0, node_id="a")
        assert reg.get() == "first"

    def test_merge(self):
        reg1 = LWWRegister()
        reg1.set("local", timestamp=100.0, node_id="a")
        reg2 = LWWRegister()
        reg2.set("remote", timestamp=200.0, node_id="b")
        reg1.merge(reg2)
        assert reg1.get() == "remote"

    def test_serialization(self):
        reg = LWWRegister()
        reg.set("val", timestamp=50.0, node_id="n1")
        data = reg.to_dict()
        restored = LWWRegister.from_dict(data)
        assert restored.get() == "val"
        assert restored._timestamp == 50.0
        assert restored._node_id == "n1"


class TestORSet:
    def test_add_and_has(self):
        orset = ORSet()
        orset.add("x")
        assert orset.has("x") is True
        assert orset.has("y") is False

    def test_remove(self):
        orset = ORSet()
        orset.add("x")
        orset.remove("x")
        assert orset.has("x") is False

    def test_merge(self):
        orset1 = ORSet()
        orset1.add("a")
        orset2 = ORSet()
        orset2.add("b")
        orset2.remove("b")
        orset1.merge(orset2)
        assert orset1.has("a") is True
        assert orset1.has("b") is False

    def test_merge_preserves_adds(self):
        orset1 = ORSet()
        orset1.add("a")
        orset2 = ORSet()
        orset2.add("a")
        orset2.add("b")
        orset1.merge(orset2)
        assert orset1.has("a") is True
        assert orset1.has("b") is True

    def test_serialization(self):
        orset = ORSet()
        orset.add("a")
        orset.add("b")
        data = orset.to_dict()
        restored = ORSet.from_dict(data)
        assert restored.has("a") is True
        assert restored.has("b") is True

    def test_elements(self):
        orset = ORSet()
        orset.add("a")
        orset.add("b")
        orset.remove("b")
        assert orset.elements() == {"a"}


class TestCrdtNode:
    def test_merge_nodes(self):
        node1 = CrdtNode(node_id="a")
        node1.counter.increment("a", 5)
        node1.set.add("item1")

        node2 = CrdtNode(node_id="b")
        node2.counter.increment("b", 3)
        node2.set.add("item2")

        node1.merge(node2)
        assert node1.counter.value() == 8
        assert node1.set.has("item1") is True
        assert node1.set.has("item2") is True

    def test_serialization_roundtrip(self):
        node = CrdtNode(node_id="test")
        node.counter.increment("a", 7)
        node.set.add("alpha")
        node.register.set("beta", timestamp=123.0, node_id="x")

        data = node.to_dict()
        restored = CrdtNode.from_dict(data)

        assert restored.node_id == "test"
        assert restored.counter.value() == 7
        assert restored.set.has("alpha") is True
        assert restored.register.get() == "beta"

    def test_vector_clock_merge_on_node_merge(self):
        node1 = CrdtNode(node_id="a")
        node1.vector_clock.increment("a")
        node2 = CrdtNode(node_id="b")
        node2.vector_clock.increment("b")
        node1.merge(node2)
        assert node1.vector_clock.get("a") == 1
        assert node1.vector_clock.get("b") == 1

    def test_node_timestamp_merge(self):
        node1 = CrdtNode(node_id="a", timestamp=100.0)
        node2 = CrdtNode(node_id="b", timestamp=200.0)
        node1.merge(node2)
        assert node1.timestamp == 200.0

    def test_from_dict_defaults(self):
        data = {"node_id": "default"}
        node = CrdtNode.from_dict(data)
        assert node.node_id == "default"
        assert node.counter.value() == 0
        assert node.timestamp == 0.0
