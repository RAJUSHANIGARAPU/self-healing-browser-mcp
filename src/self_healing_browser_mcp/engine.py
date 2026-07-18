"""
self_healing_browser_mcp.engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The browser-control core: a persistent Playwright session plus a self-healing
locator resolver.

The resolver is the point of the project. An AI agent describes an element with
whatever it knows (a test id, a role + accessible name, a label, some text, a CSS
selector). The resolver tries those strategies in priority order and uses the
first that matches exactly one visible element. If the agent's *preferred*
strategy has broken — the test id was renamed, the DOM was restructured — a later
strategy recovers the element and the result is flagged as ``healed``, so the
caller learns the locator drifted instead of just failing.

This module has no MCP dependency, so it can be unit-tested directly against
in-memory HTML with Playwright.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from playwright.async_api import Browser, Locator, Page, async_playwright

# Priority order of the explicit strategies. Test ids first (most stable when
# present), CSS last (most brittle). Fuzzy matching is a final fallback.
STRATEGY_ORDER = ("testid", "role", "label", "placeholder", "text", "css")

# Roles worth scanning during a fuzzy (accessible-name) recovery.
_FUZZY_ROLES = ("button", "link", "textbox", "checkbox", "menuitem", "tab", "option")


class ElementNotFound(RuntimeError):
    """Raised when no strategy — explicit or fuzzy — resolves the target."""


@dataclass(frozen=True)
class Hint:
    """A resilient, multi-strategy description of a target element.

    Provide as many strategies as you know; the resolver picks the best that
    still works. Order of preference matches ``STRATEGY_ORDER``.
    """

    testid: str | None = None
    role: str | None = None
    name: str | None = None  # accessible name, paired with ``role`` (or used for fuzzy)
    label: str | None = None
    placeholder: str | None = None
    text: str | None = None
    css: str | None = None

    def describe(self) -> str:
        parts = [f"{k}={v!r}" for k, v in self.__dict__.items() if v is not None]
        return "Hint(" + ", ".join(parts) + ")"


@dataclass
class Resolution:
    """The outcome of resolving a :class:`Hint`."""

    locator: Locator
    strategy: str
    healed: bool  # True when the preferred strategy failed and a fallback matched


def _candidates(page: Page, hint: Hint) -> list[tuple[str, Locator]]:
    """Build the ordered (strategy, locator) list from the hint's fields."""
    out: list[tuple[str, Locator]] = []
    if hint.testid is not None:
        out.append(("testid", page.get_by_test_id(hint.testid)))
    if hint.role is not None:
        loc = page.get_by_role(hint.role, name=hint.name) if hint.name else page.get_by_role(hint.role)
        out.append(("role", loc))
    if hint.label is not None:
        out.append(("label", page.get_by_label(hint.label)))
    if hint.placeholder is not None:
        out.append(("placeholder", page.get_by_placeholder(hint.placeholder)))
    if hint.text is not None:
        out.append(("text", page.get_by_text(hint.text)))
    if hint.css is not None:
        out.append(("css", page.locator(hint.css)))
    return out


async def _unique_visible(locator: Locator) -> Locator | None:
    """Return the locator if it resolves to exactly one visible element, else None."""
    try:
        if await locator.count() != 1:
            return None
        if await locator.first.is_visible():
            return locator.first
    except Exception:
        return None
    return None


async def _fuzzy(page: Page, needle: str) -> Locator | None:
    """Last-resort recovery: find an interactive element whose accessible name
    contains ``needle`` (case-insensitive), across common roles."""
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    for role in _FUZZY_ROLES:
        loc = page.get_by_role(role, name=pattern)
        hit = await _unique_visible(loc)
        if hit is not None:
            return hit
    return None


async def resolve(page: Page, hint: Hint) -> Resolution:
    """Resolve ``hint`` to a single element, healing to a fallback if needed.

    Raises :class:`ElementNotFound` if nothing matches.
    """
    candidates = _candidates(page, hint)
    for index, (strategy, locator) in enumerate(candidates):
        hit = await _unique_visible(locator)
        if hit is not None:
            return Resolution(locator=hit, strategy=strategy, healed=index > 0)

    needle = hint.name or hint.text
    if needle:
        hit = await _fuzzy(page, needle)
        if hit is not None:
            return Resolution(locator=hit, strategy="fuzzy", healed=True)

    raise ElementNotFound(f"no strategy resolved {hint.describe()}")


# A line in Playwright's ARIA snapshot, e.g.  `- button "Save"`  or  `- textbox "Search"`.
_ARIA_LINE = re.compile(r'^\s*-\s+(?P<role>[a-z]+)(?:\s+"(?P<name>[^"]*)")?', re.MULTILINE)


async def snapshot_interactive(page: Page) -> list[dict[str, str]]:
    """A compact, semantic view of the interactive elements on the page.

    Agents use this to 'see' the page as roles + names instead of raw HTML or a
    screenshot, then target elements through :func:`resolve`. Built from
    Playwright's ARIA snapshot (the accessibility tree).
    """
    tree = await page.locator("body").aria_snapshot()
    out: list[dict[str, str]] = []
    for match in _ARIA_LINE.finditer(tree):
        role = match.group("role")
        name = match.group("name")
        if role in _FUZZY_ROLES and name:
            out.append({"role": role, "name": name})
    return out


class BrowserSession:
    """A lazily-started, persistent Chromium page shared across MCP tool calls.

    Headless by default; set ``SHBM_HEADED=1`` to watch it. The test-id attribute
    defaults to Playwright's ``data-testid`` and can be overridden with
    ``SHBM_TESTID_ATTR`` (e.g. ``data-test`` for Sauce Labs-style apps).
    """

    def __init__(self) -> None:
        self._pw = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def page(self) -> Page:
        if self._page is None:
            self._pw = await async_playwright().start()
            testid_attr = os.environ.get("SHBM_TESTID_ATTR", "data-testid")
            self._pw.selectors.set_test_id_attribute(testid_attr)
            headed = os.environ.get("SHBM_HEADED", "") == "1"
            self._browser = await self._pw.chromium.launch(headless=not headed)
            self._page = await self._browser.new_page()
        return self._page

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None
        self._page = None
