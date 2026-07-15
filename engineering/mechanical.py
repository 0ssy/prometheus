"""
Mechanical Engineering Module
-----------------------------------------
Simulated mechanical workflows: stress analysis, motion simulation,
CAM toolpath generation, material checks.
"""

from dataclasses import dataclass, field, asdict
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StressResult:
    part_id: str
    max_stress_mpa: float
    safety_factor: float
    yield_mpa: float
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MotionSimResult:
    assembly_id: str
    joints: int
    range_of_motion_deg: float
    interference_detected: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ToolpathResult:
    part_id: str
    tool: str
    passes: int
    total_length_m: float
    estimated_time_min: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MaterialCheck:
    part_id: str
    material: str
    density_kg_m3: float
    tensile_mpa: float
    temperature_rating_c: float

    def to_dict(self) -> dict:
        return asdict(self)


class MechanicalModule:
    name = "mechanical"

    def execute(self, workflow: str, payload: dict) -> dict:
        if workflow == "analyze_stress":
            return self._analyze_stress(payload)
        if workflow == "run_motion_simulation":
            return self._run_motion_simulation(payload)
        if workflow == "generate_cam_toolpath":
            return self._generate_cam_toolpath(payload)
        if workflow == "check_materials":
            return self._check_materials(payload)
        raise ValueError(f"Unknown mechanical workflow: {workflow}")

    def _analyze_stress(self, payload: dict) -> dict:
        part_id = payload.get("part_id", "")
        max_stress = payload.get("max_stress_mpa", 180.0)
        yield_strength = payload.get("yield_mpa", 250.0)
        safety_factor = yield_strength / max_stress if max_stress > 0 else 0.0
        passed = safety_factor >= 1.5
        logger.info(f"Stress analysis for {part_id}: factor={safety_factor:.2f}")
        return StressResult(
            part_id=part_id,
            max_stress_mpa=max_stress,
            safety_factor=round(safety_factor, 2),
            yield_mpa=yield_strength,
            passed=passed,
        ).to_dict()

    def _run_motion_simulation(self, payload: dict) -> dict:
        assembly_id = payload.get("assembly_id", "")
        joints = payload.get("joints", 6)
        logger.info(f"Motion simulation for {assembly_id}")
        return MotionSimResult(
            assembly_id=assembly_id,
            joints=joints,
            range_of_motion_deg=180.0,
            interference_detected=False,
        ).to_dict()

    def _generate_cam_toolpath(self, payload: dict) -> dict:
        part_id = payload.get("part_id", "")
        tool = payload.get("tool", "endmill_6mm")
        passes = payload.get("passes", 3)
        logger.info(f"Generating CAM toolpath for {part_id}")
        return ToolpathResult(
            part_id=part_id,
            tool=tool,
            passes=passes,
            total_length_m=2.4,
            estimated_time_min=18.5,
        ).to_dict()

    def _check_materials(self, payload: dict) -> dict:
        part_id = payload.get("part_id", "")
        material = payload.get("material", "aluminum_6061")
        logger.info(f"Material check for {part_id}: {material}")
        return MaterialCheck(
            part_id=part_id,
            material=material,
            density_kg_m3=2710.0,
            tensile_mpa=310.0,
            temperature_rating_c=120.0,
        ).to_dict()
