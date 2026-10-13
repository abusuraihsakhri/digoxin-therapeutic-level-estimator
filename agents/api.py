"""
FastAPI REST API Server for Digoxin Therapeutic Level Estimator.
"""
import os
import secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Digoxin Therapeutic Level Estimator API",
    description="Educational pharmacokinetic calculator and auxiliary audit endpoints",
    version="3.0.0",
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


@app.get("/", include_in_schema=False)
def index():
    """Serve the same static offline-capable calculator in API mode."""
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "digoxin-therapeutic-level-estimator", "version": "3.0.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        # Validate the complete payload, not only the three identifier fields.
        import json
        PHIGuard.assert_no_phi(json.dumps(payload.model_dump(), allow_nan=False))
        dossier = supervisor.process_task(payload)
        return dossier.to_dict()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        from .base import SecurityException
        if isinstance(exc, SecurityException):
            raise HTTPException(status_code=422, detail="Input contains a potentially sensitive identifier")
        raise


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs(x_audit_key: str | None = Header(default=None)):
    """Never expose the in-memory audit trail without explicit authorization."""
    expected = os.getenv("DIGOXIN_AUDIT_ADMIN_KEY", "")
    if not expected or not x_audit_key or not secrets.compare_digest(x_audit_key, expected):
        raise HTTPException(status_code=403, detail="Audit log access is disabled or unauthorized")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
