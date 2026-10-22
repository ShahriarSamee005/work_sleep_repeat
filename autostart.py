import os
import sys
import winreg

KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "WorkSleepRepeat"


def _exe_command():
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return '"%s" --tray' % exe
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return '"%s" "%s" --tray' % (exe, script)


def add(reg_module=winreg):
    cmd = _exe_command()
    key = reg_module.OpenKey(reg_module.HKEY_CURRENT_USER, KEY_PATH, 0,
                             reg_module.KEY_SET_VALUE)
    try:
        reg_module.SetValueEx(key, VALUE_NAME, 0, reg_module.REG_SZ, cmd)
    finally:
        reg_module.CloseKey(key)
    return cmd


def remove(reg_module=winreg):
    try:
        key = reg_module.OpenKey(reg_module.HKEY_CURRENT_USER, KEY_PATH, 0,
                                 reg_module.KEY_SET_VALUE)
    except OSError:
        return False
    try:
        reg_module.DeleteValue(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        reg_module.CloseKey(key)


def is_enabled(reg_module=winreg):
    try:
        key = reg_module.OpenKey(reg_module.HKEY_CURRENT_USER, KEY_PATH, 0,
                                 reg_module.KEY_READ)
    except OSError:
        return False
    try:
        reg_module.QueryValueEx(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        reg_module.CloseKey(key)
