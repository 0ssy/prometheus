from __future__ import annotations



from security.authorization import Authorizer
from security.permissions import PermissionRegistry, default_registry
from security.auditing import AuditLogger
from security.integrity import IntegrityVerifier


def test_authorizer_authorize_allowed():
    authorizer = Authorizer()
    result = authorizer.authorize(
        actor="user1",
        action="device.connect",
        resource="dev1",
        permissions={"device.connect"},
    )
    assert result.allowed is True
    assert result.reason == "Authorized"


def test_authorizer_authorize_denied_missing_permissions():
    authorizer = Authorizer()
    result = authorizer.authorize(
        actor="user1",
        action="device.read",
        resource="dev1",
        permissions={"device.connect"},
    )
    assert result.allowed is False
    assert "Missing permissions" in result.reason


def test_authorizer_authorize_denied_anonymous():
    authorizer = Authorizer()
    result = authorizer.authorize(
        actor="",
        action="device.connect",
        resource="dev1",
        permissions={"device.connect"},
    )
    assert result.allowed is False
    assert "anonymous" in result.reason


def test_authorizer_require_permission_decorator():
    authorizer = Authorizer()
    call_count = 0

    @authorizer.require_permission("device.connect")
    def connect(actor="", action="", resource="", permissions=None):
        nonlocal call_count
        call_count += 1
        return "connected"

    result = connect(actor="user1", action="device.connect", resource="dev1", permissions={"device.connect"})
    assert result == "connected"
    assert call_count == 1


def test_permission_registry_register_and_get():
    from security.permissions import Permission

    registry = PermissionRegistry()
    registry.register(Permission(name="test.perm", description="desc", category="cat"))
    perm = registry.get("test.perm")
    assert perm is not None
    assert perm.description == "desc"


def test_permission_registry_list_by_category():
    registry = default_registry
    perms = registry.list_by_category("device")
    names = [p.name for p in perms]
    assert "device.connect" in names


def test_permission_registry_required_for():
    registry = default_registry
    required = registry.required_for("device.connect")
    assert required == {"device.connect"}


def test_default_registry_has_hardware_permissions():
    registry = default_registry
    required = registry.required_for("hardware.session.create")
    assert "hardware.session.create" in required


def test_audit_logger_record_and_query():
    logger = AuditLogger()
    entry = logger.record("actor1", "action1", "res1", "allowed")
    assert entry.actor == "actor1"

    results = logger.query(actor="actor1")
    assert len(results) == 1
    assert results[0] is entry


def test_audit_logger_export_json():
    logger = AuditLogger()
    logger.record("a", "b", "c", "ok")
    exported = logger.export(format="json")
    assert "a" in exported
    assert "b" in exported


def test_integrity_verifier_compute_hash():
    verifier = IntegrityVerifier()
    digest = verifier.compute_hash(b"hello", algorithm="sha256")
    assert len(digest) == 64


def test_integrity_verifier_verify():
    verifier = IntegrityVerifier()
    data = b"hello"
    expected = verifier.compute_hash(data)
    check = verifier.verify("target", expected, data=data)
    assert check.passed is True
    assert check.target == "target"


def test_integrity_verifier_attest():
    verifier = IntegrityVerifier()
    result = verifier.attest(b"data", {"key": "value"})
    assert result["attested"] is True
    assert "signature" in result
