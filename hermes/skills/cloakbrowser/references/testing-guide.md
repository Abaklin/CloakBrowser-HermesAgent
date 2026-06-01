# CloakBrowser Testing & Integration Verification

## Integration Checklist

When verifying cloakbrowser is properly installed in Hermes:

1. **Tool file exists**: `tools/cloakbrowser_tool.py` (should be ~450+ lines)
2. **Auto-discovery**: `model_tools.discover_builtin_tools()` should find `tools.cloakbrowser_tool`
   - The auto-scan checks for `registry.register(` in the file
   - No manual import in `model_tools.py` needed (unlike older docs suggest)
3. **Toolset configured**: `toolsets.py` should have:
   - `"cloakbrowser_navigate", ...` in `_HERMES_CORE_TOOLS` (or a dedicated toolset)
   - `"cloakbrowser": {...}` in `TOOLSETS` dict with `off_by_default=True`
4. **Registry verification**: After import, `registry.get_all_tool_names()` should include all 10 cloakbrowser tools

## Recommended Test URLs (Avoid 404/401/403/500)

These URLs are reliable for testing:

| URL | Purpose | Notes |
|-----|---------|-------|
| `https://example.com` | Basic navigation | Minimal page, 1 link |
| `https://httpbin.org/html` | Content extraction | Static HTML |
| `https://httpbin.org/json` | JSON response | Raw JSON page |
| `https://httpbin.org/headers` | API inspection | Shows request headers |
| `https://www.google.com` | Mixed elements | 7 buttons, 11 links - good for nth() testing |
| `https://duckduckgo.com` | Form interaction | Search box + submit workflow |
| `https://en.wikipedia.org/wiki/Main_Page` | Complex page | 100+ interactive elements |
| `https://en.wikipedia.org/wiki/Python_(programming_language)` | Stress test | 1600+ interactive elements |
| `https://www.w3.org` | Screenshot target | Good visual page |
| `https://jsonplaceholder.typicode.com/posts/1` | JSON API | Simple JSON response |

**Avoid**: `w3c.org` (connection closed), any URL that might return auth errors or server errors.

## Multi-Dimensional Test Scenarios

### 1. Core Functionality (7 tests)
- navigate, snapshot, evaluate, scroll down/up, screenshot, back

### 2. Bug Fix Verification (4 tests)
- Click non-first button (tests nth fix)
- Click duplicate name link (tests strict mode fix)
- Type with special characters (tests type fix)
- Screenshot on long page (tests timeout fix)

### 3. Form Interaction (2 tests)
- Type in search box + Enter + verify results
- Special character input (Chinese, symbols)

### 4. Error Handling (9 tests)
- All 10 tools should return `{"success": false, "error": "..."}` without session
- Invalid URL should return error, not crash
- Session recovery after error should work

### 5. Stress Testing (2 tests)
- 5+ sequential navigate/close cycles (memory leak check)
- 1000+ element snapshot parsing

### 6. Navigation Flow (2 tests)
- Click link -> back navigation
- Multi-page sequential navigation

## Common Integration Mistakes

1. **Assuming manual import needed**: The Chinese community docs mention adding to `model_tools.py` `_discover_tools()`, but modern Hermes uses auto-discovery via `discover_builtin_tools()` which scans `tools/*.py` for `registry.register(` calls.

2. **Tool not appearing in definitions**: The toolset is `off_by_default=True`. You must enable it via `hermes tools` command or `enabled_toolsets=["cloakbrowser"]` in `get_tool_definitions()`.

3. **Testing with bad URLs**: Using URLs that return 404/401/403/500 will make tests fail for network reasons, not code reasons. Always use known-good URLs for code verification.

## Test Execution Pattern

```python
import json, sys, importlib
sys.path.insert(0, "<hermes_agent_path>")
import tools.cloakbrowser_tool as cb_tool
importlib.reload(cb_tool)

# Run test
r = json.loads(cb_tool.cloakbrowser_navigate("https://example.com"))
assert r["success"], r.get("error")

# Verify snapshot has refs
r = json.loads(cb_tool.cloakbrowser_snapshot())
assert "@e1" in r["snapshot"]

# Cleanup
cb_tool.cloakbrowser_close()
```

## Performance Benchmarks

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Navigate (cold start) | 3-7s | First run downloads binary |
| Navigate (warm) | 3-5s | Binary already cached |
| Snapshot | <0.1s | Text parsing only |
| Click | 0.5-1.5s | Depends on page load |
| Type | 0.1-0.3s | Fast |
| Screenshot | 0.1-2.5s | full_page=False is faster |
| Close | 0.3s | Cleanup |
