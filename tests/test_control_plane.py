"""Acceptance tests for Phase 11 Control Plane API (Milestone M3, Prompt 11.1)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from proofqa.api.server import app, review_registry, session_events_db
from proofqa.cert.build import build_certificate
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    WorldSpec,
)


@pytest.fixture
def test_certificate(tmp_path: Path) -> Path:
    """Fixture providing a valid dummy certificate directory."""
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="ZeroQuantityException",
    )
    finding = Finding(
        id="f_api_test",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart addition returns 500",
        steps=[Action(id="a0", kind=ActionKind.GOTO, value="/")],
    )
    cert_dir = build_certificate(
        finding=finding,
        world_spec=spec,
        output_dir=tmp_path / "cert_api_test",
    )
    return cert_dir


@pytest.mark.asyncio
async def test_control_plane_endpoints_and_sse(tmp_path: Path, test_certificate: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_run(self, *args, **kwargs):
        return []
    monkeypatch.setattr("proofqa.pipeline.Pipeline.run", mock_run)

    async def mock_verify(path, replay_count=1, verbose=False):
        from proofqa.cert.verify import compute_sha256
        from proofqa.contracts import VerifyVerdict, VerifyVerdictKind
        manifest = json.loads((Path(path) / "manifest.json").read_text())
        claim_hash = compute_sha256(Path(path) / "claim.json")
        if claim_hash != manifest["files"]["claim.json"]:
            return VerifyVerdict(verdict=VerifyVerdictKind.TAMPERED)
        return VerifyVerdict(verdict=VerifyVerdictKind.VALID)
    monkeypatch.setattr("proofqa.api.server.verify_certificate", mock_verify)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /bench/summary
        resp = await client.get("/bench/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert "precision" in summary

        # 2. POST /sessions
        resp = await client.post(
            "/sessions",
            json={"app_id": "shop_twin", "bugs": ["B01"], "step_budget": 2, "k_replays": 1},
        )
        assert resp.status_code == 200
        sess_data = resp.json()
        session_id = sess_data["session_id"]
        assert sess_data["status"] == "running"

        # 3. GET /sessions
        resp = await client.get("/sessions")
        assert resp.status_code == 200
        all_sessions = resp.json()["sessions"]
        assert any(s["session_id"] == session_id for s in all_sessions)

        # 4. GET /sessions/{id}
        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

        # 5. GET /sessions/{id}/findings
        resp = await client.get(f"/sessions/{session_id}/findings")
        assert resp.status_code == 200
        assert "findings" in resp.json()

        # 6. Test SSE stream with pre-buffered events (reconnect resilience)
        session_events_db[session_id].append({"event": "mock_reconnect_evt", "timestamp": 123.0, "data": {"val": 42}})
        async with client.stream("GET", f"/sessions/{session_id}/events?once=true") as stream:
            assert stream.status_code == 200
            assert "text/event-stream" in stream.headers.get("content-type", "")
            lines = []
            async for line in stream.aiter_lines():
                if line.startswith("data:"):
                    lines.append(line)
                    break
            assert len(lines) > 0
            payload = json.loads(lines[0].replace("data:", "").strip())
            assert "event" in payload

        # 7. POST /findings/{id}/review (approve)
        resp = await client.post("/findings/f_test_1/review", json={"action": "approve", "reason": "Confirmed true bug"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert "f_test_1" in review_registry["approved_suite"]

        # 8. POST /findings/{id}/review (reject -> suppression rule)
        resp = await client.post("/findings/f_test_2/review", json={"action": "reject", "reason": "Expected 404 behavior"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
        assert "suppress_f_test_2" in review_registry["suppression_rules"]

        # 9. GET /findings/reviews
        resp = await client.get("/findings/reviews")
        assert resp.status_code == 200
        reviews = resp.json()
        assert "f_test_1" in reviews["approved_suite"]
        assert "suppress_f_test_2" in reviews["suppression_rules"]

        # 10. POST /verify with tamper demo
        resp = await client.post(
            "/verify",
            json={"certificate_path": str(test_certificate), "tamper": False},
        )
        assert resp.status_code == 200
        ver_data = resp.json()
        assert ver_data["verdict"] in ["VALID", "INVALID"]
        assert ver_data["tampered"] is False

        # Tampered verification
        resp = await client.post(
            "/verify",
            json={"certificate_path": str(test_certificate), "tamper": True},
        )
        assert resp.status_code == 200
        tamper_data = resp.json()
        assert tamper_data["verdict"] == "TAMPERED"
        assert tamper_data["tampered"] is True

        # 11. GET /certificates/{id} ZIP download
        # Place test certificate under results/certificates/
        results_cert_dir = Path("results/certificates") / test_certificate.name
        try:
            import shutil
            shutil.copytree(test_certificate, results_cert_dir, dirs_exist_ok=True)

            resp = await client.get(f"/certificates/{test_certificate.name}")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/zip"
            # Validate valid zip archive
            zip_buf = io.BytesIO(resp.content)
            with zipfile.ZipFile(zip_buf, "r") as zf:
                namelist = zf.namelist()
                assert "manifest.json" in namelist
                assert "claim.json" in namelist
        finally:
            import shutil
            if results_cert_dir.exists():
                shutil.rmtree(results_cert_dir, ignore_errors=True)
