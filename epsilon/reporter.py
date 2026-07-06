"""
Engineering Report (RFC 0004)
-----------------------------------------
The report format matters as much as the generated change — it's what
makes autonomous output auditable later. deployed is hardcoded False
for v0.1 — see RFC 0004 non-goals.
"""
from dataclasses import dataclass, asdict


@dataclass
class EngineeringReport:
    proposal_name: str
    change_type: str
    what_changed: str
    tests_run: list
    all_tests_passed: bool
    what_was_not_tested: list
    residual_risk: str
    deployed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def build_report(proposal, test_results) -> EngineeringReport:
    all_passed = all(t.passed for t in test_results)

    what_changed = (
        f"Proposed adding sensor field '{proposal.payload.get('field_name')}' "
        f"with default value {proposal.payload.get('default_value')!r} to the "
        f"DeviceTwin schema (simulated only — delta/twin.py was not modified)."
    )

    what_was_not_tested = [
        "Behavior against a real, live device twin under concurrent writes.",
        "Whether existing agents or plugins that read twin.sensors expect a fixed schema.",
        "Any interaction with Gamma's recovery_options field, which this proposal does not touch.",
    ]

    residual_risk = (
        "Low for this specific change (additive, optional field) — but this report "
        "covers exactly one proposal type. 'All tests passed' here is not a general "
        "guarantee for change types beyond add_twin_field."
    )

    return EngineeringReport(
        proposal_name=proposal.name,
        change_type=proposal.change_type,
        what_changed=what_changed,
        tests_run=[t.to_dict() for t in test_results],
        all_tests_passed=all_passed,
        what_was_not_tested=what_was_not_tested,
        residual_risk=residual_risk,
        deployed=False,
    )
