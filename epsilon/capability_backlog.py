"""
Capability Backlog (Phase Epsilon)
-----------------------------------------
Every time we discover a genuine AI limitation, it goes here.
This is a living research roadmap, not a wishlist.

For each limitation, we ask:
1. Is it fundamentally impossible?
2. If not, can we extend AI with tools, hardware, or software to address it?
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CapabilityLimitation:
    id: str
    description: str
    fundamental: bool
    extension_strategy: str
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CapabilityBacklog:
    limitations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def register_limitation(
    limitation_id: str,
    description: str,
    fundamental: bool,
    extension_strategy: str,
) -> CapabilityLimitation:
    limitation = CapabilityLimitation(
        id=limitation_id,
        description=description,
        fundamental=fundamental,
        extension_strategy=extension_strategy,
    )
    logger.info(f"Registered capability limitation: {limitation_id} — {description}")
    return limitation


def get_backlog() -> CapabilityBacklog:
    return CapabilityBacklog(limitations=[
        CapabilityLimitation(
            id="LIM-001",
            description="AI cannot reliably verify every factual claim without external verification tools.",
            fundamental=False,
            extension_strategy="Integrate formal verification tools, cryptographic proof checkers, and multi-source fact-checking pipelines.",
        ),
        CapabilityLimitation(
            id="LIM-002",
            description="AI cannot understand the complete state of a physical machine without sensors.",
            fundamental=False,
            extension_strategy="Deploy sensor arrays (temperature, voltage, current, vibration) and feed telemetry into the knowledge graph.",
        ),
        CapabilityLimitation(
            id="LIM-003",
            description="AI cannot recover every device without manufacturer support.",
            fundamental=True,
            extension_strategy="Build manufacturer-specific recovery modules; fall back to generic low-level flash tools when official paths fail.",
        ),
        CapabilityLimitation(
            id="LIM-004",
            description="AI cannot remember everything forever without a durable memory store.",
            fundamental=False,
            extension_strategy="Persist all facts, twins, and history to SQLite/PostgreSQL with periodic backups and export/import.",
        ),
        CapabilityLimitation(
            id="LIM-005",
            description="AI cannot build hardware on its own.",
            fundamental=True,
            extension_strategy="Interface with PCB fab APIs, component distributors, and assembly houses via automated ordering pipelines.",
        ),
        CapabilityLimitation(
            id="LIM-006",
            description="AI cannot perform experiments in the physical world by itself.",
            fundamental=True,
            extension_strategy="Robot arms, environmental chambers, and automated test rigs controlled via Prometheus hardware abstraction layer.",
        ),
    ])
