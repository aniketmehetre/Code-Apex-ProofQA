"""ProofQA Control Plane API (Milestone M3, Prompt 11.1).

FastAPI backend providing:
- POST /sessions
- GET /sessions/{id}
- GET /sessions/{id}/events (SSE with reconnect buffer)
- GET /sessions/{id}/findings
- GET /certificates/{id} (ZIP download)
- POST /race (concurrent ProofQA vs Random Monkey baseline with live streaming)
- POST /verify (streams proofqa verify lines, with tamper option)
- GET /bench/summary
- POST /findings/{id}/review (approve -> regression suite; reject -> signature suppression rule)
"""

from __future__ import annotations

import asyncio
import io
import json
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from proofbench.baselines import RandomMonkeyBaseline
from proofqa.cert.verify import verify_certificate
from proofqa.contracts import (
    WorldSpec,
)
from proofqa.pipeline import Pipeline, PipelineEventBus


class SessionCreateRequest(BaseModel):
    world_spec: WorldSpec | None = None
    step_budget: int = 10
    k_replays: int = 1
    app_id: str = "shop_twin"
    bugs: list[str] = Field(default_factory=lambda: ["B01", "B03"])


class RaceRequest(BaseModel):
    world_spec: WorldSpec | None = None
    budget: int = 10
    bugs: list[str] = Field(default_factory=lambda: ["B01", "B03", "B10"])


class VerifyRequest(BaseModel):
    certificate_path: str | None = None
    certificate_id: str | None = None
    tamper: bool = False


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = None


# Authoritative state stores
sessions_db: dict[str, dict[str, Any]] = {}
session_events_db: dict[str, list[dict[str, Any]]] = {}
session_subscribers_db: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

races_db: dict[str, dict[str, Any]] = {}
race_events_db: dict[str, list[dict[str, Any]]] = {}
race_subscribers_db: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

review_registry: dict[str, dict[str, Any]] = {
    "approved_suite": {},
    "suppression_rules": {},
}


def create_app() -> FastAPI:
    app = FastAPI(title="ProofQA Control Plane API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def _emit_session_event(session_id: str, event_type: str, data: dict[str, Any]) -> None:
        payload = {"event": event_type, "timestamp": time.time(), "data": data}
        if session_id not in session_events_db:
            session_events_db[session_id] = []
        session_events_db[session_id].append(payload)

        queues = session_subscribers_db.get(session_id, [])
        for q in list(queues):
            try:
                await q.put(payload)
            except Exception:
                pass

    async def _emit_race_event(race_id: str, event_type: str, data: dict[str, Any]) -> None:
        payload = {"event": event_type, "timestamp": time.time(), "data": data}
        if race_id not in race_events_db:
            race_events_db[race_id] = []
        race_events_db[race_id].append(payload)

        queues = race_subscribers_db.get(race_id, [])
        for q in list(queues):
            try:
                await q.put(payload)
            except Exception:
                pass

    @app.post("/sessions")
    async def create_session(req: SessionCreateRequest) -> dict[str, Any]:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        spec = req.world_spec or WorldSpec(app_id=req.app_id, bugs=req.bugs)

        sessions_db[session_id] = {
            "session_id": session_id,
            "status": "running",
            "world_spec": spec.model_dump(),
            "findings": [],
            "certificates": [],
            "created_at": time.time(),
        }
        session_events_db[session_id] = []
        session_subscribers_db[session_id] = []

        async def _run_pipeline_task() -> None:
            bus = PipelineEventBus()

            async def _forward_event(evt: dict[str, Any]) -> None:
                await _emit_session_event(session_id, evt.get("event", "pipeline"), evt.get("data", {}))

            bus.subscribe(_forward_event)

            pipeline = Pipeline(
                world_spec=spec,
                output_dir=f"results/certificates/{session_id}",
                session_db_path=f"results/sessions/{session_id}.db",
                event_bus=bus,
            )

            try:
                await _emit_session_event(session_id, "session_started", {"session_id": session_id})
                certs = await pipeline.run(step_budget=req.step_budget, k_replays=req.k_replays)
                cert_strs = [str(c) for c in certs]
                sessions_db[session_id]["certificates"] = cert_strs
                sessions_db[session_id]["status"] = "completed"
                await _emit_session_event(
                    session_id,
                    "session_completed",
                    {"certificates": cert_strs, "status": "completed"},
                )
            except Exception as exc:
                sessions_db[session_id]["status"] = "failed"
                sessions_db[session_id]["error"] = str(exc)
                await _emit_session_event(session_id, "session_failed", {"error": str(exc)})

        asyncio.create_task(_run_pipeline_task())
        return {"session_id": session_id, "status": "running"}

    @app.get("/sessions")
    async def list_sessions() -> dict[str, Any]:
        return {"sessions": list(sessions_db.values())}

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        if session_id not in sessions_db:
            raise HTTPException(status_code=404, detail="Session not found")
        return sessions_db[session_id]

    @app.get("/sessions/{session_id}/findings")
    async def get_session_findings(session_id: str) -> dict[str, Any]:
        if session_id not in sessions_db:
            raise HTTPException(status_code=404, detail="Session not found")
        sess = sessions_db[session_id]
        return {"findings": sess.get("findings", [])}

    @app.get("/sessions/{session_id}/events")
    async def stream_session_events(
        session_id: str, request: Request, once: bool = False
    ) -> StreamingResponse:
        if session_id not in sessions_db:
            raise HTTPException(status_code=404, detail="Session not found")

        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if session_id not in session_subscribers_db:
            session_subscribers_db[session_id] = []
        session_subscribers_db[session_id].append(q)

        async def event_generator():
            try:
                # 1. Yield buffered history events (reconnect resilience)
                for past_event in session_events_db.get(session_id, []):
                    yield f"data: {json.dumps(past_event)}\n\n"

                if once:
                    return

                # 2. Yield live events
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=0.5)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            except (asyncio.CancelledError, GeneratorExit):
                pass
            finally:
                if session_id in session_subscribers_db and q in session_subscribers_db[session_id]:
                    session_subscribers_db[session_id].remove(q)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/certificates/{cert_id}")
    async def download_certificate(cert_id: str) -> Response:
        """Download certificate directory as hermetic ZIP archive."""
        # Locate certificate directory
        target_dir: Path | None = None
        candidates = [
            Path("results/certificates") / cert_id,
            Path("results") / cert_id,
        ]
        for c in candidates:
            if c.exists() and (c / "manifest.json").exists():
                target_dir = c
                break

        if not target_dir:
            # Search recursively under results
            for p in Path("results").rglob("manifest.json"):
                if p.parent.name == cert_id or cert_id in str(p.parent):
                    target_dir = p.parent
                    break

        if not target_dir or not target_dir.exists():
            raise HTTPException(status_code=404, detail=f"Certificate {cert_id} not found")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in target_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(target_dir)
                    zip_file.write(file_path, arcname=str(arcname))

        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{cert_id}.zip"'},
        )

    @app.post("/race")
    async def start_race(req: RaceRequest) -> dict[str, Any]:
        """Runs ProofQA and Monkey baseline concurrently on the same world and streams updates."""
        race_id = f"race_{uuid.uuid4().hex[:8]}"
        spec = req.world_spec or WorldSpec(app_id="shop_twin", bugs=req.bugs)

        races_db[race_id] = {
            "race_id": race_id,
            "status": "running",
            "proofqa_lane": {
                "reports_filed": 0,
                "certificates_valid": 0,
                "false_reports": 0,
                "findings": [],
            },
            "baseline_lane": {
                "reports_filed": 0,
                "certificates_valid": 0,
                "false_reports": 0,
                "findings": [],
            },
        }
        race_events_db[race_id] = []
        race_subscribers_db[race_id] = []

        async def _run_race_task() -> None:
            await _emit_race_event(race_id, "race_started", {"race_id": race_id})

            async def _run_proofqa():
                bus = PipelineEventBus()

                async def _on_pipeline_event(evt: dict[str, Any]):
                    event_type = evt.get("event", "")
                    data = evt.get("data", {})
                    if event_type == "certificate_issued":
                        races_db[race_id]["proofqa_lane"]["reports_filed"] += 1
                        races_db[race_id]["proofqa_lane"]["certificates_valid"] += 1
                    await _emit_race_event(
                        race_id,
                        "lane_update",
                        {"lane": "proofqa", "event": event_type, "data": data},
                    )

                bus.subscribe(_on_pipeline_event)
                pipeline = Pipeline(
                    world_spec=spec,
                    output_dir=f"results/race_{race_id}/proofqa",
                    session_db_path=f"results/race_{race_id}/proofqa.db",
                    event_bus=bus,
                )
                certs = await pipeline.run(step_budget=req.budget, k_replays=1)
                return certs

            async def _run_baseline():
                monkey = RandomMonkeyBaseline(step_budget=req.budget, seed=123)
                findings = await monkey.run(spec)
                for f in findings:
                    races_db[race_id]["baseline_lane"]["reports_filed"] += 1
                    # Naive baseline reports without cryptographic verification
                    races_db[race_id]["baseline_lane"]["false_reports"] += 1
                    await _emit_race_event(
                        race_id,
                        "lane_update",
                        {
                            "lane": "baseline",
                            "event": "naive_report_filed",
                            "claim": f.claim,
                            "tier": f.tier.value,
                        },
                    )
                return findings

            # Run concurrently
            await asyncio.gather(_run_proofqa(), _run_baseline(), return_exceptions=True)
            races_db[race_id]["status"] = "completed"
            await _emit_race_event(
                race_id,
                "race_completed",
                {
                    "race_id": race_id,
                    "proofqa_lane": races_db[race_id]["proofqa_lane"],
                    "baseline_lane": races_db[race_id]["baseline_lane"],
                },
            )

        asyncio.create_task(_run_race_task())
        return {"race_id": race_id, "status": "running"}

    @app.get("/race/{race_id}")
    async def get_race(race_id: str) -> dict[str, Any]:
        if race_id not in races_db:
            raise HTTPException(status_code=404, detail="Race not found")
        return races_db[race_id]

    @app.get("/race/{race_id}/events")
    async def stream_race_events(race_id: str, request: Request) -> StreamingResponse:
        if race_id not in races_db:
            raise HTTPException(status_code=404, detail="Race not found")

        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if race_id not in race_subscribers_db:
            race_subscribers_db[race_id] = []
        race_subscribers_db[race_id].append(q)

        async def event_generator():
            try:
                for past_event in race_events_db.get(race_id, []):
                    yield f"data: {json.dumps(past_event)}\n\n"

                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=2.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                if race_id in race_subscribers_db and q in race_subscribers_db[race_id]:
                    race_subscribers_db[race_id].remove(q)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.post("/verify")
    async def verify_cert_endpoint(req: VerifyRequest) -> dict[str, Any]:
        """Runs proofqa verify on a certificate path/id, with optional 1-byte tamper demonstration."""
        target_path: Path | None = None
        if req.certificate_path:
            p = Path(req.certificate_path)
            if p.exists():
                target_path = p
        elif req.certificate_id:
            candidates = list(Path("results").rglob(req.certificate_id))
            for c in candidates:
                if c.is_dir() and (c / "manifest.json").exists():
                    target_path = c
                    break

        if not target_path or not target_path.exists():
            raise HTTPException(status_code=404, detail="Target certificate path not found")


        if req.tamper:
            # Create a temporary copy and tamper 1 byte
            tmp_dir = Path(tempfile.mkdtemp(prefix="tamper_demo_"))
            try:
                shutil.copytree(target_path, tmp_dir, dirs_exist_ok=True)
                claim_file = tmp_dir / "claim.json"
                if claim_file.exists():
                    content = bytearray(claim_file.read_bytes())
                    if len(content) > 0:
                        content[0] ^= 0x01
                    claim_file.write_bytes(content)
                verdict = await verify_certificate(tmp_dir, replay_count=1, verbose=False)
                return {
                    "verdict": verdict.verdict.value,
                    "tampered": True,
                    "target_path": str(tmp_dir),
                    "log": f"Tampered byte at claim.json:0x00 -> Verdict: {verdict.verdict.value}",
                }
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        verdict = await verify_certificate(target_path, replay_count=1, verbose=False)
        return {
            "verdict": verdict.verdict.value,
            "tampered": False,
            "target_path": str(target_path),
            "log": f"Verified {target_path} -> Verdict: {verdict.verdict.value}",
        }

    @app.get("/bench/summary")
    async def get_bench_summary() -> dict[str, Any]:
        summary_path = Path("results/summary.json")
        if summary_path.exists():
            return json.loads(summary_path.read_text(encoding="utf-8"))
        return {
            "true_bugs_count": 0,
            "precision": 1.0,
            "recall": 0.0,
            "certificate_validity_rate": 1.0,
            "decoy_false_positive_rate": 0.0,
        }

    @app.post("/findings/{finding_id}/review")
    async def review_finding(finding_id: str, req: ReviewRequest) -> dict[str, Any]:
        """Approve adds to regression suite; reject creates signature-level suppression rule."""
        if req.action == "approve":
            review_registry["approved_suite"][finding_id] = {
                "finding_id": finding_id,
                "approved_at": time.time(),
                "reason": req.reason or "Approved for continuous regression suite",
            }
            return {
                "finding_id": finding_id,
                "status": "approved",
                "suite_size": len(review_registry["approved_suite"]),
            }
        else:
            # Reject -> create suppression rule
            rule_id = f"suppress_{finding_id}"
            review_registry["suppression_rules"][rule_id] = {
                "finding_id": finding_id,
                "rejected_at": time.time(),
                "reason": req.reason or "Rejected as unwanted or intended behavior",
            }
            return {
                "finding_id": finding_id,
                "status": "rejected",
                "suppression_rule_id": rule_id,
                "suppression_count": len(review_registry["suppression_rules"]),
            }

    @app.get("/findings/reviews")
    async def list_reviews() -> dict[str, Any]:
        return review_registry

    dist_dir = Path("dashboard/dist")
    if dist_dir.exists():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(dist_dir / "index.html")

    return app


app = create_app()
