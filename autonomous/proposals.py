"""
Engineering Proposal (RFC 0004)
-----------------------------------------
A proposal is a small, structured description of a change — never
free-form code execution. v0.1 supports exactly one change_type:
"add_twin_field", matching RFC 0004's own milestone example. Extend
the whitelist deliberately, one change_type at a time, rather than
ever accepting arbitrary code to run.
"""

from dataclasses import dataclass, asdict

SUPPORTED_CHANGE_TYPES = ("add_twin_field",)


@dataclass
class Proposal:
    name: str
    description: str
    change_type: str
    payload: dict

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if self.change_type not in SUPPORTED_CHANGE_TYPES:
            raise ValueError(
                f"Unsupported change_type '{self.change_type}'. "
                f"v0.1 only supports: {SUPPORTED_CHANGE_TYPES}. "
                f"This is a deliberate whitelist, not a missing feature."
            )
        if self.change_type == "add_twin_field":
            if "field_name" not in self.payload or "default_value" not in self.payload:
                raise ValueError(
                    "add_twin_field requires payload keys: field_name, default_value"
                )
