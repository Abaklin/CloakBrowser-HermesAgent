---
name: cloakbrowser
description: "Use when stealth browser access is needed to bypass bot detection (Cloudflare Turnstile, FingerprintJS, reCAPTCHA v3, BrowserScan). CloakBrowser provides a patched Chromium binary with 58 C++-level fingerprint modifications."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [browser, stealth, scraping, automation, cloakbrowser, anti-detect]
    homepage: https://github.com/CloakHQ/CloakBrowser
---

# CloakBrowser

## Overview

Stealth Chromium that passes every bot detection test. Not a patched config, not a JS injection -- a real Chromium binary with fingerprints modified at the C++ source level. Available as both a Python API (`from cloakbrowser import launch`) and native Hermes tools (`cloakbrowser_navigate`, etc.).

## When to Use

- User asks to access a site with anti-bot protection (Cloudflare, FingerprintJS, reCAPTCHA, Datadome, Kasada)
- User needs a browser that scores as "human" on detection services
- Scraping or automation tasks where the standard `browser_navigate` tool gets blocked
- Need human-like mouse/keyboard/scroll behavior (`humanize=True`)

**Don't use for:** Simple web browsing where the standard browser tool works fine. CloakBrowser is heavier (separate binary, separate session management).

## Key Features

- **58 source-level C++ patches** — canvas, WebGL, audio, fonts, GPU, screen, WebRTC, network timing, automation signals
- **humanize=True** — human-like mouse curves, keyboard timing, scroll patterns
- **0.9 reCAPTCHA v3 score** — human-level, server-verified
- **Passes** Cloudflare Turnstile, FingerprintJS, BrowserScan (30+ detection sites)
- **Auto-updating binary** — background update checks

## Installation

Already installed in Hermes venv:
```bash
pip install cloakbrowser  # Already done
```

Binary auto-downloads on first use (~200MB).

## Environment Variables

Set in `~/.hermes/.env` (adjust paths for your platform):
```
CLOAKBROWSER_CACHE_DIR=<hermes_home>/hermes-agent/CloakbrowerDate/cache
PLAYWRIGHT_BROWSERS_PATH=<hermes_home>/hermes-agent/CloakbrowerDate/playwright-browsers
```

On this Windows host, paths resolve to `D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\`.

If binary fails to download, verify `CLOAKBROWSER_CACHE_DIR` is set and the directory is writable.

## Hermes Native Tools

Available via the `cloakbrowser` toolset (off by default, enable via `hermes tools`):

| Tool | Description |
|------|-------------|
| `cloakbrowser_navigate` | Navigate to URL (opens stealth browser session) |
| `cloakbrowser_snapshot` | Get page accessibility tree with ref IDs |
| `cloakbrowser_click` | Click element by ref (e.g. @e5) |
| `cloakbrowser_type` | Type text into input field by ref |
| `cloakbrowser_press` | Press keyboard key (Enter, Tab, etc.) |
| `cloakbrowser_scroll` | Scroll page up or down |
| `cloakbrowser_back` | Navigate back |
| `cloakbrowser_screenshot` | Take page screenshot |
| `cloakbrowser_evaluate` | Execute JavaScript in page context |
| `cloakbrowser_close` | Close browser session |

## Python API (for execute_code)

```python
from cloakbrowser import launch, launch_context

# Basic usage
browser = launch()
page = browser.new_page()
page.goto("https://example.com")
print(page.title())
browser.close()

# With stealth options for anti-bot sites
browser = launch(
    proxy="http://user:pass@residential-proxy:port",
    geoip=True,
    headless=False,
    humanize=True,
)

# Persistent context (cookies/localStorage survive across sessions)
ctx = launch_context(
    user_data_dir="./my-profile",
    headless=False,
    humanize=True,
)
page = ctx.new_page()
page.goto("https://example.com")
ctx.close()  # Profile saved
```

## Common Parameters for launch()

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| headless | bool | True | Run in headless mode |
| proxy | str/dict | None | Proxy URL or Playwright proxy dict |
| geoip | bool | False | Auto-detect timezone/locale from proxy IP |
| humanize | bool | False | Enable human-like behavior |
| human_preset | str | "default" | "default" or "careful" |
| timezone | str | None | IANA timezone (e.g. "America/New_York") |
| locale | str | None | BCP 47 locale (e.g. "en-US") |
| backend | str | "playwright" | "playwright" or "patchright" |
| extension_paths | list | None | Chrome extension paths to load |

## Troubleshooting

### Binary not downloading
Check `CLOAKBROWSER_CACHE_DIR` is set correctly and writable.

### Still detected by anti-bot
- Use `headless=False` — some sites detect headless even with patches
- Add `humanize=True` for behavioral detection
- Use a residential proxy, not datacenter
- Try `backend="patchright"` for reCAPTCHA v3 Enterprise

### Windows GPU issues
On Windows, `--ignore-gpu-blocklist` is auto-added. If WebGL still fails, ensure GPU drivers are up to date.

### Version check
```python
from cloakbrowser.config import get_chromium_version, get_platform_tag
print(f"Platform: {get_platform_tag()}")
print(f"Chromium: {get_chromium_version()}")
```

## CloakBrowser Data Directory

All CloakBrowser data is stored at:
```
D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\
├── cache/                          # Stealth Chromium binaries
│   └── chromium-146.0.7680.177.5/  # Current version
│       └── chrome.exe
└── playwright-browsers/            # Playwright engine browsers
    └── chromium-1223/
```

The CloakBrowser source code is at:
```
D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\CloakBrowser\
```

## Common Pitfalls

### CRITICAL: How ref IDs and element targeting work internally
The `cloakbrowser_snapshot` tool uses `page.aria_snapshot()` (NOT `page.accessibility` — see pitfall #6 below) which returns a YAML-like string of all elements. The tool assigns `@e1`, `@e2`, etc. as **global sequential counters** across ALL interactive roles (links, buttons, inputs, etc.).

When `cloakbrowser_click` or `cloakbrowser_type` receives a ref like `@e5`, it must look up that element's **role_index** (its position among elements of the SAME role) and use `page.get_by_role(role).nth(role_index)` as the locator.

**Why this matters:** If you write custom code that uses the cloakbrowser Python API directly, you MUST follow this pattern:
```python
# WRONG: using global ref number with nth()
page.get_by_role("link").nth(4)  # ref @e5, but only 2 links on page -> FAILS

# CORRECT: use role_index (0-based among same-role elements)
page.get_by_role("link").nth(1)  # 2nd link on page
```

**Never use `exact=True` on `get_by_role()` when names may repeat** — multiple links/buttons with the same name (e.g., 5 links all named "C" on Wikipedia) triggers Playwright strict mode violation and causes a 5-second timeout. Always prefer `nth(role_index)`.

1. **Binary download fails on first run.** The ~200MB stealth Chromium binary downloads automatically on first `launch()`. If it fails, check network connectivity and that `CLOAKBROWSER_CACHE_DIR` is writable. You can also set `CLOAKBROWSER_BINARY_PATH` to a pre-downloaded binary.
2. **Still detected despite patches.** Some sites require `headless=False` (headed mode) because they detect headless browsers at a deeper level. Add `humanize=True` for behavioral detection bypass. For sites with strict anti-bot, use a residential proxy, not a datacenter one.
3. **`patchright` backend breaks proxy auth.** The `patchright` backend suppresses CDP signals (helpful for reCAPTCHA v3 Enterprise) but breaks proxy authentication and `add_init_script`. Use `backend="playwright"` (default) unless you specifically need patchright.
4. **Tool session leaks.** Each `cloakbrowser_navigate` creates a new browser session. Always call `cloakbrowser_close` when done, or the Chromium process will leak.
5. **Ref IDs are snapshot-scoped.** CloakBrowser tools use the same `@e1`, `@e2` ref ID format as the standard `browser_*` tools, but they are session-independent. You must call `cloakbrowser_snapshot` to get fresh ref IDs for each page.
6. **`page.accessibility` does not exist in Playwright Python.** The Node.js Playwright has `page.accessibility.snapshot()` which returns a dict tree. The Python binding **does not have this API**. Use `page.aria_snapshot()` instead, which returns a YAML-like string. The native `cloakbrowser_snapshot` tool handles this internally, but if you write custom code using the Python API directly, do NOT use `page.accessibility` — it will raise `AttributeError`. Use `page.aria_snapshot()` and parse the string output, or use standard Playwright locators (`page.locator()`, `page.get_by_role()`).
7. **Screenshot `full_page=True` times out on long pages.** On pages like Wikipedia with lots of content, `page.screenshot(full_page=True)` can exceed the default 30-second timeout. Use `full_page=False` or increase timeout to 15000ms minimum.
8. **Press Enter requires longer wait for navigation.** After pressing Enter (or other navigation-triggering keys), the page needs 2+ seconds to navigate. A 500ms wait causes "Execution context was destroyed" errors on subsequent `evaluate` calls. Use 2000ms+ wait after Enter/Return.
9. **Ref parsing must use exact `@e` prefix match.** `ref.lstrip("@e")` strips ALL leading `@` and `e` characters (e.g., `@ee12` becomes `12`). Use `ref.startswith("@e")` and slice `ref[2:]` for correct parsing.

## Linked Files

- `references/source-reference.md` -- Source code structure, binary resolution flow, env vars, Playwright integration details, and steps for adding CloakBrowser as a native Hermes toolset.
- `references/bug-fixes.md` -- Detailed bug investigation, root cause analysis, and fix recipes for 5 bugs discovered during tool verification (nth index mismatch, ref parsing, strict mode, screenshot timeout, Enter timing).
- `references/testing-guide.md` -- Integration verification checklist, reliable test URLs (avoid 404/401/403/500), multi-dimensional test scenarios, common integration mistakes, and performance benchmarks.
