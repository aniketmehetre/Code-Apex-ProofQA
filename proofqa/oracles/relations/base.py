"""Plugin interface for Class B Metamorphic Relations and widget classification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from playwright.async_api import Page

from proofqa.contracts import Finding, WorldSpec


class Relation(ABC):
    """Metamorphic relation testing behavioral invariants without known output oracles."""

    name: str

    @abstractmethod
    def applies(self, widgets: dict[str, Any]) -> bool:
        """Determines if the current page contains the widgets necessary for this relation."""
        ...

    @abstractmethod
    async def run(self, page: Page, world_url: str) -> Finding | None:
        """Executes the relation sequence on the page, returning a Finding if invariant is violated."""
        ...

    @abstractmethod
    async def validate(self, world_spec: WorldSpec) -> bool:
        """Validates that this relation holds consistently on a clean reference world.

        A relation MUST pass validation before it is permitted to raise findings.
        """
        ...


class WidgetClassifier:
    """Classifies page semantic components (sort controls, filters, pagination, forms)."""

    @staticmethod
    async def classify(page: Page) -> dict[str, bool]:
        """Inspects page elements and returns a dictionary of detected widget types."""
        widgets: dict[str, bool] = {
            "sort_control": False,
            "category_filter": False,
            "paginator": False,
            "search_box": False,
            "cart": False,
            "address_form": False,
        }

        try:
            # Sort control
            sort_select = page.locator('select[aria-label="Sort products"]')
            if await sort_select.count() > 0:
                widgets["sort_control"] = True

            # Category filter
            cat_select = page.locator('select[aria-label="Filter by Category"]')
            if await cat_select.count() > 0:
                widgets["category_filter"] = True

            # Paginator
            pagination = page.locator('[aria-label="Pagination"]')
            if await pagination.count() > 0:
                widgets["paginator"] = True

            # Search box
            search = page.locator('input[aria-label="Search products"]')
            if await search.count() > 0:
                widgets["search_box"] = True

            # Cart badge
            cart = page.locator('[data-testid="cart-badge"]')
            if await cart.count() > 0:
                widgets["cart"] = True

            # Address form
            address = page.locator('input[aria-label="Shipping Address"]')
            if await address.count() > 0:
                widgets["address_form"] = True
        except Exception:
            pass

        return widgets
