---
name: sidebar-laya
description: Use local Laya to plan actions for Codex's in-app browser, with a Jev TypeSafe fallback and redacted decision logs. Trigger when the user asks Laya or Jev to work in the Codex sidebar browser.
---

# Sidebar Laya Browser

Use this skill when the user asks for autonomous or semi-autonomous browser work in Codex's built-in browser.

The `sidebar_laya_plan` MCP tool is a planner only. It receives the current visible DOM and returns one proposed `node_id`. It does not control browser tabs, send messages, or receive passwords/API keys.

## Required workflow

1. Use the Codex in-app Browser skill and obtain the active tab's visible DOM with `tab.dom_cua.get_visible_dom()`.
2. Call `sidebar_laya_plan` with the user goal, exact DOM string, current URL, title, and only the short visible text needed for completion checking.
3. Report the chosen engine and timing briefly in commentary.
4. Execute only the returned `node_id` with the Codex Browser skill:
   - `CLICK` -> `tab.dom_cua.click({ node_id })`
   - `TYPE_TEXT` -> first click the node, then type user-authorized text.
5. Re-observe the DOM after every action and make a new plan. Never repeat a browser mutation.
6. Stop at `DONE`, `BLOCKED`, an error, or the user's maximum requested number of steps.

## Safety

- Do not type or submit secrets, payment data, passwords, verification codes, or personal files.
- Ask immediately before a final form submission, sending a message, purchasing, uploading, changing access, or accepting browser permissions unless the user's initial request explicitly authorizes that exact action and destination.
- A plan is not proof of success. Confirm the outcome from the visible page.
- If Laya errors or blocks and `TYPESAFE_API_KEY` is configured in the Jev runtime environment, the MCP server automatically asks Jev's TypeSafe decision API for a replacement plan. It never returns the key.

## Logs

Call `sidebar_laya_recent_decisions` after a run when the user asks for timing or decision visibility. Logs contain timestamp, host, engine, fallback flag, operation, node id, confidence, and latency only. They intentionally exclude DOM text, prompts, and secrets.
