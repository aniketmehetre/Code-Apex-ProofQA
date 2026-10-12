"""Acceptance tests for Phase 6: Certificate builder, independent verifier, and fix-flip validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofqa.cert import (
    build_certificate,
    generate_pytest_test,
    verify_certificate,
)
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    VerifyVerdictKind,
    WorldSpec,
)


@pytest.fixture
def b01_fixture() -> tuple[Finding, list[Action], WorldSpec]:
    sig = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="HTTP <NUM> on /api/cart",
    )
    spec = WorldSpec(app_id="shop_twin", bugs=["B01"])
    actions = [
        Action(id="s0_home", kind=ActionKind.GOTO, value="/"),
        Action(
            id="s1_open_modal",
            kind=ActionKind.CLICK,
            locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones"),
        ),
        Action(
            id="s2_set_zero_qty",
            kind=ActionKind.FILL,
            locator=Locator(role="spinbutton", name="Quantity", label="Quantity"),
            value="0",
        ),
        Action(
            id="s3_submit_cart",
            kind=ActionKind.CLICK,
            locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart"),
        ),
    ]
    finding = Finding(
        id="cert_b01_test",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig,
        claim="Zero quantity cart addition produces HTTP 500 (B01)",
        steps=actions,
        confidence=1.0,
    )
    return finding, actions, spec


@pytest.mark.asyncio
async def test_certificate_build_and_verify_valid(
    tmp_path: Path, b01_fixture: tuple[Finding, list[Action], WorldSpec]
) -> None:
    finding, actions, spec = b01_fixture

    # 1. Build certificate
    cert_dir = build_certificate(
        finding=finding,
        world_spec=spec,
        output_dir=tmp_path,
    )

    assert cert_dir.exists()
    assert (cert_dir / "manifest.json").exists()
    assert (cert_dir / "claim.json").exists()
    assert (cert_dir / "repro.json").exists()
    assert (cert_dir / "signature.json").exists()
    assert (cert_dir / "world.json").exists()

    # 2. Verify certificate -> VALID
    verdict = await verify_certificate(cert_dir, replay_count=1, verbose=False)
    assert verdict.verdict == VerifyVerdictKind.VALID


@pytest.mark.asyncio
async def test_certificate_tamper_detection(
    tmp_path: Path, b01_fixture: tuple[Finding, list[Action], WorldSpec]
) -> None:
    finding, actions, spec = b01_fixture

    cert_dir = build_certificate(
        finding=finding,
        world_spec=spec,
        output_dir=tmp_path,
    )

    # Tamper with repro.json (flip one character)
    repro_path = cert_dir / "repro.json"
    content = repro_path.read_text(encoding="utf-8")
    repro_path.write_text(content + " ", encoding="utf-8")

    # Verifier must immediately detect tampering
    verdict = await verify_certificate(cert_dir, replay_count=1, verbose=False)
    assert verdict.verdict == VerifyVerdictKind.TAMPERED


@pytest.mark.asyncio
async def test_certificate_invalid_on_fixed_world(
    tmp_path: Path, b01_fixture: tuple[Finding, list[Action], WorldSpec]
) -> None:
    finding, actions, spec = b01_fixture

    cert_dir = build_certificate(
        finding=finding,
        world_spec=spec,
        output_dir=tmp_path,
    )

    # Point world.json to fixed world (no bugs) and re-sign manifest to avoid TAMPERED
    world_path = cert_dir / "world.json"
    fixed_spec = WorldSpec(app_id="shop_twin", bugs=[])
    world_path.write_text(json.dumps(fixed_spec.model_dump(), indent=2), encoding="utf-8")

    # Recompute manifest so hashes match but world is fixed
    manifest_path = cert_dir / "manifest.json"
    from proofqa.cert.build import compute_sha256
    file_hashes = {}
    for p in sorted(cert_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            file_hashes[p.relative_to(cert_dir).as_posix()] = compute_sha256(p)
    import hashlib
    hasher = hashlib.sha256()
    for rel_p in sorted(file_hashes.keys()):
        hasher.update(f"{rel_p}:{file_hashes[rel_p]}".encode())
    from proofqa.contracts import CertificateManifest
    m = CertificateManifest(
        certificate_id=finding.id,
        finding_id=finding.id,
        created_at="2026-10-24T09:00:00Z",
        files=file_hashes,
        manifest_hash=hasher.hexdigest(),
    )
    manifest_path.write_text(json.dumps(m.model_dump(), indent=2), encoding="utf-8")

    # Replay on fixed world will not reproduce bug -> INVALID
    verdict = await verify_certificate(cert_dir, replay_count=1, verbose=False)
    assert verdict.verdict == VerifyVerdictKind.INVALID


def test_exported_pytest_test_generation(
    b01_fixture: tuple[Finding, list[Action], WorldSpec]
) -> None:
    finding, actions, _ = b01_fixture
    code = generate_pytest_test(finding, actions, test_name="test_b01_zero_qty")

    assert "async def test_b01_zero_qty" in code
    assert "page.goto" in code
    assert "Noise-Canceling Wireless Headphones" in code
    assert "assert len(observed_5xx) == 0" in code
