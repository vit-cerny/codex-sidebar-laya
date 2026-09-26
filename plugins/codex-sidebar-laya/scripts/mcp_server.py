"""MCP decision service for the Codex in-app browser.

The service deliberately *plans* one action; it never receives browser credentials and never
drives the tab. Codex's Browser skill executes a returned node_id after its normal safety checks.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer

CONFIG_DIR = Path(os.environ.get("USERPROFILE", Path.home())) / ".codex-sidebar-laya"
CONFIG_PATH = CONFIG_DIR / "config.json"
LOG_PATH = CONFIG_DIR / "decisions.jsonl"
MAX_ACTIONS = 12
SENSITIVE = re.compile(r"(api[_ -]?key|authorization|bearer|password|token|secret|@)", re.I)


def _config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _browseruse_root() -> Path:
    configured = os.environ.get("SIDEBAR_LAYA_BROWSERUSE_ROOT") or _config().get("browserUseRoot")
    return Path(configured) if configured else Path.home() / "Documents" / "browseruse"


def _load_runtime() -> tuple[object, object, object]:
    root = _browseruse_root()
    if not (root / "jev_ultrafast" / "model.py").exists():
        raise RuntimeError("Jev/Laya runtime not found. Run install.ps1 with -BrowserUseRoot.")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from jev_config import load_env  # type: ignore
    from jev_ultrafast.model import choose_laya, choose_typesafe  # type: ignore
    from jev_security import redact  # type: ignore

    load_env()
    return choose_laya, choose_typesafe, redact


def _attribute(line: str, name: str) -> str:
    quoted = re.search(rf'{re.escape(name)}="([^"]*)"', line)
    if quoted:
        return quoted.group(1)
    bare = re.search(rf'{re.escape(name)}=([^\s>/]+)', line)
    return bare.group(1) if bare else ""


def _parse_visible_dom(visible_dom: str) -> list[dict]:
    """Turn Browser dom_cua output into Jev's restricted action schema."""
    actions: list[dict] = []
    for line in visible_dom.splitlines():
        node = _attribute(line, "node_id")
        if not node:
            continue
        tag = (re.match(r"\s*<([a-zA-Z0-9-]+)", line) or ["", ""])[1].lower()
        role = _attribute(line, "role") or tag
        label = _attribute(line, "aria-label") or _attribute(line, "placeholder") or role
        value = _attribute(line, "value")
        if SENSITIVE.search(label) or SENSITIVE.search(value):
            continue
        input_type = _attribute(line, "type").lower()
        if tag in {"input", "textarea"} and input_type not in {"password", "hidden", "file", "checkbox", "radio", "submit", "button"}:
            actions.append({"id": f"{node}-fill", "node": node, "kind": "fill", "role": role,
                            "label": label, "value": value})
        elif tag in {"button", "a", "select"} or role in {"button", "link", "combobox", "menuitem", "tab"}:
            actions.append({"id": f"{node}-click", "node": node, "kind": "click", "role": role,
                            "label": label, "value": value})
    return actions[:MAX_ACTIONS]


def _safe_host(url: str) -> str:
    return urlparse(url).netloc.lower()[:120]


def _append_log(entry: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _plan(goal: str, visible_dom: str, url: str = "", title: str = "", text: str = "") -> dict:
    if not goal.strip():
        return {"status": "error", "error": "goal is required"}
    actions = _parse_visible_dom(visible_dom)
    if not actions:
        return {"status": "blocked", "error": "no safe interactive elements in the supplied sidebar DOM"}

    state = {"url": url, "title": title[:200], "text": text[:600], "actions": actions}
    started = time.perf_counter()
    fallback = False
    reason = ""
    try:
        choose_laya, choose_typesafe, redact = _load_runtime()
        decision = choose_laya(state, goal, [])
        engine = "laya"
        laya_refused = decision.get("operation") == "BLOCKED"
        # Laya is known to produce false DONE responses when it cannot reason over the
        # action set. If actionable controls remain, ask the Jev provider to verify it.
        laya_unverified_done = decision.get("operation") == "DONE" and bool(actions)
        if (laya_refused or laya_unverified_done) and os.environ.get("TYPESAFE_API_KEY"):
            fallback, reason = True, "laya_blocked" if laya_refused else "laya_unverified_done"
            decision, engine = choose_typesafe(state, goal, []), "jev-typesafe"
        elif laya_unverified_done:
            return {
                "status": "needs_verification",
                "engine": "laya",
                "operation": "DONE",
                "latency_ms": decision.get("latency_ms"),
                "note": "Laya reported DONE while interactive controls remained. No action was taken and no Jev API fallback is configured.",
            }
    except Exception as error:
        safe_error = str(error)
        try:
            choose_laya, choose_typesafe, redact = _load_runtime()
            safe_error = redact(safe_error)
            if os.environ.get("TYPESAFE_API_KEY"):
                fallback, reason = True, "laya_error"
                decision, engine = choose_typesafe(state, goal, []), "jev-typesafe"
            else:
                return {"status": "error", "error": safe_error}
        except Exception:
            return {"status": "error", "error": "Laya decision failed; no configured Jev fallback is available"}

    action_by_id = {action["id"]: action for action in actions}
    action = action_by_id.get(str(decision.get("choice")))
    result = {
        "status": "ok" if action else str(decision.get("operation", "blocked")).lower(),
        "engine": engine,
        "fallback": fallback,
        "fallback_reason": reason or None,
        "operation": decision.get("operation"),
        "node_id": action.get("node") if action else None,
        "kind": action.get("kind") if action else None,
        "role": action.get("role") if action else None,
        "confidence": decision.get("confidence"),
        "latency_ms": decision.get("latency_ms", round((time.perf_counter() - started) * 1000)),
        "requires_text": bool(action and action.get("kind") == "fill"),
        "note": "This is a plan only. Execute node_id through Codex Browser after normal safety checks.",
    }
    _append_log({
        "at": datetime.now(UTC).isoformat(), "host": _safe_host(url), "engine": engine,
        "fallback": fallback, "reason": reason or None, "operation": result["operation"],
        "node_id": result["node_id"], "kind": result["kind"], "confidence": result["confidence"],
        "latency_ms": result["latency_ms"],
    })
    return result


server = MCPServer(
    name="sidebar-laya",
    version="0.1.0",
    instructions=(
        "Plans one next action for a Codex in-app browser tab. Pass dom_cua visible DOM output. "
        "It uses local Laya first and may use the configured Jev TypeSafe key only after Laya blocks or errors. "
        "It does not execute actions, send prompts, or expose credentials."
    ),
)


@server.tool(description="Plan one safe next action for the built-in Codex browser. Pass the exact visible DOM from dom_cua. The returned node_id must be executed only through the Codex Browser skill.")
def sidebar_laya_plan(goal: str, visible_dom: str, url: str = "", title: str = "", text: str = "") -> str:
    return json.dumps(_plan(goal, visible_dom, url, title, text), ensure_ascii=False, indent=2)


@server.tool(description="Return redacted Laya/Jev decision timing history for display in chat. It never includes page text, typed prompts, credentials, or API keys.")
def sidebar_laya_recent_decisions(limit: int = 20) -> str:
    try:
        rows = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    except FileNotFoundError:
        rows = []
    return json.dumps(rows[-max(0, min(limit, 100)):], ensure_ascii=False, indent=2)


@server.tool(description="Check whether the local Laya runtime and optional Jev TypeSafe fallback are available. This never reads or returns secrets.")
def sidebar_laya_status() -> str:
    root = _browseruse_root()
    return json.dumps({
        "browseruse_root": str(root),
        "runtime_ready": (root / ".venv" / "Scripts" / "python.exe").exists() and (root / "jev_ultrafast" / "model.py").exists(),
        "laya_model_ready": (root / "models" / "laya-typed-decisions" / "model.safetensors").exists(),
        "jev_typesafe_fallback_configured": bool(os.environ.get("TYPESAFE_API_KEY")),
        "log_path": str(LOG_PATH),
    }, indent=2)


if __name__ == "__main__":
    server.run()
