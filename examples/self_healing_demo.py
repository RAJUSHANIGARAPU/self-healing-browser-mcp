"""
Runnable demonstration of the self-healing locator engine.

    python -m playwright install chromium   # once
    python examples/self_healing_demo.py

Shows the whole point of the project: the *same* locator hint keeps working after
a refactor deletes the element's ``data-testid``. The engine falls back to the
role + accessible name, reports that it healed, and the recovered element is
genuinely usable — no test edit, no agent retry loop.
"""

import asyncio

from playwright.async_api import async_playwright

from self_healing_browser_mcp.engine import Hint, resolve

# Version 1 of the app: the "Place order" button carries the data-testid the agent
# originally learned.
APP_V1 = '<button data-testid="place-order" aria-label="Place order">Place order</button>'

# Version 2, after a refactor: the data-testid is gone and the class changed —
# the agent's preferred locator is now dead.
APP_V2 = '<button class="btn-primary" aria-label="Place order">Place order</button>'

# The agent remembers several ways to find the button, most stable first.
HINT = Hint(testid="place-order", role="button", name="Place order")


async def main() -> None:
    async with async_playwright() as playwright:
        playwright.selectors.set_test_id_attribute("data-testid")
        browser = await playwright.chromium.launch()
        page = await browser.new_page()

        print("1) Original app — the preferred data-testid resolves the button:")
        await page.set_content(APP_V1)
        first = await resolve(page, HINT)
        print(f"   -> resolved via {first.strategy!r}   healed={first.healed}\n")

        print("2) After a refactor removed the data-testid — SAME hint, no code change:")
        await page.set_content(APP_V2)
        healed = await resolve(page, HINT)
        print(f"   -> resolved via {healed.strategy!r}       healed={healed.healed}")
        await healed.locator.click()
        print("   -> clicked the recovered element successfully")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
