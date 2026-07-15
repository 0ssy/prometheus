"""
P2–P11 phase endpoints (FastAPI router).

Wires the per-phase Python services + SQL models into REST endpoints so
the Rust/TypeScript/Python layers are exercised end-to-end. Mounted by
``backend/main.py`` via ``app.include_router(phase_router)``.

Lazy-imports ``get_db``/``get_container`` from ``backend.main`` to avoid a
circular import at module load.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db

phase_router = APIRouter()


# --- P2 Hardware: signed flashing -----------------------------------------
@phase_router.post("/epsilon/firmware/flash")
def flash_firmware(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    from hardware.flash_service import FlashService, SigningVerifier

    verifier = SigningVerifier()
    try:
        return FlashService(verifier=verifier).flash(
            db,
            device_id=payload["device_id"],
            firmware_version=payload["firmware_version"],
            firmware_path=payload.get("firmware_path"),
            signature=payload.get("signature"),
            enforced=payload.get("enforced", True),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


# --- P3 Aether: provider routing ------------------------------------------
@phase_router.post("/aether/route")
def aether_route(payload: dict[str, Any] | None = None):
    from aether.runtime import AetherRuntime

    budget = (payload or {}).get("budget")
    return AetherRuntime().select_provider(budget)


# --- P4 Engineering: confidence-gated suggestions + approval -------------
@phase_router.post("/engineering/suggestions")
def create_suggestion(payload: dict[str, Any], db: Session = Depends(get_db)):
    from engineering.intelligence import EngineeringIntelligence, Suggestion

    ei = EngineeringIntelligence()
    rep = ei.submit(
        db,
        Suggestion(
            title=payload["title"],
            summary=payload.get("summary", ""),
            confidence=float(payload.get("confidence", 0.0)),
            details=payload.get("details"),
        ),
    )
    return {"id": rep.id, "status": rep.status, "confidence": rep.confidence}


@phase_router.get("/engineering/suggestions")
def list_suggestions(db: Session = Depends(get_db)):
    from engineering.models import EngineeringReport

    rows = db.query(EngineeringReport).all()
    return {"reports": [{"id": r.id, "title": r.title, "status": r.status, "confidence": r.confidence} for r in rows]}


@phase_router.post("/engineering/suggestions/{report_id}/approve")
def approve_suggestion(report_id: str, db: Session = Depends(get_db)):
    from engineering.intelligence import EngineeringIntelligence

    try:
        rep = EngineeringIntelligence().approve(db, report_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"id": rep.id, "status": rep.status, "approved": rep.approved}


# --- P5 Titan: license-gated dataset registration ------------------------
@phase_router.post("/titan/datasets/register")
def register_dataset(payload: dict[str, Any], db: Session = Depends(get_db)):
    from titan.governance import TitanGovernance, LicenseError

    try:
        ds = TitanGovernance().register_dataset(
            db,
            name=payload["name"],
            license=payload["license"],
            source_text=payload.get("source_text", ""),
            lineage=payload.get("lineage"),
        )
    except LicenseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": ds.id, "license": ds.license, "source_hash": ds.source_hash}


# --- P8 Cloud: tenant + billing -------------------------------------------
@phase_router.post("/cloud/tenant")
def create_tenant(payload: dict[str, Any], db: Session = Depends(get_db)):
    from enterprise.cloud import AuthService

    t = AuthService(db).create_tenant(payload["name"])
    return {"id": t.id, "name": t.name}


@phase_router.get("/cloud/status")
def cloud_status(db: Session = Depends(get_db)):
    from enterprise.models import Tenant, Invoice, UsageEvent

    return {
        "tenants": db.query(Tenant).count(),
        "invoices": db.query(Invoice).count(),
        "usage_events": db.query(UsageEvent).count(),
    }


# --- P10 Marketplace governance -------------------------------------------
@phase_router.get("/marketplace/approvals")
def list_approvals(db: Session = Depends(get_db)):
    from marketplace.governance import MarketplaceGovernance

    pending = MarketplaceGovernance().pending(db)
    return {"pending": [{"id": a.id, "name": a.name, "category": a.category} for a in pending]}


@phase_router.post("/marketplace/approvals/{approval_id}/review")
def review_approval(approval_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    from marketplace.governance import MarketplaceGovernance

    try:
        rec = MarketplaceGovernance().review(
            db,
            approval_id,
            decision=payload["decision"],
            reviewer=payload.get("reviewer", "reviewer"),
            quality_score=float(payload.get("quality_score", 0.0)),
            notes=payload.get("notes"),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"id": rec.id, "status": rec.status}


# --- P11 OS status ---------------------------------------------------------
@phase_router.get("/os/status")
def os_status(db: Session = Depends(get_db)):
    from core.enterprise_workflow_runner import EnterpriseWorkflowRunner
    from core.enterprise_workflow import EnterpriseWorkflow

    rate = EnterpriseWorkflowRunner().success_rate(db)
    return {
        "enterprise_workflows": db.query(EnterpriseWorkflow).count(),
        "end_to_end_success_rate": rate,
    }
