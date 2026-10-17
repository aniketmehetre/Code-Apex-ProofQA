"""AuthBootstrap: autonomous authentication handling with hermetic tape actions (Prompt 4)."""

from __future__ import annotations

from typing import Any

from proofqa.contracts import Action, ActionKind, TapeEvent


class AuthBootstrap:
    """Detects authentication barriers and plans ordinary, replayable tape actions to resolve them."""

    @staticmethod
    def is_auth_wall(
        url_path: str,
        recent_events: list[TapeEvent],
        grounded_controls: list[Action],
    ) -> bool:
        """Determines if the explorer is blocked by an authentication wall."""
        norm_path = (url_path or "/").lower()
        if "/login" in norm_path or "/register" in norm_path:
            return True

        # Check for 401 status in recent tape events
        for ev in recent_events:
            ev_type = getattr(ev, "type", None) or getattr(ev, "kind", None)
            st = (
                getattr(ev, "status", 0)
                if hasattr(ev, "status")
                else (getattr(ev, "payload", {}) or {}).get("status", 0)
            )
            if (ev_type in ("network", "network_response")) and st == 401:
                return True

        # Check for presence of login form fields
        has_pw = any(
            c.kind == ActionKind.FILL and c.locator and "password" in (c.locator.name or c.locator.label or "").lower()
            for c in grounded_controls
        )
        has_login_btn = any(
            c.kind == ActionKind.CLICK and c.locator and "login" in (c.locator.name or "").lower()
            for c in grounded_controls
        )
        return has_pw and has_login_btn

    @staticmethod
    def plan_login_or_register(
        grounded_controls: list[Action],
        fixtures: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> list[Action]:
        """Plans sequence of Actions to authenticate, using fixtures or registration."""
        actions: list[Action] = []
        user_email = f"auth_user_{seed}@example.com"
        user_pw = "Password123!456"
        user_name = "Auth User"

        if fixtures and "accounts" in fixtures:
            test_acc = fixtures["accounts"].get("test_user", {})
            if test_acc:
                user_email = test_acc.get("email", user_email)
                user_pw = test_acc.get("password", user_pw)
                user_name = test_acc.get("name", user_name)

        # Match input controls
        for ctrl in grounded_controls:
            if ctrl.kind == ActionKind.FILL and ctrl.locator:
                lbl = (ctrl.locator.name or ctrl.locator.label or ctrl.locator.testid or "").lower()
                if "email" in lbl or "user" in lbl:
                    actions.append(
                        Action(
                            id=f"auth_fill_email_{ctrl.id}",
                            kind=ActionKind.FILL,
                            locator=ctrl.locator,
                            value=user_email,
                        )
                    )
                elif "password" in lbl:
                    actions.append(
                        Action(
                            id=f"auth_fill_pw_{ctrl.id}",
                            kind=ActionKind.FILL,
                            locator=ctrl.locator,
                            value=user_pw,
                        )
                    )
                elif "name" in lbl or "display" in lbl:
                    actions.append(
                        Action(
                            id=f"auth_fill_name_{ctrl.id}",
                            kind=ActionKind.FILL,
                            locator=ctrl.locator,
                            value=user_name,
                        )
                    )

        # Match submit or login button
        for ctrl in grounded_controls:
            if ctrl.kind == ActionKind.CLICK and ctrl.locator:
                name = (ctrl.locator.name or ctrl.locator.testid or "").lower()
                if any(w in name for w in ["login", "sign in", "register", "submit"]):
                    actions.append(
                        Action(
                            id=f"auth_click_{ctrl.id}",
                            kind=ActionKind.CLICK,
                            locator=ctrl.locator,
                        )
                    )
                    break

        return actions
