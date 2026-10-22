import tkinter as tk
from tkinter import messagebox

import config


def _test_connection(url, key):
    import requests
    base = url.rstrip("/") + "/rest/v1/rpc/"
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    }
    resp = requests.post(base + "wsr_get_state", json={}, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()


def run(defaults=None):
    defaults = defaults or {}
    result = {}

    root = tk.Tk()
    root.title("Work•Sleep•Repeat — setup")
    root.configure(bg=config.PANEL_BG)
    root.resizable(False, False)

    pad = {"padx": 12, "pady": 4}
    fg = config.TEXT
    bg = config.PANEL_BG
    entry_bg = config.PANEL_CARD
    font = ("Consolas", 10)

    tk.Label(root, text="Who are you?", fg=fg, bg=bg, font=font, anchor="w").grid(
        row=0, column=0, sticky="w", **pad)

    who_var = tk.StringVar(value=defaults.get("me", "samee"))
    frame_who = tk.Frame(root, bg=bg)
    frame_who.grid(row=0, column=1, sticky="w", **pad)
    for name in ("samee", "rifat"):
        tk.Radiobutton(frame_who, text=name.capitalize(), variable=who_var, value=name,
                       fg=fg, bg=bg, selectcolor=entry_bg, activebackground=bg,
                       activeforeground=fg, font=font).pack(side="left", padx=4)

    tk.Label(root, text="Supabase URL", fg=fg, bg=bg, font=font, anchor="w").grid(
        row=1, column=0, sticky="w", **pad)
    url_var = tk.StringVar(value=defaults.get("supabase_url", ""))
    tk.Entry(root, textvariable=url_var, width=40, bg=entry_bg, fg=fg,
             insertbackground=fg, font=font).grid(row=1, column=1, sticky="w", **pad)

    tk.Label(root, text="Supabase key", fg=fg, bg=bg, font=font, anchor="w").grid(
        row=2, column=0, sticky="w", **pad)
    key_var = tk.StringVar(value=defaults.get("supabase_key", ""))
    tk.Entry(root, textvariable=key_var, width=40, bg=entry_bg, fg=fg,
             insertbackground=fg, font=font, show="•").grid(
        row=2, column=1, sticky="w", **pad)

    hooks_var = tk.BooleanVar(value=defaults.get("hooks", True))
    tk.Checkbutton(root, text="Connect to Claude Code (installs hooks).\n"
                              "A backup of your settings is saved first.",
                   variable=hooks_var, fg=fg, bg=bg, selectcolor=entry_bg,
                   activebackground=bg, activeforeground=fg, font=font,
                   anchor="w", justify="left").grid(
        row=3, column=0, columnspan=2, sticky="w", **pad)

    autostart_var = tk.BooleanVar(value=defaults.get("autostart", True))
    tk.Checkbutton(root, text="Start with Windows", variable=autostart_var,
                   fg=fg, bg=bg, selectcolor=entry_bg,
                   activebackground=bg, activeforeground=fg, font=font,
                   anchor="w").grid(
        row=4, column=0, columnspan=2, sticky="w", **pad)

    status_label = tk.Label(root, text="", fg=config.GOLD, bg=bg, font=font,
                            anchor="w", wraplength=380)
    status_label.grid(row=5, column=0, columnspan=2, sticky="w", **pad)

    def on_test():
        url = url_var.get().strip()
        key = key_var.get().strip()
        if not url or not key:
            status_label.config(text="Enter both URL and key first.", fg=config.WARNING)
            return
        status_label.config(text="Testing...", fg=config.GOLD)
        root.update_idletasks()
        try:
            _test_connection(url, key)
            status_label.config(text="✓ Connected", fg=config.ONLINE_GREEN)
        except Exception as exc:
            msg = str(exc)[:200]
            status_label.config(text=msg, fg=config.WARNING)

    def on_save():
        url = url_var.get().strip()
        key = key_var.get().strip()
        if not url or not key:
            status_label.config(text="Enter both URL and key first.", fg=config.WARNING)
            return
        result["me"] = who_var.get()
        result["supabase_url"] = url
        result["supabase_key"] = key
        result["hooks"] = hooks_var.get()
        result["autostart"] = autostart_var.get()
        root.destroy()

    btn_frame = tk.Frame(root, bg=bg)
    btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
    tk.Button(btn_frame, text="Test connection", command=on_test,
              bg=entry_bg, fg=fg, font=font, activebackground=bg,
              activeforeground=fg).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Save", command=on_save,
              bg=config.ACCENT, fg=config.OUTLINE, font=font,
              activebackground=config.GOLD, activeforeground=config.OUTLINE).pack(
        side="left", padx=8)

    note = tk.Label(root, text="After saving, restart any open Claude Code sessions\n"
                               "so they load the new hooks.",
                    fg=config.TEXT_DIM, bg=bg, font=("Consolas", 9), anchor="w",
                    justify="left")
    note.grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    return result if result else None
