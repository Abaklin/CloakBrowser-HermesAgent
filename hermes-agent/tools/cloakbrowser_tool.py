#!/usr/bin/env python3
"""
CloakBrowser Tool Module

Stealth Chromium browser that passes bot detection tests. Drop-in Playwright
replacement with source-level fingerprint patches at the C++ level.

Usage:
    from tools.cloakbrowser_tool import cloakbrowser_navigate, cloakbrowser_snapshot
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from typing import Any

logger = logging.getLogger("cloakbrowser_tool")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_sessions: dict[str, dict[str, Any]] = {}


def _get_session(task_id: str | None = None) -> dict[str, Any] | None:
    tid = task_id or "default"
    return _sessions.get(tid)


def _set_session(task_id: str | None, session: dict[str, Any]) -> None:
    tid = task_id or "default"
    _sessions[tid] = session


def _clear_session(task_id: str | None = None) -> None:
    tid = task_id or "default"
    session = _sessions.pop(tid, None)
    if session:
        try:
            browser = session.get("browser")
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            pw = session.get("playwright")
            if pw:
                pw.stop()
        except Exception:
            pass


def _launch_browser(headless: bool = True, **kwargs) -> dict[str, Any]:
    """Launch a stealth Chromium browser using CloakBrowser."""
    from cloakbrowser.config import DEFAULT_VIEWPORT, IGNORE_DEFAULT_ARGS
    from cloakbrowser.browser import build_args
    from cloakbrowser.download import ensure_binary
    from playwright.sync_api import sync_playwright

    binary_path = ensure_binary()
    chrome_args = build_args(stealth_args=True, extra_args=[], headless=headless)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        executable_path=binary_path,
        headless=headless,
        args=chrome_args,
        ignore_default_args=IGNORE_DEFAULT_ARGS,
    )
    context = browser.new_context(viewport=DEFAULT_VIEWPORT)
    page = context.new_page()

    original_close = browser.close
    def _close_with_cleanup():
        try:
            original_close()
        finally:
            try:
                pw.stop()
            except Exception:
                pass
    browser.close = _close_with_cleanup

    return {"browser": browser, "playwright": pw, "context": context, "page": page, "binary_path": binary_path}


# ---------------------------------------------------------------------------
# Aria snapshot parsing
# ---------------------------------------------------------------------------
_INTERACTIVE_ROLES = frozenset({
    "link", "button", "textbox", "combobox", "checkbox", "radio",
    "searchbox", "spinbutton", "slider", "menuitem", "menuitemcheckbox",
    "menuitemradio", "option", "tab",
})

_ARIA_ELEMENT_RE = re.compile(
    r'^(\s*)- (link|button|textbox|combobox|checkbox|radio|searchbox|spinbutton|slider|menuitem|menuitemcheckbox|menuitemradio|option|tab)'
    r'(?:\s+"([^"]*)")?\s*:?\s*$'
)


def _parse_aria_snapshot(text: str) -> tuple[str, dict[int, dict]]:
    """Parse aria_snapshot text and assign [@eN] refs to interactive elements.
    
    Returns (formatted_snapshot_text, element_map).
    element_map keys are integer ref numbers, values are {role, name, role_index}.
    role_index is the 0-based index among elements of the same role (for nth() lookup).
    """
    lines = text.split("\n")
    result_lines: list[str] = []
    ref_counter = 0
    role_counters: dict[str, int] = {}  # per-role index tracker
    element_map: dict[int, dict] = {}

    for line in lines:
        m = _ARIA_ELEMENT_RE.match(line)
        if m:
            indent = m.group(1)
            role = m.group(2)
            name = m.group(3) if m.group(3) else ""

            if role in _INTERACTIVE_ROLES:
                ref_counter += 1
                role_index = role_counters.get(role, 0)
                role_counters[role] = role_index + 1
                ref_id = f"[@e{ref_counter}]"
                element_map[ref_counter] = {"role": role, "name": name, "role_index": role_index}
                name_part = f' "{name}"' if name else ""
                result_lines.append(f"{indent}- {ref_id} {role}{name_part}:")
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    return "\n".join(result_lines), element_map


def _page_snapshot(page, full: bool = False) -> tuple[str, dict]:
    """Get aria snapshot and parse it. Returns (text, element_map)."""
    try:
        raw = page.aria_snapshot()
        return _parse_aria_snapshot(raw)
    except Exception as e:
        return f"[Snapshot error: {e}]", {}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def cloakbrowser_navigate(url: str = "", headless: bool = True,
                          humanize: bool = False, proxy: str = None,
                          task_id: str = None) -> str:
    _clear_session(task_id)
    try:
        session = _launch_browser(headless=headless)
        _set_session(task_id, session)
        page = session["page"]
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        snapshot_text, _ = _page_snapshot(page, full=False)
        return json.dumps({
            "success": True,
            "title": page.title(),
            "url": page.url,
            "snapshot": snapshot_text,
            "headless": headless,
            "humanize": humanize,
            "binary": str(session["binary_path"]),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        _clear_session(task_id)
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)


def cloakbrowser_snapshot(full: bool = False, task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session. Call cloakbrowser_navigate first."})
    try:
        page = session["page"]
        snapshot_text, _ = _page_snapshot(page, full=full)
        return json.dumps({
            "success": True,
            "title": page.title(),
            "url": page.url,
            "snapshot": snapshot_text,
            "full": full,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_click(ref: str = "", task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        # Parse current snapshot to find element
        snapshot_text, element_map = _page_snapshot(page)
        
        try:
            # Properly parse @eN format: strip leading @e exactly
            ref_str = ref.strip()
            if ref_str.startswith("@e"):
                ref_num = int(ref_str[2:])
            else:
                ref_num = int(ref_str)
        except (ValueError, AttributeError):
            return json.dumps({"success": False, "error": f"Invalid ref format: {ref}. Expected @e1, @e2, etc."})

        if ref_num not in element_map:
            available = ", ".join(f"@e{k}" for k in sorted(element_map.keys())[:10])
            return json.dumps({
                "success": False,
                "error": f"Ref {ref} not found. {len(element_map)} interactive elements on page. Available: {available}..."
            })

        elem = element_map[ref_num]
        role = elem["role"]
        name = elem["name"]

        # Use Playwright locator to click
        elem_info = element_map[ref_num]
        role_index = elem_info.get("role_index", 0)
        
        # Always use nth(role_index) to avoid strict mode violations
        # when multiple elements share the same name (e.g., many links named "a")
        all_elements = page.get_by_role(role)
        locator = all_elements.nth(role_index)

        locator.click(timeout=5000)
        page.wait_for_timeout(500)
        
        return json.dumps({
            "success": True,
            "clicked": f"{role} \"{name}\"",
            "new_url": page.url,
            "new_title": page.title(),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_type(ref: str = "", text: str = "", task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        snapshot_text, element_map = _page_snapshot(page)
        
        try:
            # Properly parse @eN format: strip leading @e exactly
            ref_str = ref.strip()
            if ref_str.startswith("@e"):
                ref_num = int(ref_str[2:])
            else:
                ref_num = int(ref_str)
        except (ValueError, AttributeError):
            return json.dumps({"success": False, "error": f"Invalid ref format: {ref}"})

        if ref_num not in element_map:
            return json.dumps({"success": False, "error": f"Ref {ref} not found."})

        elem = element_map[ref_num]
        role = elem["role"]
        name = elem["name"]

        elem_info = element_map[ref_num]
        role_index = elem_info.get("role_index", 0)
        
        # Always use nth(role_index) for precise element targeting
        locator = page.get_by_role(role).nth(role_index)

        locator.click()
        locator.fill(text, timeout=5000)
        
        return json.dumps({
            "success": True,
            "typed": text,
            "into": f"{role} \"{name}\"",
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_press(key: str = "", task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        # Navigation-triggering keys need longer wait
        nav_keys = {"Enter", "Return"}
        page.keyboard.press(key)
        wait_ms = 2000 if key in nav_keys else 500
        page.wait_for_timeout(wait_ms)
        return json.dumps({
            "success": True,
            "key": key,
            "url": page.url,
            "title": page.title(),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_scroll(direction: str = "down", task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        amount = 500 if direction == "down" else -500
        page.mouse.wheel(0, amount)
        page.wait_for_timeout(300)
        return json.dumps({"success": True, "direction": direction, "url": page.url})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_back(task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        page.go_back(wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        return json.dumps({"success": True, "url": page.url, "title": page.title()})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_close(task_id: str = None) -> str:
    try:
        _clear_session(task_id)
        return json.dumps({"success": True, "message": "Browser session closed."})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_screenshot(path: str = None, task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        if path is None:
            path = os.path.join(tempfile.gettempdir(), f"cloakbrowser_screenshot_{int(time.time())}.png")
        page.screenshot(path=path, full_page=False, timeout=15000)
        return json.dumps({"success": True, "path": path, "url": page.url})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_evaluate(expression: str = "", task_id: str = None) -> str:
    session = _get_session(task_id)
    if not session:
        return json.dumps({"success": False, "error": "No active browser session."})
    try:
        page = session["page"]
        result = page.evaluate(expression)
        return json.dumps({"success": True, "result": str(result)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def cloakbrowser_console(clear: bool = False, task_id: str = None) -> str:
    return json.dumps({"success": True, "message": "Use cloakbrowser_evaluate for JS inspection."})


# ---------------------------------------------------------------------------
# Requirements check
# ---------------------------------------------------------------------------
def check_cloakbrowser_requirements() -> bool:
    try:
        import cloakbrowser
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------
CLOAKBROWSER_SCHEMAS = [
    {"name": "cloakbrowser_navigate", "description": "Navigate to a URL using CloakBrowser stealth Chromium. Opens a new stealth browser session. Must be called before other cloakbrowser tools.", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "The URL to navigate to"}, "headless": {"type": "boolean", "default": True, "description": "Run in headless mode (default True)"}, "humanize": {"type": "boolean", "default": False, "description": "Enable human-like mouse/keyboard/scroll behavior"}, "proxy": {"type": "string", "default": None, "description": "Optional proxy URL"}}, "required": ["url"]}},
    {"name": "cloakbrowser_snapshot", "description": "Get a text-based snapshot of the current page's accessibility tree. Returns interactive elements with ref IDs (like @e1, @e2).", "parameters": {"type": "object", "properties": {"full": {"type": "boolean", "default": False, "description": "If true, returns complete page content"}}, "required": []}},
    {"name": "cloakbrowser_click", "description": "Click on an element identified by its ref ID from the snapshot (e.g. '@e5').", "parameters": {"type": "object", "properties": {"ref": {"type": "string", "description": "The element reference from the snapshot (e.g. '@e5', '@e12')"}}, "required": ["ref"]}},
    {"name": "cloakbrowser_type", "description": "Type text into an input field identified by its ref ID. Clears the field first.", "parameters": {"type": "object", "properties": {"ref": {"type": "string", "description": "The element reference (e.g. '@e3')"}, "text": {"type": "string", "description": "The text to type"}}, "required": ["ref", "text"]}},
    {"name": "cloakbrowser_press", "description": "Press a keyboard key. Useful for submitting forms (Enter), navigating (Tab), or shortcuts.", "parameters": {"type": "object", "properties": {"key": {"type": "string", "description": "Key to press (e.g. 'Enter', 'Tab', 'Escape')"}}, "required": ["key"]}},
    {"name": "cloakbrowser_scroll", "description": "Scroll the page. Use to reveal content below or above the viewport.", "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"], "description": "Direction to scroll"}}, "required": ["direction"]}},
    {"name": "cloakbrowser_back", "description": "Navigate back to the previous page in browser history.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "cloakbrowser_screenshot", "description": "Take a screenshot of the current page.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": None, "description": "Optional file path to save. Defaults to temp file."}}, "required": []}},
    {"name": "cloakbrowser_evaluate", "description": "Evaluate JavaScript in the page context. Use for DOM inspection, reading page state, or extracting data.", "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "JavaScript expression to evaluate"}}, "required": ["expression"]}},
    {"name": "cloakbrowser_close", "description": "Close the current CloakBrowser session and free resources.", "parameters": {"type": "object", "properties": {}, "required": []}},
]

_SCHEMA_MAP = {s["name"]: s for s in CLOAKBROWSER_SCHEMAS}

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry

registry.register(name="cloakbrowser_navigate", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_navigate"],
    handler=lambda args, **kw: cloakbrowser_navigate(url=args.get("url",""), headless=args.get("headless",True), humanize=args.get("humanize",False), proxy=args.get("proxy"), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F977")

registry.register(name="cloakbrowser_snapshot", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_snapshot"],
    handler=lambda args, **kw: cloakbrowser_snapshot(full=args.get("full",False), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F4F8")

registry.register(name="cloakbrowser_click", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_click"],
    handler=lambda args, **kw: cloakbrowser_click(ref=args.get("ref",""), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F446")

registry.register(name="cloakbrowser_type", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_type"],
    handler=lambda args, **kw: cloakbrowser_type(ref=args.get("ref",""), text=args.get("text",""), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\u2328\ufe0f")

registry.register(name="cloakbrowser_press", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_press"],
    handler=lambda args, **kw: cloakbrowser_press(key=args.get("key",""), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F518")

registry.register(name="cloakbrowser_scroll", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_scroll"],
    handler=lambda args, **kw: cloakbrowser_scroll(direction=args.get("direction","down"), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F4DC")

registry.register(name="cloakbrowser_back", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_back"],
    handler=lambda args, **kw: cloakbrowser_back(task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\u25C0\ufe0f")

registry.register(name="cloakbrowser_screenshot", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_screenshot"],
    handler=lambda args, **kw: cloakbrowser_screenshot(path=args.get("path"), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F5BC\ufe0f")

registry.register(name="cloakbrowser_evaluate", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_evaluate"],
    handler=lambda args, **kw: cloakbrowser_evaluate(expression=args.get("expression",""), task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F4BB")

registry.register(name="cloakbrowser_close", toolset="cloakbrowser", schema=_SCHEMA_MAP["cloakbrowser_close"],
    handler=lambda args, **kw: cloakbrowser_close(task_id=kw.get("task_id")),
    check_fn=check_cloakbrowser_requirements, emoji="\U0001F6AA")
