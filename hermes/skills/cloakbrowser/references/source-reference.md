# CloakBrowser Source Code Reference

## Repository Location

```
D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\CloakBrowser\
```

This is a git clone of https://github.com/CloakHQ/CloakBrowser (main branch).

## Key Source Files

| File | Purpose |
|------|---------|
| `cloakbrowser/browser.py` | Main launch functions: `launch()`, `launch_async()`, `launch_persistent_context()`, `launch_context()` |
| `cloakbrowser/config.py` | Platform detection, cache paths, binary paths, stealth args, download URLs |
| `cloakbrowser/download.py` | Binary download and cache management (`ensure_binary()`) |
| `cloakbrowser/geoip.py` | GeoIP resolution for timezone/locale from proxy IP |
| `cloakbrowser/human/` | Human-like behavioral patching (mouse, keyboard, scroll) |
| `pyproject.toml` | Package metadata, dependencies, entry points |

## Binary Resolution Flow

1. `ensure_binary()` in `download.py` is called on every `launch()`
2. Checks `CLOAKBROWSER_BINARY_PATH` env var first (local override)
3. Falls back to cache dir: `CLOAKBROWSER_CACHE_DIR/chromium-<version>/chrome.exe`
4. If binary not found, downloads from `https://cloakbrowser.dev/chromium-v<version>/cloakbrowser-<platform>.zip`
5. Version: `146.0.7680.177.5` (Windows x64, as of v0.3.31)

## Critical Environment Variables

| Variable | Purpose |
|----------|---------|
| `CLOAKBROWSER_CACHE_DIR` | Override binary cache directory (default: `~/.cloakbrowser/`) |
| `CLOAKBROWSER_BINARY_PATH` | Skip download, use local Chromium binary |
| `CLOAKBROWSER_DOWNLOAD_URL` | Override download base URL |
| `CLOAKBROWSER_BACKEND` | Override backend: `playwright` (default) or `patchright` |
| `PLAYWRIGHT_BROWSERS_PATH` | Override Playwright browser engine path |

## Default Stealth Args (Windows)

```
--no-sandbox
--fingerprint=<random_seed>
--fingerprint-platform=windows
--ignore-gpu-blocklist  (auto-added on Windows)
```

## Platform Detection

`SUPPORTED_PLATFORMS` in `config.py`:
- `("Windows", "AMD64")` -> `"windows-x64"`
- `("Windows", "x86_64")` -> `"windows-x64"`

## Binary Cache Structure

```
<CLOAKBROWSER_CACHE_DIR>/
  chromium-146.0.7680.177.5/
    chrome.exe              # The patched Chromium binary
  latest_version_windows-x64  # Auto-update marker file
  .welcome_shown              # First-run marker
```

## Integration with Playwright

CloakBrowser is a thin wrapper around Playwright:
- Uses `playwright.sync_api.sync_playwright` (or `async_playwright`)
- Passes custom `executable_path` to `pw.chromium.launch()`
- Sets `ignore_default_args=["--enable-automation", "--enable-unsafe-swiftshader"]`
- Returns a standard Playwright `Browser` object with patched `close()`

## Adding CloakBrowser to Hermes as a Native Toolset

### Files to create/modify

1. **Create** `tools/cloakbrowser_tool.py`:
   - Define tool handlers (navigate, snapshot, click, type, etc.)
   - Define `CLOAKBROWSER_SCHEMAS` list (one schema per tool)
   - Register each tool via `registry.register()` with `toolset="cloakbrowser"`
   - Include `check_fn=check_cloakbrowser_requirements` that imports cloakbrowser

2. **Edit** `toolsets.py`:
   - Add `"cloakbrowser"` entry to `TOOLSETS` dict with `"off_by_default": True`
   - Add all cloakbrowser tool names to `_HERMES_CORE_TOOLS` list

3. **Edit** `~/.hermes/.env`:
   - Set `CLOAKBROWSER_CACHE_DIR` and `PLAYWRIGHT_BROWSERS_PATH`

4. **Install** Python package:
   - `pip install cloakbrowser` into the Hermes venv

### Tool naming convention

Tools use the `cloakbrowser_` prefix to distinguish from the existing `browser_` toolset (which uses agent-browser). The ref ID format (`@e1`, `@e2`) is identical for compatibility.

### Snapshot Implementation: `aria_snapshot()` vs `accessibility`

The native `cloakbrowser_snapshot` tool uses `page.aria_snapshot()` to generate the accessibility tree. This is **not** the same as Node.js Playwright's `page.accessibility.snapshot()`:

| Feature | Node.js `accessibility.snapshot()` | Python `aria_snapshot()` |
|---------|-----------------------------------|--------------------------|
| Return type | Dict tree (JSON) | YAML-like string |
| Python available? | No (AttributeError) | Yes |
| Structure | Nested objects with `role`, `name`, `children` | Indented text with `- role "name"` per line |

The `_parse_aria_snapshot()` function in `cloakbrowser_tool.py` parses the string format:
- Scans for interactive elements: `link`, `button`, `textbox`, `combobox`, `checkbox`, `radio`, `spinbutton`, `listbox`
- Extracts the element name from quoted strings (e.g., `- link "Learn More"`)
- Dynamically assigns `[@e1]`, `[@e2]`, etc. ref IDs
- Returns both the formatted text snapshot and an `elements` dict mapping ref IDs to `{role, name, selector}`

If you need to modify the snapshot logic, look for `_parse_aria_snapshot()` in `tools/cloakbrowser_tool.py`. The regex pattern matches lines like:
```
- link "Click me"
- textbox "Search"
- button "Submit" [cursor=12]
```

### Verification Checklist

After setting up CloakBrowser native tools, verify with:
1. `cloakbrowser_navigate("https://example.com")` — should return URL and status
2. `cloakbrowser_snapshot()` — should return text with `[@eN]` ref IDs
3. `cloakbrowser_click("@e1")` — should click the first interactive element
4. `cloakbrowser_close()` — should terminate the Chromium process
