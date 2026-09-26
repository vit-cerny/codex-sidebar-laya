import importlib.util
from pathlib import Path


SERVER = Path(__file__).parents[1] / "plugins" / "codex-sidebar-laya" / "scripts" / "mcp_server.py"
spec = importlib.util.spec_from_file_location("sidebar_laya_server", SERVER)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_parse_visible_dom_extracts_safe_actions():
    dom = '\n'.join([
        '<input node_id=4 aria-label="Search" type="text" />',
        '<button node_id=5 aria-label="Search now">Search</button>',
        '<input node_id=6 aria-label="Password" type="password" />',
        '<input node_id=7 aria-label="Remember me" type=checkbox />',
    ])
    actions = module._parse_visible_dom(dom)
    assert [action["id"] for action in actions] == ["4-fill", "5-click"]
    assert {action["node"] for action in actions} == {"4", "5"}


def test_parse_visible_dom_caps_action_count():
    dom = '\n'.join(f'<button node_id={index} aria-label="Action {index}">x</button>' for index in range(20))
    assert len(module._parse_visible_dom(dom)) == module.MAX_ACTIONS
