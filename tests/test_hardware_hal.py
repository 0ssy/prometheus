"""P2 Hardware Platform — HAL conformance + signed flashing tests."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import core.database as cd
from hardware.flash_service import FlashService, HALConformance, SigningVerifier
from hardware.hal_models import FirmwareFlashLog, HALProtocolTest


@pytest.fixture
def session(tmp_path, monkeypatch):
    db_path = tmp_path / "p2.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(cd, "engine", engine)
    monkeypatch.setattr(cd, "SessionLocal", factory)
    cd.init_db()
    with factory() as s:
        yield s
    engine.dispose()


def _keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv, pub


def test_hal_conformance_records_and_rates(session):
    hal = HALConformance()
    targets = [("USB", "dev-1"), ("Serial", "dev-2"), ("GPIO", "unknown")]
    results = hal.run(session, targets)
    assert len(results) == 3
    rate = hal.success_rate(results)
    assert rate == pytest.approx(2 / 3, abs=1e-3)
    rows = session.query(HALProtocolTest).all()
    assert len(rows) == 3
    assert all(r.transport in ("USB", "Serial", "GPIO") for r in rows)


def test_signed_flash_enforced_rejects_unsigned(session):
    priv, pub = _keypair()
    svc = FlashService(verifier=SigningVerifier(public_key_pem=pub))
    with pytest.raises(PermissionError, match="signed-only"):
        svc.flash(
            session,
            device_id="dev-1",
            firmware_version="1.0.0",
            firmware_path="/tmp/fw.bin",
            signature=None,
            enforced=True,
        )
    log = session.query(FirmwareFlashLog).one()
    assert log.signature_valid is False
    assert log.status == "rolled_back"


def test_signed_flash_verified_succeeds(session):

    priv, pub = _keypair()
    svc = FlashService(verifier=SigningVerifier(public_key_pem=pub))
    payload = b"dev-1:1.0.0"
    sig = priv.sign(payload).hex()
    result = svc.flash(
        session,
        device_id="dev-1",
        firmware_version="1.0.0",
        firmware_path="/tmp/fw.bin",
        signature=sig,
        enforced=True,
    )
    assert result["status"] == "success"
    assert result["signed"] is True
    log = session.query(FirmwareFlashLog).one()
    assert log.signature_valid is True


def test_flash_log_rollback_recorded(session):
    svc = FlashService(verifier=SigningVerifier())
    log_id = str(uuid.uuid4())
    session.add(
        FirmwareFlashLog(
            id=log_id, device_id="dev-9", firmware_version="0.9",
            signature_valid=True, status="success",
        )
    )
    session.commit()
    svc.record_rollback(session, log_id, "post-flash diagnostics failed")
    row = session.get(FirmwareFlashLog, log_id)
    assert row.status == "rolled_back"
    assert row.error == "post-flash diagnostics failed"
