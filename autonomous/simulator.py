"""
Engineering Simulator (RFC 0004)
-----------------------------------------
Applies a Proposal to a COPY of an existing DeviceTwin dict — never
the live twin, never a real file on disk.
"""
import copy
from .proposals import Proposal


def simulate_proposal(proposal: Proposal, base_twin_dict: dict) -> dict:
    proposal.validate()
    simulated = copy.deepcopy(base_twin_dict)

    if proposal.change_type == "add_twin_field":
        field_name = proposal.payload["field_name"]
        default_value = proposal.payload["default_value"]
        simulated.setdefault("sensors", {})
        simulated["sensors"][field_name] = default_value

    return simulated
