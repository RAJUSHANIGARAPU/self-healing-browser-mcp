# self-healing-browser-mcp

[![CI](https://github.com/RAJUSHANIGARAPU/self-healing-browser-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RAJUSHANIGARAPU/self-healing-browser-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/protocol-MCP-8A2BE2)

An **[MCP](https://modelcontextprotocol.io) server** that hands an AI agent — Claude Desktop, Claude Code, Cursor, or anything that speaks MCP — a real browser to drive, with **self-healing locators**.

## Why

The moment you let an agent automate a browser, brittle selectors bite: a `data-testid` gets renamed, the DOM is restructured, a button's markup changes — and the run dies on a `locator not found`. Agents burn tokens retrying, or just give up.

This server takes a different contract. You describe an element by **whatever you know** — a test id, a role + accessible name, a label, some text, a CSS selector — and it resolves the element using the most stable strategy that still works. If your *preferred* locator has drifted, it **heals to a fallback and tells you so**, instead of failing.

## How the self-healing works

Each element tool accepts the same optional strategies. The resolver tries them in priority order and uses the first that matches **exactly one visible element**:

```
testid  →  role + name  →  label  →  placeholder  →  text  →  css  →  fuzzy (accessible-name match)
```

- If your first-choice strategy resolves the element, great — no heal.
- If it doesn't (renamed test id, changed structure) but a later strategy does, the result is flagged **`healed`** so you know the locator drifted and should be updated.
- If only a name is known and its casing/wording shifted, a final **fuzzy** pass matches the accessible name across interactive roles.

The agent "sees" the page semantically via `browser_snapshot` (roles + accessible names from the accessibility tree), not raw HTML or screenshots.

## Tools

| Tool | What it does |
|------|--------------|
| `browser_navigate(url)` | Open a URL in the shared page |
| `browser_snapshot()` | List interactive elements as `{role, name}` |
| `browser_click(...)` | Click an element (self-healing) |
| `browser_fill(value, ...)` | Type into a field (self-healing) |
| `browser_get_text(...)` | Read an element's text |
| `browser_assert_visible(...)` | Assert an element is visible — `PASS`/`FAIL` |
| `browser_close()` | Close the browser |

The `...` on element tools is the locator strategy set: `testid`, `role`, `name`, `label`, `placeholder`, `text`, `css` — all optional; pass as many as you know.

## Install

```bash
# install straight from the repo (PyPI release coming)
pip install "git+https://github.com/RAJUSHANIGARAPU/self-healing-browser-mcp"
python -m playwright install chromium
```

## Use it from an MCP client

**Claude Code:**

```bash
claude mcp add self-healing-browser -- self-healing-browser-mcp
```

**Claude Desktop / Cursor** — add to the MCP servers config:

```json
{
  "mcpServers": {
    "self-healing-browser": {
      "command": "self-healing-browser-mcp"
    }
  }
}
```

Then ask your agent to, e.g., *"open example.com, snapshot the page, and click the Sign in button."* When a selector has drifted, the tool result will say it healed.

### Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `SHBM_TESTID_ATTR` | `data-testid` | The attribute `testid` maps to (e.g. `data-test`, `data-cy`) |
| `SHBM_HEADED` | _(unset)_ | Set to `1` to watch the browser instead of running headless |

## Develop

```bash
pip install -e ".[dev]"
python -m playwright install chromium
pytest
```

The self-healing engine (`src/self_healing_browser_mcp/engine.py`) is decoupled from the MCP layer and tested deterministically against in-memory HTML — no external site, no flakiness.

## Releasing

Publishing to PyPI is automated with GitHub Actions via
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API
token is stored in the repo. Every push builds and `twine check`s the distribution in
CI, so `main` is always release-ready.

To cut a release:

1. **One-time:** on PyPI, create the `self-healing-browser-mcp` project's Trusted
   Publisher pointing at this repo, workflow `publish.yml`, and environment `pypi`.
2. Bump `version` in `pyproject.toml`, commit, and tag (`git tag v0.1.1 && git push --tags`).
3. Publish a GitHub Release for that tag — the `Publish to PyPI` workflow builds and
   uploads automatically. After that, `pip install self-healing-browser-mcp` works.

## License

MIT — see [LICENSE](LICENSE).
