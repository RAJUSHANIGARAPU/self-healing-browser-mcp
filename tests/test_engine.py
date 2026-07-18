"""Tests for the self-healing locator engine — the core of the project."""

import pytest

from self_healing_browser_mcp.engine import (
    ElementNotFound,
    Hint,
    resolve,
    snapshot_interactive,
)


async def test_resolves_by_testid(page):
    await page.set_content('<button data-testid="submit">Submit</button>')
    res = await resolve(page, Hint(testid="submit"))
    assert res.strategy == "testid"
    assert res.healed is False


async def test_resolves_by_role_and_name(page):
    await page.set_content('<button aria-label="Log in">Go</button>')
    res = await resolve(page, Hint(role="button", name="Log in"))
    assert res.strategy == "role"
    assert res.healed is False


async def test_self_heals_when_preferred_testid_is_missing(page):
    # The agent's preferred locator (data-testid) no longer exists, but it also
    # knows the role + accessible name. The resolver must recover via the
    # fallback and flag that the locator drifted.
    await page.set_content('<button aria-label="Submit order">Submit</button>')
    res = await resolve(page, Hint(testid="submit-btn", role="button", name="Submit order"))
    assert res.strategy == "role"
    assert res.healed is True
    # the healed locator is genuinely usable, not just found
    await res.locator.click()


async def test_self_heals_to_css_last(page):
    # Only a stale testid and a CSS selector are known; CSS is the last resort.
    await page.set_content('<button class="cta">Buy</button>')
    res = await resolve(page, Hint(testid="buy", css="button.cta"))
    assert res.strategy == "css"
    assert res.healed is True


async def test_fuzzy_heals_on_case_mismatch(page):
    # Only a name is known and its case has drifted; fuzzy recovery matches it
    # across interactive roles.
    await page.set_content('<button>Continue</button>')
    res = await resolve(page, Hint(name="continue"))
    assert res.strategy == "fuzzy"
    assert res.healed is True


async def test_not_found_raises(page):
    await page.set_content("<div>nothing interactive here</div>")
    with pytest.raises(ElementNotFound):
        await resolve(page, Hint(testid="ghost", role="button", name="Nope"))


async def test_fill_and_read_back(page):
    await page.set_content('<label>Email <input data-testid="email"></label>')
    res = await resolve(page, Hint(testid="email"))
    await res.locator.fill("ada@example.com")
    assert await res.locator.input_value() == "ada@example.com"


async def test_ambiguous_match_is_skipped_then_healed(page):
    # Two buttons share text, so the text strategy is ambiguous (not exactly one)
    # and must be skipped in favour of the unique testid.
    await page.set_content(
        '<button data-testid="primary">Save</button><button>Save</button>'
    )
    res = await resolve(page, Hint(text="Save", testid="primary"))
    assert res.strategy == "testid"


async def test_snapshot_lists_interactive_elements(page):
    await page.set_content(
        """
        <button>Save</button>
        <a href="#">Docs</a>
        <input aria-label="Search">
        <p>not interactive</p>
        """
    )
    elements = await snapshot_interactive(page)
    pairs = {(e["role"], e["name"]) for e in elements}
    assert ("button", "Save") in pairs
    assert ("link", "Docs") in pairs
    assert ("textbox", "Search") in pairs
    # non-interactive content is excluded
    assert all(e["role"] != "paragraph" for e in elements)
