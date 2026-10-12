"""ProofQA 2.0 CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from proofqa.cert.verify import verify_certificate
from proofqa.contracts import VerifyVerdictKind, WorldSpec
from proofqa.pipeline import Pipeline

app = typer.Typer(help="ProofQA 2.0: The Verification-Native Autonomous QA Engineer")


@app.command()
def version() -> None:
    """Show ProofQA version."""
    typer.echo("ProofQA 2.0.0-dev (Contracts v1)")


@app.command()
def run(
    world: str = typer.Option("shop_twin", "--world", help="Target app name or comma-separated bugs (e.g. B01,B03)"),
    bugs: Optional[str] = typer.Option(None, "--bugs", help="Comma-separated bug IDs (e.g. B01,B03,B10)"),
    budget: int = typer.Option(20, "--budget", help="Exploration step budget"),
    replays: int = typer.Option(2, "--replays", help="Number of confirmation replays required (k of k)"),
    out: str = typer.Option("results/certificates", "--out", help="Certificate output directory"),
) -> None:
    """Run full ProofQA pipeline: explore, detect, prove, shrink, and certify."""
    bug_list: list[str] = []
    if bugs:
        bug_list = [b.strip() for b in bugs.split(",") if b.strip()]
    elif "," in world:
        bug_list = [b.strip() for b in world.split(",") if b.strip()]

    spec = WorldSpec(app_id="shop_twin", bugs=bug_list)
    typer.echo(f"[*] Starting ProofQA Pipeline on app={spec.app} with bugs={spec.bugs}")

    pipeline = Pipeline(world_spec=spec, output_dir=out)

    def on_event(ev: dict) -> None:
        event_name = ev.get("event")
        data = ev.get("data", {})
        if event_name == "certificate_issued":
            typer.secho(f"  [+] Certificate issued: {data.get('certificate_path')}", fg=typer.colors.GREEN, bold=True)
        elif event_name == "candidate_found":
            typer.echo(f"  [?] Discovered candidate: {data.get('signature', {}).get('message_norm', '')}")

    pipeline.event_bus.subscribe(on_event)

    certs = asyncio.run(pipeline.run(step_budget=budget, k_replays=replays))
    typer.echo(f"[*] Pipeline complete. Total certificates issued: {len(certs)}")


@app.command()
def verify(
    path: str = typer.Argument(..., help="Path to certificate directory"),
    docker: bool = typer.Option(False, "--docker", help="Run world inside hermetic Docker container"),
    replays: int = typer.Option(3, "--replays", help="Replay evaluation count"),
) -> None:
    """Independently verify a certificate directory (Rule 3 compliant)."""
    typer.echo(f"[*] Verifying certificate at {path} (docker={docker}, replays={replays})...")
    verdict = asyncio.run(verify_certificate(cert_path=Path(path), use_docker=docker, replay_count=replays, verbose=True))

    if verdict.verdict == VerifyVerdictKind.VALID:
        typer.secho(f"FINAL VERDICT: {verdict.verdict.value}", fg=typer.colors.GREEN, bold=True)
    elif verdict.verdict == VerifyVerdictKind.TAMPERED:
        typer.secho(f"FINAL VERDICT: {verdict.verdict.value} ({verdict.reason})", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=2)
    elif verdict.verdict == VerifyVerdictKind.INVALID:
        typer.secho(f"FINAL VERDICT: {verdict.verdict.value} ({verdict.reason})", fg=typer.colors.YELLOW, bold=True)
        raise typer.Exit(code=1)
    else:
        typer.secho(f"FINAL VERDICT: {verdict.verdict.value} ({verdict.reason})", fg=typer.colors.MAGENTA, bold=True)
        raise typer.Exit(code=3)


@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", help="Port to serve the control plane and dashboard"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface"),
) -> None:
    """Launch the ProofQA Control Plane and Web Dashboard."""
    import uvicorn

    from proofqa.api.server import app as fastapi_app
    typer.echo(f"[*] Starting ProofQA Dashboard at http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()

