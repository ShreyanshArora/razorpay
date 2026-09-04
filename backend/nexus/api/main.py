"""Phase 5b — the NEXUS FastAPI app."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from nexus.api.service import get_service

app = FastAPI(title="NEXUS API", version="0.1.0",
              description="Network-level fraud investigation & defensible decisions")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "nexus"}


@app.get("/api/overview")
def overview():
    return get_service().overview()


@app.get("/api/cases")
def cases():
    return get_service().list_cases()


@app.get("/api/cases/{cluster_id}")
def case(cluster_id: str):
    c = get_service().case(cluster_id)
    if not c:
        raise HTTPException(404, "cluster not found")
    return c


@app.get("/api/cases/{cluster_id}/graph")
def graph(cluster_id: str):
    g = get_service().graph_data(cluster_id)
    if not g:
        raise HTTPException(404, "cluster not found")
    return g


@app.get("/api/cases/{cluster_id}/audit")
def case_audit(cluster_id: str):
    return get_service().audit_events(cluster_id)


@app.post("/api/cases/{cluster_id}/execute")
def execute_case(cluster_id: str):
    return get_service().execute_case(cluster_id)


@app.get("/api/eval")
def eval_results():
    return get_service().eval_results()


@app.get("/api/audit")
def audit():
    return get_service().audit_events()
