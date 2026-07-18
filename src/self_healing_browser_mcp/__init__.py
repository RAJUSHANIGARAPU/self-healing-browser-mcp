"""self-healing-browser-mcp — an MCP server giving AI agents a browser with self-healing locators."""

from .engine import (
    BrowserSession,
    ElementNotFound,
    Hint,
    Resolution,
    resolve,
    snapshot_interactive,
)

__version__ = "0.1.0"
__all__ = [
    "BrowserSession",
    "ElementNotFound",
    "Hint",
    "Resolution",
    "resolve",
    "snapshot_interactive",
]
