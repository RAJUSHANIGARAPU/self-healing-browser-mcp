"""Tests for the MCP protocol layer — the tools are registered with the
expected names and each element tool exposes the locator strategies."""

from self_healing_browser_mcp.server import mcp

EXPECTED_TOOLS = {
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_fill",
    "browser_get_text",
    "browser_assert_visible",
    "browser_close",
}


async def test_all_tools_are_registered():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names


async def test_element_tools_expose_locator_strategies():
    by_name = {t.name: t for t in await mcp.list_tools()}
    props = set(by_name["browser_click"].inputSchema.get("properties", {}))
    assert {"testid", "role", "name", "label", "placeholder", "text", "css"} <= props
    # browser_fill additionally requires the value to type
    fill_props = set(by_name["browser_fill"].inputSchema.get("properties", {}))
    assert "value" in fill_props
