"""
Recovery Planner (RFC 0002)
-----------------------------------------
Given inspected device state, proposes an ORDERED LIST of official
recovery options. It never executes anything — that is a binding
design property of this module, not a missing feature to add later.

Simple rule-based logic for v0.1, deliberately — not ML.
"""

from dataclasses import dataclass, field, asdict
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RecoveryStep:
    order: int
    action: str
    description: str
    official: bool = True


@dataclass
class RecoveryPlan:
    device_id: str
    scenario: str
    steps: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "scenario": self.scenario,
            "steps": [asdict(s) for s in self.steps],
        }


def plan_recovery(
    device_id: str, boot_chain_status: str, partition_scheme: str
) -> RecoveryPlan:
    steps = []

    if boot_chain_status == "invalid":
        steps.append(
            RecoveryStep(
                order=1,
                action="halt_and_report",
                description="Boot signature is invalid. Do not proceed with any flash or "
                "repair action automatically. Report to the device owner for "
                "manual verification before anything else happens.",
            )
        )
        steps.append(
            RecoveryStep(
                order=2,
                action="official_reflash_guide",
                description="If the owner confirms this is expected (e.g. intentional custom "
                "firmware), point them to the manufacturer's official reflash "
                "documentation. Prometheus does not perform the reflash.",
            )
        )
    elif boot_chain_status == "unknown":
        steps.append(
            RecoveryStep(
                order=1,
                action="gather_more_info",
                description="No signature/public key was available to verify the boot chain. "
                "Recommend locating the manufacturer's public key or official "
                "firmware source before planning further.",
            )
        )
    else:  # "valid"
        steps.append(
            RecoveryStep(
                order=1,
                action="no_action_needed",
                description="Boot chain verified valid. No recovery action indicated from "
                "this signal alone.",
            )
        )

    if partition_scheme == "unknown":
        steps.append(
            RecoveryStep(
                order=len(steps) + 1,
                action="partition_table_repair_guide",
                description="Partition table could not be parsed as GPT or MBR. Point the "
                "owner to their OS/manufacturer's official disk repair tool — do "
                "not attempt an automatic rewrite of the partition table.",
            )
        )

    scenario = f"boot_chain={boot_chain_status}, partition_scheme={partition_scheme}"
    logger.info(
        f"Recovery plan generated for {device_id}: {scenario} -> {len(steps)} step(s)"
    )
    return RecoveryPlan(device_id=device_id, scenario=scenario, steps=steps)
