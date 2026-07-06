from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Session

from core.database import Base


class LearningExperience(Base):
    __tablename__ = "learning_experiences"

    id = Column(Integer, primary_key=True, index=True)
    scenario_key = Column(String, index=True, nullable=False)
    outcome = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    context_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LearningStore:
    def record(
        self,
        db: Session,
        scenario_key: str,
        outcome: str,
        confidence: float,
        context: dict,
    ) -> LearningExperience:
        experience = LearningExperience(
            scenario_key=scenario_key,
            outcome=outcome,
            confidence=confidence,
            context_json=json.dumps(context),
        )
        db.add(experience)
        db.commit()
        db.refresh(experience)
        return experience

    def recall(self, db: Session, scenario_key: str | None = None) -> list[LearningExperience]:
        query = db.query(LearningExperience)
        if scenario_key:
            query = query.filter(LearningExperience.scenario_key == scenario_key)
        return query.order_by(LearningExperience.created_at.desc()).all()
