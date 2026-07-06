from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Provenance:
    source: str
    rationale: str
    evidence: dict

    def to_dict(self) -> dict:
        return asdict(self)
