"""tests/test_claude_settings.py — settings.json-এ হুক merge/remove নিয়ম (techspec §4.3)।

চালানো: pytest tests/test_claude_settings.py
সব টেস্ট pytest-এর tmp_path-এ নিজের settings.json নিয়ে কাজ করে — আসল
~/.claude/settings.json কখনো পড়া বা লেখা হয় না।
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import claude_settings as cs

FOREIGN_HOOK = {"hooks": [{"type": "command", "command": "echo someone-else"}]}
FOREIGN_STATUSLINE = {"type": "command", "command": "echo my status line"}


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path.read_text(encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def backups(tmp_path):
    return sorted(p.name for p in tmp_path.iterdir() if ".wsr-backup-" in p.name)


def test_install_into_missing_file(tmp_path):
    target = tmp_path / "settings.json"
    result = cs.install(target)
    assert result.ok
    data = read(target)
    assert sorted(data["hooks"]) == sorted(e for e, _m in cs.HOOK_EVENTS)
    assert data["hooks"]["PostToolUse"][0]["matcher"] == "*"
    assert cs.marker() in data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert backups(tmp_path) == []          # ফাইলই ছিল না, তাই ব্যাকআপ নেই


def test_install_writes_backup_first(tmp_path):
    target = tmp_path / "settings.json"
    original = write(target, {"effortLevel": "max"})
    result = cs.install(target)
    assert result.ok and result.backup
    assert (tmp_path / os.path.basename(result.backup)).read_text(encoding="utf-8") == original


def test_install_keeps_foreign_keys_and_hooks(tmp_path):
    target = tmp_path / "settings.json"
    write(target, {
        "permissions": {"allow": ["Bash(ls)"]},
        "statusLine": FOREIGN_STATUSLINE,
        "hooks": {"PreToolUse": [FOREIGN_HOOK], "Stop": [FOREIGN_HOOK]},
    })
    assert cs.install(target).ok
    data = read(target)
    assert data["permissions"] == {"allow": ["Bash(ls)"]}
    assert data["statusLine"] == FOREIGN_STATUSLINE      # statusLine আমরা কখনো ছুঁই না
    assert data["hooks"]["PreToolUse"] == [FOREIGN_HOOK]  # অন্যের ইভেন্ট অবিকৃত
    assert data["hooks"]["Stop"][0] == FOREIGN_HOOK       # অন্যের এন্ট্রি আগে, আমাদের পরে
    assert cs.marker() in json.dumps(data["hooks"]["Stop"][1])


def test_install_never_adds_a_statusline(tmp_path):
    target = tmp_path / "settings.json"
    cs.install(target)
    assert "statusLine" not in read(target)              # usage ফিচার বাদ (tracker 2026-10-20)


def test_install_is_idempotent(tmp_path):
    target = tmp_path / "settings.json"
    cs.install(target)
    first = target.read_text(encoding="utf-8")
    second = cs.install(target)
    assert second.ok and second.changed == []
    assert target.read_text(encoding="utf-8") == first    # দ্বিতীয়বারে কিছুই বদলায়নি
    assert len(read(target)["hooks"]["SessionStart"]) == 1
    assert backups(tmp_path) == []                        # বদল নেই → ব্যাকআপও নেই


def test_remove_restores_file_byte_for_byte(tmp_path):
    # plan Step B gate: install → remove-এর পর ফাইল আগের মতোই (diff খালি)
    target = tmp_path / "settings.json"
    original = write(target, {
        "permissions": {"allow": ["Bash(flutter build *)"]},
        "effortLevel": "max",
    })
    cs.install(target)
    assert cs.remove(target).ok
    assert target.read_text(encoding="utf-8") == original


def test_remove_keeps_foreign_entries(tmp_path):
    target = tmp_path / "settings.json"
    write(target, {"statusLine": FOREIGN_STATUSLINE,
                   "hooks": {"Stop": [FOREIGN_HOOK], "PreToolUse": [FOREIGN_HOOK]}})
    cs.install(target)
    cs.remove(target)
    data = read(target)
    assert data["hooks"] == {"Stop": [FOREIGN_HOOK], "PreToolUse": [FOREIGN_HOOK]}
    assert data["statusLine"] == FOREIGN_STATUSLINE


def test_remove_only_matches_our_port(tmp_path):
    target = tmp_path / "settings.json"
    cs.install(target, port=47821)
    before = target.read_text(encoding="utf-8")
    result = cs.remove(target, port=47999)               # অন্য পোর্টের মার্কার — আমাদের নয়
    assert result.ok and result.changed == []
    assert target.read_text(encoding="utf-8") == before


def test_remove_on_clean_file_changes_nothing(tmp_path):
    target = tmp_path / "settings.json"
    original = write(target, {"effortLevel": "max"})
    result = cs.remove(target)
    assert result.ok and result.changed == []
    assert target.read_text(encoding="utf-8") == original


def test_invalid_json_aborts_without_writing(tmp_path):
    target = tmp_path / "settings.json"
    broken = '{"effortLevel": "max",}\n'                 # ট্রেইলিং কমা — JSON নয়
    target.write_text(broken, encoding="utf-8")
    for action in (cs.install, cs.remove, cs.status):
        result = action(target)
        assert not result.ok
        assert "not valid JSON" in result.message
    assert target.read_text(encoding="utf-8") == broken   # কিছুই লেখা হয়নি
    assert backups(tmp_path) == []


def test_non_object_json_aborts(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text("[1, 2, 3]\n", encoding="utf-8")
    assert not cs.install(target).ok


def test_odd_hook_shapes_abort_or_are_left_alone(tmp_path):
    target = tmp_path / "settings.json"
    write(target, {"hooks": "not an object"})
    assert not cs.install(target).ok
    write(target, {"hooks": {"Stop": "not a list"}})
    result = cs.install(target)
    assert not result.ok and "not a list" in result.message


def test_status_reports_before_and_after(tmp_path):
    target = tmp_path / "settings.json"
    write(target, {"effortLevel": "max"})
    before = cs.status(target)
    assert before.ok and before.present == [] and len(before.changed) == 6
    cs.install(target)
    after = cs.status(target)
    assert sorted(after.present) == sorted(e for e, _m in cs.HOOK_EVENTS)
    assert after.changed == []


def test_status_mentions_a_foreign_statusline(tmp_path):
    target = tmp_path / "settings.json"
    write(target, {"statusLine": FOREIGN_STATUSLINE})
    assert "statusLine" in cs.status(target).message


def test_hook_command_shape(tmp_path):
    cmd = cs.hook_command()
    assert cmd.startswith("curl -s -m 1 -X POST --data-binary @-")
    assert "/hook" in cmd
    assert cmd.endswith("|| true")                        # হুক কখনো Claude Code ব্লক করবে না


def test_cli_usage_and_actions(tmp_path, monkeypatch, capsys):
    target = tmp_path / "settings.json"
    monkeypatch.setattr(cs, "settings_path", lambda: target)
    assert cs.main(["claude_settings.py"]) == 2           # ভুল/ফাঁকা সাব-কমান্ড
    assert cs.main(["claude_settings.py", "install"]) == 0
    assert cs.main(["claude_settings.py", "status"]) == 0
    assert cs.main(["claude_settings.py", "remove"]) == 0
    out = capsys.readouterr().out
    assert "installed hooks" in out and "removed our hooks" in out
    assert not target.exists() or "hooks" not in read(target)
