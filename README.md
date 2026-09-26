# Codex Sidebar Laya

Use local [Laya](https://github.com/NandhaKishorM/laya) to choose the next action in a Codex built-in browser tab. The plugin turns Codex's visible `node_id` DOM into Laya's action format, returns exactly one plan, and lets Codex's normal browser skill execute the action.

This is deliberately a planner, not a replacement browser driver. It cannot access cookies, passwords, or API keys; it cannot submit forms by itself; and it does not bypass Codex browser safety checks.

## What it does

1. Codex reads the live sidebar tab's accessible DOM.
2. Laya chooses a local next action from at most 12 safe visible controls.
3. Codex executes that chosen `node_id` in the same sidebar tab.
4. If Laya blocks/errors and the existing Jev runtime has `TYPESAFE_API_KEY`, the planner uses Jev's TypeSafe API for that decision only.
5. A redacted JSONL log records decision, engine, fallback, confidence, and elapsed time.

The first Laya decision can take about 40 seconds while the model loads. It may also block on complex pages. Treat `DONE` as a claim and verify the displayed result.

## Prerequisites

- Windows, Codex desktop, and its built-in Browser plugin.
- A working Jev/Laya checkout with the Laya model. The default location is `%USERPROFILE%\Documents\browseruse`.
- Python is already supplied by that Jev/Laya checkout; this plugin does not copy models or credentials.

## Install

Clone this repository, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

For a non-default Jev/Laya folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -BrowserUseRoot C:\path\to\browseruse
```

Restart Codex or start a new task. Then say:

> Use Sidebar Laya Browser to find an online chatbot and plan the next safe action.

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

Use `-KeepLogs` to retain `%USERPROFILE%\.codex-sidebar-laya\decisions.jsonl`.

## Logs and secrets

Decision logs are visible to Codex through `sidebar_laya_recent_decisions`. They record only timestamp, website host, engine, fallback, operation, node id, confidence, and latency. They do **not** store DOM text, prompts, typed values, cookies, passwords, or API keys.

Laya runs locally. Jev fallback is opt-in: set `TYPESAFE_API_KEY` only in the existing Jev runtime environment. This repository never writes it to config, logs, or Git.

## Known limits

- It adds a guided Laya/Jev planner to Codex; it cannot globally override Codex's own internal browser runtime.
- Codex remains responsible for clicks, typing, and confirmation gates. This keeps the action in the current sidebar tab and preserves the browser safety model.
- Laya is intentionally limited to 12 visible controls per step; on large pages Codex should narrow the page or scroll before asking again.

## Development smoke test

Use the included script after the Jev/Laya checkout is available:

```powershell
& "$env:USERPROFILE\Documents\browseruse\.venv\Scripts\python.exe" .\tests\test_planner.py
```
