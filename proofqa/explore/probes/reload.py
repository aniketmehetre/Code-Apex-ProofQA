"""ReloadProbe: Metamorphic persistence verification after stateful mutations (Prompt 5).

Issues a reload / navigation back to the current URL to verify that server-side
state and user settings persist accurately across page reloads.
"""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind
from proofqa.explore.probes.base import Probe, ProbeContext


class ReloadProbe(Probe):
    """Reloads the current page to check for client-side state loss or persistence defects."""

    @property
    def name(self) -> str:
        return "reload"

    def applies(self, ctx: ProbeContext) -> bool:
        """Applies on stateful pages (account, profile, cart, settings)."""
        url_path = ctx.semantic_state_key.split(":")[0] if ctx.semantic_state_key else "/"
        return any(segment in url_path for segment in ["account", "profile", "cart", "settings", "orders"])

    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans a reload action to the current page path."""
        url_path = ctx.semantic_state_key.split(":")[0] if ctx.semantic_state_key else "/"
        return [
            Action(
                id="reload_current_page",
                kind=ActionKind.GOTO,
                value=url_path,
                params={"reload": True},
            )
        ]
