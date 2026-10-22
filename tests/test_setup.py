import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import userconfig
import autostart


# ---- userconfig.save round-trip ----

def test_save_creates_config(tmp_path):
    p = tmp_path / "cfg" / "config.json"
    userconfig.save("rifat", "https://x.supabase.co", "key123", path=p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["me"] == "rifat"
    assert data["supabase_url"] == "https://x.supabase.co"
    assert data["supabase_key"] == "key123"


def test_save_preserves_existing_keys(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"me": "samee", "custom": 42}), encoding="utf-8")
    userconfig.save("rifat", "https://x.supabase.co", "key1", path=p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["me"] == "rifat"
    assert data["custom"] == 42


def test_save_round_trip_with_load(tmp_path):
    p = tmp_path / "config.json"
    userconfig.save("samee", "https://a.supabase.co", "k", alerts={"free": False},
                    hooks_installed=True, autostart=True, path=p)
    cfg = userconfig.load(path=p)
    assert cfg.me == "samee"
    assert cfg.supabase_url == "https://a.supabase.co"
    assert cfg.has_supabase


def test_save_sets_optional_fields(tmp_path):
    p = tmp_path / "config.json"
    userconfig.save("samee", "u", "k", hooks_installed=True, autostart=False, path=p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["hooks_installed"] is True
    assert data["autostart"] is False


def test_save_omits_optional_fields_when_none(tmp_path):
    p = tmp_path / "config.json"
    userconfig.save("samee", "u", "k", path=p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "hooks_installed" not in data
    assert "autostart" not in data


# ---- autostart command building ----

class FakeReg:
    HKEY_CURRENT_USER = "HKCU"
    KEY_SET_VALUE = 2
    KEY_READ = 1
    REG_SZ = 1

    def __init__(self):
        self._store = {}

    def OpenKey(self, root, path, reserved, access):
        return (root, path, access)

    def SetValueEx(self, key, name, reserved, reg_type, value):
        self._store[name] = value

    def DeleteValue(self, key, name):
        if name not in self._store:
            raise FileNotFoundError(name)
        del self._store[name]

    def QueryValueEx(self, key, name):
        if name not in self._store:
            raise FileNotFoundError(name)
        return (self._store[name], 1)

    def CloseKey(self, key):
        pass


def test_autostart_add_remove():
    reg = FakeReg()
    cmd = autostart.add(reg_module=reg)
    assert "--tray" in cmd
    assert autostart.is_enabled(reg_module=reg)
    autostart.remove(reg_module=reg)
    assert not autostart.is_enabled(reg_module=reg)


def test_autostart_remove_when_not_set():
    reg = FakeReg()
    assert autostart.remove(reg_module=reg) is False


def test_autostart_command_contains_main():
    reg = FakeReg()
    cmd = autostart.add(reg_module=reg)
    assert "main.py" in cmd or ".exe" in cmd.lower()
