import pytest_asyncio
from playwright.async_api import async_playwright


@pytest_asyncio.fixture
async def page():
    """A fresh Chromium page per test, driven entirely from in-memory HTML
    (page.set_content) so the self-healing engine is tested deterministically
    with no external site."""
    async with async_playwright() as p:
        p.selectors.set_test_id_attribute("data-testid")
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        try:
            yield pg
        finally:
            await browser.close()
