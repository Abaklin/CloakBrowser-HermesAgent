# CloakBrowser Bug Fixes Reference

## Bug #1: click/type nth() Index Mismatch (CRITICAL)

**Symptom:** On any page with mixed element types (links + buttons + inputs), clicking @e5 would target the wrong element or fail entirely.

**Root Cause:** The ref ID (`@e1`, `@e2`, ...) is a **global counter** across all interactive roles. But Playwright's `.nth()` is **per-role**. So if @e5 is the 3rd button on a page, calling `page.get_by_role("button").nth(4)` (using global ref_num - 1) would try to access the 5th button, which doesn't exist.

**Evidence (Google homepage):**
```
@e3  button "Google 应用"       -> tool used nth(2) but should use nth(0)
@e5  button "添加文件和工具"    -> tool used nth(4) but should use nth(1)
@e19 button "设置"             -> tool used nth(18) but should use nth(6)
```
16 out of 19 elements had wrong nth() indices.

**Fix:** Track per-role index (`role_index`) during aria snapshot parsing. Use `nth(role_index)` instead of `nth(ref_num - 1)`.

## Bug #2: ref Parsing with lstrip

**Symptom:** `ref.lstrip("@e")` strips ALL leading `@` AND `e` characters, not just the prefix.

**Example:** `@ee12`.lstrip("@e") = "12" (correct by accident) but `@e1`.lstrip("@e") = "1" (correct). However `@@e1`.lstrip("@e") = "1" (wrong — strips too much).

**Fix:** Use `ref.startswith("@e")` then `ref[2:]` for precise prefix removal.

## Bug #3: exact=True Strict Mode Violation

**Symptom:** Clicking a link named "C" on Wikipedia times out after 5 seconds.

**Root Cause:** `page.get_by_role("link", name="C", exact=True)` matches 5 different links on Wikipedia. Playwright strict mode rejects multiple matches, causing a timeout instead of an immediate error.

**Fix:** Never use `exact=True` on `get_by_role()`. Always use `nth(role_index)` which is unambiguous.

## Bug #4: Screenshot Timeout on Long Pages

**Symptom:** `page.screenshot(full_page=True, timeout=30000)` times out on Wikipedia pages.

**Root Cause:** Rendering very long pages (Wikipedia has 1600+ interactive elements) exceeds 30 seconds for full-page screenshot.

**Fix:** Use `full_page=False, timeout=15000` for viewport screenshots. Full-page screenshots are unreliable on complex pages.

## Bug #5: Press Enter Navigation Timing

**Symptom:** After pressing Enter to submit a form, subsequent `evaluate()` calls fail with "Execution context was destroyed".

**Root Cause:** The 500ms wait after pressing Enter is insufficient for page navigation. The old page context is destroyed before the new one loads.

**Fix:** Use 2000ms wait for navigation-triggering keys (Enter, Return).

## aria_snapshot Parsing Logic

The correct approach for parsing `page.aria_snapshot()`:

```python
_ARIA_ELEMENT_RE = re.compile(
    r'^(\s*)- (link|button|textbox|combobox|checkbox|radio|searchbox|spinbutton|slider|menuitem|menuitemcheckbox|menuitemradio|option|tab)'
    r'(?:\s+"([^"]*)")?\s*:?\s*$'
)

_INTERACTIVE_ROLES = frozenset({
    "link", "button", "textbox", "combobox", "checkbox", "radio",
    "searchbox", "spinbutton", "slider", "menuitem", "menuitemcheckbox",
    "menuitemradio", "option", "tab",
})

def _parse_aria_snapshot(text: str):
    lines = text.split("\n")
    ref_counter = 0
    role_counters: dict[str, int] = {}  # per-role index tracker
    element_map: dict[int, dict] = {}

    for line in lines:
        m = _ARIA_ELEMENT_RE.match(line)
        if m:
            indent, role, name = m.group(1), m.group(2), m.group(3) or ""
            if role in _INTERACTIVE_ROLES:
                ref_counter += 1
                role_index = role_counters.get(role, 0)
                role_counters[role] = role_index + 1
                element_map[ref_counter] = {
                    "role": role,
                    "name": name,
                    "role_index": role_index,  # 0-based among same-role elements
                }
    
    return element_map
```

## Test Results Summary

| Category | Tests | Result |
|----------|-------|--------|
| Core tools (navigate, snapshot, evaluate, scroll, screenshot) | 7/7 | PASS |
| Click nth fix verification | 2/2 | PASS |
| Duplicate name click | 2/2 | PASS |
| Form interaction (type + enter) | 2/2 | PASS |
| Navigation (back) | 1/1 | PASS |
| Error handling (9 tools without session) | 9/9 | PASS |
| Session recovery | 3/3 | PASS |
| Ref parsing edge cases | 2/2 | PASS |
| Memory leak check (5 sequential navigations) | 1/1 | PASS |
| **Total** | **28/28** | **PASS** |
