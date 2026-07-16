"""
P2 Hardware Platform — persistence models.

Tracks HAL transport conformance results and signed firmware flash
attempts (with rollback events) so hardware operations are auditable
and reproducible.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Float, Text

from core.database import Base


class HALProtocolTest(Base):
    __tablename__ = "hal_protocol_tests"

    id = Column(String, primary_key=True)
    transport = Column(String, index=True, nullable=False)  # USB/Serial/Network/GPIO
    target = Column(String, index=True, nullable=False)
    handshake_success = Column(Boolean, default=False, nullable=False)
    latency_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FirmwareFlashLog(Base):
    __tablename__ = "firmware_flash_log"

    id = Column(String, primary_key=True)
    device_id = Column(String, index=True, nullable=False)
    firmware_version = Column(String, nullable=False)
    firmware_path = Column(String, nullable=True)
    signature = Column(Text, nullable=True)
    signature_valid = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="attempted", nullable=False)  # attempted|success|rolled_back
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
