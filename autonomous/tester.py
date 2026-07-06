"""
Engineering Tester (RFC 0004)
-----------------------------------------
Runs a small set of explicit, named checks comparing the original
twin to the simulated one.
"""

from dataclasses import dataclass, asdict
import json


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def run_tests(original: dict, simulated: dict, proposal) -> list[TestResult]:
    results = []

    unaffected_keys = [k for k in original if k != "sensors"]
    unchanged = all(original.get(k) == simulated.get(k) for k in unaffected_keys)
    results.append(
        TestResult(
            name="unrelated_fields_unchanged",
            passed=unchanged,
            detail=(
                "All twin fields other than 'sensors' are identical to the original."
                if unchanged
                else "One or more unrelated fields changed unexpectedly."
            ),
        )
    )

    if proposal.change_type == "add_twin_field":
        field_name = proposal.payload["field_name"]
        expected = proposal.payload["default_value"]
        present = simulated.get("sensors", {}).get(field_name) == expected
        results.append(
            TestResult(
                name="new_field_present_with_default",
                passed=present,
                detail=(
                    f"sensors.{field_name} == {expected!r}"
                    if present
                    else f"sensors.{field_name} missing or has wrong value."
                ),
            )
        )

    try:
        json.dumps(simulated)
        serializes, detail = True, "Simulated twin serializes to JSON without error."
    except TypeError as e:
        serializes, detail = False, f"Simulated twin failed to serialize: {e}"
    results.append(
        TestResult(name="json_serializable", passed=serializes, detail=detail)
    )

    return results
