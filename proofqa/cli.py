"""ProofQA 2.0 CLI."""

import typer

app = typer.Typer(help="ProofQA 2.0: The Verification-Native Autonomous QA Engineer")


@app.command()
def version():
    """Show version."""
    typer.echo("ProofQA 2.0.0-dev")


if __name__ == "__main__":
    app()
