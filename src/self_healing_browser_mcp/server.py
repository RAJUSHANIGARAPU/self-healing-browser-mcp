"""
self_healing_browser_mcp.server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
An MCP server that hands an AI agent (Claude Desktop, Cursor, Claude Code, …) a
real browser to drive, with self-healing locators.

Every element-targeting tool takes the same set of optional locator strategies
(``testid``, ``role`` + ``name``, ``label``, ``placeholder``, ``text``, ``css``).
Provide whatever you know; the server resolves the element and, when your
preferred strategy has broken, transparently heals to a working one and tells
you so in the result.

Run it: ``self-healing-browser-mcp`` (stdio transport).
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from .engine import BrowserSession, ElementNotFound, Hint, resolve, snapshot_interactive

mcp = FastMCP("self-healing-browser")
_session = BrowserSession()


def _hint(testid, role, name, label, placeholder, text, css) -> Hint:
    return Hint(
        testid=testid, role=role, name=name, label=label,
        placeholder=placeholder, text=text, css=css,
    )


def _resolved_note(strategy: str, healed: bool) -> str:
    return f"via {strategy}" + (" (healed — your preferred locator had drifted)" if healed else "")


@mcp.tool()
async def browser_navigate(url: str) -> str:
    """Open a URL in the shared browser page and return the final URL."""
    page = await _session.page()
    await page.goto(url)
    return f"Navigated to {page.url}"


@mcp.tool()
async def browser_snapshot() -> str:
    """Return the page's interactive elements as roles + accessible names.

    Use this to 'see' the page semantically before deciding what to click or type.
    """
    page = await _session.page()
    elements = await snapshot_interactive(page)
    return json.dumps({"url": page.url, "elements": elements}, indent=2)


@mcp.tool()
async def browser_click(
    testid: str | None = None,
    role: str | None = None,
    name: str | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    text: str | None = None,
    css: str | None = None,
) -> str:
    """Click an element described by any combination of locator strategies.

    Provide as many as you know (e.g. ``role='button'`` + ``name='Log in'``, and a
    ``testid`` if you have one). The most stable available strategy wins; if it
    healed to a fallback, the result says so.
    """
    page = await _session.page()
    try:
        res = await resolve(page, _hint(testid, role, name, label, placeholder, text, css))
    except ElementNotFound as exc:
        return f"Could not find the element: {exc}"
    await res.locator.click()
    return f"Clicked {_resolved_note(res.strategy, res.healed)}"


@mcp.tool()
async def browser_fill(
    value: str,
    testid: str | None = None,
    role: str | None = None,
    name: str | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    text: str | None = None,
    css: str | None = None,
) -> str:
    """Type ``value`` into an input described by the locator strategies."""
    page = await _session.page()
    try:
        res = await resolve(page, _hint(testid, role, name, label, placeholder, text, css))
    except ElementNotFound as exc:
        return f"Could not find the field: {exc}"
    await res.locator.fill(value)
    return f"Filled {_resolved_note(res.strategy, res.healed)}"


@mcp.tool()
async def browser_get_text(
    testid: str | None = None,
    role: str | None = None,
    name: str | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    text: str | None = None,
    css: str | None = None,
) -> str:
    """Return the visible text of the described element."""
    page = await _session.page()
    try:
        res = await resolve(page, _hint(testid, role, name, label, placeholder, text, css))
    except ElementNotFound as exc:
        return f"Could not find the element: {exc}"
    return await res.locator.inner_text()


@mcp.tool()
async def browser_assert_visible(
    testid: str | None = None,
    role: str | None = None,
    name: str | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    text: str | None = None,
    css: str | None = None,
) -> str:
    """Assert the described element is present and visible. Returns PASS or FAIL."""
    page = await _session.page()
    try:
        res = await resolve(page, _hint(testid, role, name, label, placeholder, text, css))
    except ElementNotFound as exc:
        return f"FAIL — element not visible: {exc}"
    return f"PASS — element is visible {_resolved_note(res.strategy, res.healed)}"


@mcp.tool()
async def browser_close() -> str:
    """Close the browser and release its resources."""
    await _session.close()
    return "Browser closed"


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
