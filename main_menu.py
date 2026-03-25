import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
import re
import requests
import psutil
from PIL import Image, ImageTk
from io import BytesIO
import math
import time
import random

server_path = None
bat_file = None
server_process = None
players = []
players_imgs = {}
ram_history = []
cpu_history = []

root = tk.Tk()
root.title("ServerWatcher PRO")
root.geometry("1560x940")
root.configure(bg="#03070d")
root.resizable(True, True)

BG0    = "#03070d"
BG1    = "#060d16"
BG2    = "#0a1420"
BG3    = "#0f1e2e"
BG4    = "#162840"
BORDER = "#1a3550"
GRID   = "#0d1f30"

CYAN   = "#00f5ff"
GREEN  = "#00ff7f"
ORANGE = "#ff7b00"
RED    = "#ff1f4b"
YELLOW = "#ffe400"
VIOLET = "#9f4fff"
WHITE  = "#e0f0ff"
DIM    = "#2a5070"
DIMMER = "#152535"

FONT_MONO  = ("Consolas", 11)
FONT_SMALL = ("Consolas", 9)
FONT_MED   = ("Consolas", 10, "bold")
FONT_BIG   = ("Consolas", 13, "bold")
FONT_HUGE  = ("Consolas", 16, "bold")
FONT_TINY  = ("Consolas", 8)

def ui(func):
    root.after(0, func)

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def make_btn(parent, text, color, command=None):
    f = tk.Frame(parent, bg=BG1, padx=1, pady=1)
    inner = tk.Frame(f, bg=color)
    inner.pack(fill="both", expand=True)
    lbl = tk.Label(inner, text=text, bg=color, fg=BG0,
                   font=FONT_MED, padx=16, pady=7, cursor="hand2")
    lbl.pack()

    def _enter(e):
        inner.config(bg=CYAN); lbl.config(bg=CYAN, fg=BG0); f.config(bg=CYAN)
    def _leave(e):
        inner.config(bg=color); lbl.config(bg=color, fg=BG0); f.config(bg=BG1)
    def _click(e):
        if command: command()

    for w in (f, inner, lbl):
        w.bind("<Enter>", _enter)
        w.bind("<Leave>", _leave)
        w.bind("<Button-1>", _click)
    return f, lbl

scan_canvas = tk.Canvas(root, bg=BG0, highlightthickness=0)
scan_canvas.place(x=0, y=0, relwidth=1, relheight=1)

scanline_offset = [0]

def animate_scanlines():
    scan_canvas.delete("scanline")
    h = root.winfo_height()
    w = root.winfo_width()
    y = scanline_offset[0] % 4
    while y < h:
        scan_canvas.create_line(0, y, w, y, fill="#ffffff", stipple="gray12", tags="scanline")
        y += 4
    scanline_offset[0] = (scanline_offset[0] + 1) % 4
    root.after(80, animate_scanlines)

topbar = tk.Frame(root, bg=BG1, height=62)
topbar.place(x=0, y=0, relwidth=1, height=62)

topbar_canvas = tk.Canvas(topbar, bg=BG1, highlightthickness=0, height=62)
topbar_canvas.place(x=0, y=0, relwidth=1, height=62)

def draw_topbar_deco():
    topbar_canvas.delete("all")
    w = topbar_canvas.winfo_width() or 1560
    topbar_canvas.create_rectangle(0, 0, w, 62, fill=BG1, outline="")
    for i in range(0, w, 60):
        topbar_canvas.create_line(i, 0, i, 62, fill=GRID, width=1)
    topbar_canvas.create_line(0, 61, w, 61, fill=CYAN, width=1)

topbar.bind("<Configure>", lambda e: draw_topbar_deco())

logo_frame = tk.Frame(topbar, bg=BG1)
logo_frame.place(x=20, y=0, height=62)

logo_canvas = tk.Canvas(logo_frame, width=18, height=18, bg=BG1, highlightthickness=0)
logo_canvas.pack(side="left", padx=(0, 10), pady=22)

pulse_size = [0]
pulse_dir  = [1]

def animate_logo_pulse():
    s = pulse_size[0]
    logo_canvas.delete("all")
    logo_canvas.create_oval(9-s, 9-s, 9+s, 9+s, fill="", outline=GREEN, width=1)
    logo_canvas.create_oval(4, 4, 14, 14, fill=GREEN, outline="")
    pulse_size[0] += pulse_dir[0]
    if pulse_size[0] >= 8 or pulse_size[0] <= 0:
        pulse_dir[0] *= -1
    root.after(60, animate_logo_pulse)

tk.Label(logo_frame, text="SERVER",  bg=BG1, fg=WHITE, font=("Consolas", 16, "bold")).pack(side="left")
tk.Label(logo_frame, text="WATCHER", bg=BG1, fg=CYAN,  font=("Consolas", 16, "bold")).pack(side="left")
tk.Label(logo_frame, text="  ·  PRO", bg=BG1, fg=DIM,  font=("Consolas", 10)).pack(side="left", pady=6)

tk.Frame(topbar, bg=BORDER, width=1).place(x=320, y=10, height=42)

btn_frame = tk.Frame(topbar, bg=BG1)
btn_frame.place(x=340, y=12, height=38)

start_btn_frame, start_btn_lbl = make_btn(btn_frame, "▶  START", GREEN)
start_btn_frame.pack(side="left", padx=(0, 6))

stop_btn_frame, stop_btn_lbl = make_btn(btn_frame, "■  STOP", RED)
stop_btn_frame.pack(side="left", padx=(0, 6))

import_btn_frame, import_btn_lbl = make_btn(btn_frame, "⊕  IMPORT", CYAN)
import_btn_frame.pack(side="left")

status_frame = tk.Frame(topbar, bg=BG1)
status_frame.place(relx=1.0, x=-200, y=0, height=62, width=200)

status_dot_c = tk.Canvas(status_frame, width=14, height=14, bg=BG1, highlightthickness=0)
status_dot_c.pack(side="left", padx=(20, 6), pady=24)
status_dot_c.create_oval(2, 2, 12, 12, fill=DIM,    outline="", tags="dot")
status_dot_c.create_oval(5, 5, 9,  9,  fill=DIMMER, outline="", tags="dotcore")

status_lbl = tk.Label(status_frame, text="OFFLINE", bg=BG1, fg=DIM, font=("Consolas", 9, "bold"))
status_lbl.pack(side="left")

status_ring_size = [0]
status_ring_dir  = [1]
_server_online   = [False]

def animate_status_ring():
    if _server_online[0]:
        s = status_ring_size[0]
        status_dot_c.delete("ring")
        if s > 0:
            status_dot_c.create_oval(7-s, 7-s, 7+s, 7+s,
                                     fill="", outline=GREEN, width=1, tags="ring")
        status_ring_size[0] += status_ring_dir[0]
        if status_ring_size[0] >= 7 or status_ring_size[0] <= 0:
            status_ring_dir[0] *= -1
    root.after(50, animate_status_ring)

def set_status(online: bool):
    _server_online[0] = online
    if online:
        status_dot_c.itemconfig("dot",     fill=GREEN)
        status_dot_c.itemconfig("dotcore", fill=GREEN)
        status_lbl.config(text="ONLINE", fg=GREEN)
    else:
        status_dot_c.delete("ring")
        status_dot_c.itemconfig("dot",     fill=DIM)
        status_dot_c.itemconfig("dotcore", fill=DIMMER)
        status_lbl.config(text="OFFLINE", fg=DIM)

body = tk.Frame(root, bg=BG0)
body.place(x=0, y=62, relwidth=1, relheight=1, height=-88)

sidebar = tk.Frame(body, bg=BG1, width=240)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

sidebar_header = tk.Frame(sidebar, bg=BG1)
sidebar_header.pack(fill="x", padx=12, pady=(12, 6))
tk.Label(sidebar_header, text="FILE TREE", bg=BG1, fg=DIM, font=("Consolas", 8, "bold")).pack(side="left")

tk.Frame(sidebar, bg=CYAN, height=1).pack(fill="x", padx=12, pady=(0, 6))

style = ttk.Style()
style.theme_use("clam")
style.configure("SW.Treeview",
    background=BG2, foreground=DIM, fieldbackground=BG2,
    borderwidth=0, font=("Consolas", 9), rowheight=24)
style.configure("SW.Treeview.Heading",
    background=BG3, foreground=DIM, font=("Consolas", 9, "bold"))
style.map("SW.Treeview",
    background=[("selected", BG4)],
    foreground=[("selected", CYAN)])

tree_wrap = tk.Frame(sidebar, bg=BG2)
tree_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))

tree_scroll = tk.Scrollbar(tree_wrap, bg=BG2, troughcolor=BG2,
                            activebackground=BORDER, width=5, bd=0)
tree_scroll.pack(side="right", fill="y")

tree = ttk.Treeview(tree_wrap, style="SW.Treeview",
                    yscrollcommand=tree_scroll.set, show="tree")
tree.pack(fill="both", expand=True)
tree_scroll.config(command=tree.yview)

tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

content = tk.Frame(body, bg=BG0)
content.pack(side="left", fill="both", expand=True)

style.configure("SW.TNotebook", background=BG0, borderwidth=0, tabmargins=[0, 0, 0, 0])
style.configure("SW.TNotebook.Tab",
    background=BG1, foreground=DIM,
    font=("Consolas", 10), padding=[22, 9], borderwidth=0)
style.map("SW.TNotebook.Tab",
    background=[("selected", BG0)],
    foreground=[("selected", CYAN)])

notebook = ttk.Notebook(content, style="SW.TNotebook")
notebook.pack(fill="both", expand=True)

logs_tab = tk.Frame(notebook, bg=BG0)
notebook.add(logs_tab, text="  LOGS  ")

log_header = tk.Frame(logs_tab, bg=BG0)
log_header.pack(fill="x", padx=16, pady=(12, 0))
tk.Label(log_header, text="◈  CONSOLE OUTPUT", bg=BG0, fg=DIM, font=("Consolas", 8, "bold")).pack(side="left")
log_count_lbl = tk.Label(log_header, text="0 lines", bg=BG0, fg=DIMMER, font=FONT_TINY)
log_count_lbl.pack(side="right")

console_wrap = tk.Frame(logs_tab, bg=BORDER, bd=1)
console_wrap.pack(fill="both", expand=True, padx=16, pady=(6, 0))
console_inner = tk.Frame(console_wrap, bg=BG1)
console_inner.pack(fill="both", expand=True, padx=1, pady=1)

console = tk.Text(
    console_inner, bg=BG1, fg=DIM,
    insertbackground=CYAN, font=FONT_MONO,
    relief="flat", bd=0, padx=14, pady=10,
    state="disabled", selectbackground=BG4,
    selectforeground=WHITE, spacing1=2)
con_scroll = tk.Scrollbar(console_inner, bg=BG1, troughcolor=BG1,
                           activebackground=BORDER, width=5, bd=0)
con_scroll.pack(side="right", fill="y")
console.pack(fill="both", expand=True)
con_scroll.config(command=console.yview)
console.config(yscrollcommand=con_scroll.set)

console.tag_config("timestamp", foreground=DIMMER)
console.tag_config("info",      foreground=GREEN)
console.tag_config("error",     foreground=RED)
console.tag_config("cmd",       foreground=CYAN, font=("Consolas", 11, "bold"))
console.tag_config("default",   foreground=DIM)
console.tag_config("boot",      foreground=VIOLET)

log_line_count = [0]

def log(text):
    def _log():
        console.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        if "[ERROR]" in text or "[WARN]" in text:
            tag = "error"
        elif "[INFO]" in text:
            tag = "info"
        elif text.startswith(">"):
            tag = "cmd"
            ts  = None
        else:
            tag = "default"
        if ts:
            console.insert(tk.END, f"[{ts}]  ", "timestamp")
        console.insert(tk.END, text, tag)
        console.see(tk.END)
        console.config(state="disabled")
        log_line_count[0] += 1
        log_count_lbl.config(text=f"{log_line_count[0]} lines")
    ui(_log)

cmd_row = tk.Frame(logs_tab, bg=BG0)
cmd_row.pack(fill="x", padx=16, pady=10)

prompt_canvas = tk.Canvas(cmd_row, width=32, height=36, bg=BG1, highlightthickness=0)
prompt_canvas.pack(side="left")
prompt_canvas.create_text(16, 18, text="❯", fill=CYAN, font=("Consolas", 14, "bold"))

command_entry = tk.Entry(cmd_row, bg=BG1, fg=WHITE,
                         insertbackground=CYAN, font=FONT_MONO,
                         relief="flat", bd=0)
command_entry.pack(side="left", fill="x", expand=True, ipady=9)

tk.Frame(cmd_row, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)

send_btn_frame, send_btn_lbl = make_btn(cmd_row, "SEND", CYAN)
send_btn_frame.pack(side="left", padx=(6, 0))

diag_tab = tk.Frame(notebook, bg=BG0)
notebook.add(diag_tab, text="  DIAGNOSTICS  ")

def make_diag_card(parent, title, accent_color):
    outer = tk.Frame(parent, bg=accent_color, pady=1, padx=1)
    inner = tk.Frame(outer, bg=BG1)
    inner.pack(fill="both", expand=True)
    header = tk.Frame(inner, bg=BG1)
    header.pack(fill="x", padx=14, pady=(10, 4))
    dot = tk.Canvas(header, width=8, height=8, bg=BG1, highlightthickness=0)
    dot.create_oval(0, 0, 8, 8, fill=accent_color, outline="")
    dot.pack(side="left", padx=(0, 8))
    tk.Label(header, text=title, bg=BG1, fg=accent_color,
             font=("Consolas", 8, "bold")).pack(side="left")
    return outer, inner, header

ram_outer, ram_inner, ram_hdr = make_diag_card(diag_tab, "RAM USAGE", GREEN)
ram_outer.pack(fill="x", padx=16, pady=(16, 0))
ram_pct_lbl = tk.Label(ram_hdr, text="0%", bg=BG1, fg=GREEN, font=("Consolas", 18, "bold"))
ram_pct_lbl.pack(side="right")
ram_mb_lbl = tk.Label(ram_hdr, text="– MB / – MB", bg=BG1, fg=DIM, font=FONT_TINY)
ram_mb_lbl.pack(side="right", padx=12)
ram_track = tk.Frame(ram_inner, bg=BG3, height=8)
ram_track.pack(fill="x", padx=14, pady=(2, 4))
ram_track.pack_propagate(False)
ram_fill = tk.Frame(ram_track, bg=GREEN, height=8)
ram_fill.place(x=0, y=0, height=8, relwidth=0.0)
ram_canvas = tk.Canvas(ram_inner, height=80, bg=BG1, highlightthickness=0)
ram_canvas.pack(fill="x", padx=14, pady=(2, 12))

cpu_outer, cpu_inner, cpu_hdr = make_diag_card(diag_tab, "CPU USAGE", CYAN)
cpu_outer.pack(fill="x", padx=16, pady=(10, 0))
cpu_pct_lbl = tk.Label(cpu_hdr, text="0%", bg=BG1, fg=CYAN, font=("Consolas", 18, "bold"))
cpu_pct_lbl.pack(side="right")
cpu_track = tk.Frame(cpu_inner, bg=BG3, height=8)
cpu_track.pack(fill="x", padx=14, pady=(2, 4))
cpu_track.pack_propagate(False)
cpu_fill = tk.Frame(cpu_track, bg=CYAN, height=8)
cpu_fill.place(x=0, y=0, height=8, relwidth=0.0)
cpu_canvas = tk.Canvas(cpu_inner, height=80, bg=BG1, highlightthickness=0)
cpu_canvas.pack(fill="x", padx=14, pady=(2, 12))

players_outer, players_inner, players_hdr = make_diag_card(diag_tab, "ONLINE PLAYERS", VIOLET)
players_outer.pack(fill="both", expand=True, padx=16, pady=(10, 16))
player_count_lbl = tk.Label(players_hdr, text="0 players", bg=BG1, fg=DIM, font=FONT_TINY)
player_count_lbl.pack(side="right")
players_canvas = tk.Canvas(players_inner, bg=BG1, highlightthickness=0)
players_canvas.pack(fill="both", expand=True, padx=10, pady=10)

props_tab = tk.Frame(notebook, bg=BG0)
notebook.add(props_tab, text="  PROPERTIES  ")

props_hdr_row = tk.Frame(props_tab, bg=BG0)
props_hdr_row.pack(fill="x", padx=16, pady=(12, 6))
tk.Label(props_hdr_row, text="◈  SERVER.PROPERTIES", bg=BG0, fg=DIM,
         font=("Consolas", 8, "bold")).pack(side="left")
props_save_btn_f, props_save_btn_l = make_btn(props_hdr_row, "SAVE TO FILE", CYAN)
props_save_btn_f.pack(side="right")

props_border = tk.Frame(props_tab, bg=BORDER, bd=1)
props_border.pack(fill="both", expand=True, padx=16, pady=(0, 14))
props_bg = tk.Frame(props_border, bg=BG1)
props_bg.pack(fill="both", expand=True, padx=1, pady=1)

props_sc = tk.Canvas(props_bg, bg=BG1, highlightthickness=0)
props_sb = tk.Scrollbar(props_bg, orient="vertical", command=props_sc.yview,
                         bg=BG2, troughcolor=BG1, activebackground=BORDER, width=6, bd=0)
props_sb.pack(side="right", fill="y")
props_sc.pack(side="left", fill="both", expand=True)
props_sc.configure(yscrollcommand=props_sb.set)

pc = tk.Frame(props_sc, bg=BG1)
_pcwin = props_sc.create_window((0, 0), window=pc, anchor="nw")

def _pc_resize(e=None):
    props_sc.configure(scrollregion=props_sc.bbox("all"))
    props_sc.itemconfig(_pcwin, width=props_sc.winfo_width())

pc.bind("<Configure>", _pc_resize)
props_sc.bind("<Configure>", _pc_resize)

def _mwheel(e):
    props_sc.yview_scroll(int(-1 * (e.delta / 120)), "units")

props_sc.bind("<MouseWheel>", _mwheel)
pc.bind("<MouseWheel>", _mwheel)

prop_vars = {}
gm_btns   = {}
diff_btns = {}
gm_var    = tk.StringVar(value="survival")
diff_var  = tk.StringVar(value="easy")
prop_vars["gamemode"]   = gm_var
prop_vars["difficulty"] = diff_var
diff_colors = {"peaceful": GREEN, "easy": CYAN, "normal": YELLOW, "hard": RED}

def _sec(text):
    f = tk.Frame(pc, bg=BG1)
    f.pack(fill="x", padx=16, pady=(20, 6))
    tk.Canvas(f, width=3, height=14, bg=CYAN, highlightthickness=0).pack(side="left", padx=(0, 8))
    tk.Label(f, text=text, bg=BG1, fg=CYAN, font=("Consolas", 8, "bold")).pack(side="left")
    tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=(12, 0))

def _row(label, hint):
    r = tk.Frame(pc, bg=BG2)
    r.pack(fill="x", padx=16, pady=2)
    inner = tk.Frame(r, bg=BG2, padx=14, pady=11)
    inner.pack(fill="x")
    lc = tk.Frame(inner, bg=BG2)
    lc.pack(side="left", fill="x", expand=True)
    tk.Label(lc, text=label, bg=BG2, fg=WHITE,  font=("Consolas", 10, "bold")).pack(anchor="w")
    tk.Label(lc, text=hint,  bg=BG2, fg=DIMMER, font=("Consolas", 8)).pack(anchor="w")
    rc = tk.Frame(inner, bg=BG2)
    rc.pack(side="right")
    r.bind("<MouseWheel>", _mwheel)
    inner.bind("<MouseWheel>", _mwheel)
    lc.bind("<MouseWheel>", _mwheel)
    return rc

toggle_syncers = {}

def _toggle(key, default_on, rc):
    var = tk.BooleanVar(value=default_on)
    prop_vars[key] = var
    tf = tk.Frame(rc, bg=BG2)
    tf.pack()
    ind = tk.Canvas(tf, width=46, height=24, bg=BG2, highlightthickness=0)
    ind.pack(side="left", padx=(0, 8))
    vlbl = tk.Label(tf, text="ON" if default_on else "OFF",
                    fg=GREEN if default_on else DIM,
                    bg=BG2, font=("Consolas", 9, "bold"), width=3, anchor="w")
    vlbl.pack(side="left")

    def _draw(on):
        ind.delete("all")
        ind.create_rectangle(2, 6, 44, 18, fill=BG4 if not on else BG3,
                             outline=GREEN if on else BORDER, width=1)
        kx = 34 if on else 12
        ind.create_oval(kx-7, 5, kx+7, 19, fill=GREEN if on else DIM, outline="")
        vlbl.config(text="ON" if on else "OFF", fg=GREEN if on else DIM)

    def _sync():
        v = var.get()
        _draw(v)
        if key == "white-list":
            if v:
                wl_expander.pack(fill="x", padx=16, pady=(0, 4))
            else:
                wl_expander.pack_forget()

    def _click(_e=None):
        var.set(not var.get())
        _sync()

    toggle_syncers[key] = _sync
    _draw(default_on)
    for w in (ind, vlbl, tf):
        w.bind("<Button-1>", _click)
        w.config(cursor="hand2")
        w.bind("<MouseWheel>", _mwheel)
    return var

def _stepper(key, default_val, rc, lo=0, hi=1000):
    var = tk.StringVar(value=str(default_val))
    prop_vars[key] = var
    sf = tk.Frame(rc, bg=BG2)
    sf.pack()
    def _dec():
        try: var.set(str(max(lo, int(var.get()) - 1)))
        except: pass
    def _inc():
        try: var.set(str(min(hi, int(var.get()) + 1)))
        except: pass
    tk.Button(sf, text="−", bg=BG3, fg=WHITE, font=("Consolas", 11, "bold"),
              relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
              activebackground=RED, activeforeground=WHITE,
              command=_dec).pack(side="left")
    tk.Label(sf, textvariable=var, bg=BG2, fg=CYAN,
             font=("Consolas", 14, "bold"), width=4, anchor="center").pack(side="left")
    tk.Button(sf, text="+", bg=BG3, fg=WHITE, font=("Consolas", 11, "bold"),
              relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
              activebackground=GREEN, activeforeground=BG0,
              command=_inc).pack(side="left")
    sf.bind("<MouseWheel>", _mwheel)

def set_gamemode(mode):
    gm_var.set(mode)
    for m, (bf, bl) in gm_btns.items():
        active = m == mode
        bf.config(bg=CYAN if active else BG3)
        bl.config(bg=CYAN if active else BG3, fg=BG0 if active else DIM)

def set_difficulty(d):
    diff_var.set(d)
    for dd, (bf, bl) in diff_btns.items():
        c = diff_colors[dd]
        active = dd == d
        bf.config(bg=c if active else BG3)
        bl.config(bg=c if active else BG3, fg=BG0 if active else DIM)

_sec("PLAYERS")

rc = _row("Players", "max-players")
_stepper("max-players", 20, rc, lo=1, hi=1000)

rc = _row("Whitelist", "white-list")
_toggle("white-list", False, rc)

wl_expander = tk.Frame(pc, bg=BG3, pady=1, padx=1)
wl_exp_bg = tk.Frame(wl_expander, bg=BG2)
wl_exp_bg.pack(fill="both", expand=True, padx=1, pady=1)
tk.Label(wl_exp_bg, text="WHITELISTED PLAYERS", bg=BG2, fg=VIOLET,
         font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
whitelist_players = []
wl_list_frame = tk.Frame(wl_exp_bg, bg=BG2)
wl_list_frame.pack(fill="x", padx=14, pady=(0, 4))
wl_add_row = tk.Frame(wl_exp_bg, bg=BG2)
wl_add_row.pack(fill="x", padx=14, pady=(0, 10))
wl_entry = tk.Entry(wl_add_row, bg=BG3, fg=WHITE, insertbackground=CYAN,
                    font=FONT_MONO, relief="flat", bd=0)
wl_entry.pack(side="left", fill="x", expand=True, ipady=6)

def wl_add():
    name = wl_entry.get().strip()
    if not name or name in whitelist_players:
        return
    whitelist_players.append(name)
    wl_entry.delete(0, tk.END)
    pr = tk.Frame(wl_list_frame, bg=BG3)
    pr.pack(fill="x", pady=2)
    tk.Label(pr, text=f"  {name}", bg=BG3, fg=CYAN, font=("Consolas", 9)).pack(side="left", padx=4, pady=4)
    def _rm():
        whitelist_players.remove(name)
        pr.destroy()
    tk.Button(pr, text="✕", bg=BG3, fg=RED, font=("Consolas", 8), relief="flat", bd=0,
              padx=6, cursor="hand2", activebackground=BG3, activeforeground=RED,
              command=_rm).pack(side="right", padx=4)

wl_add_bf, wl_add_bl = make_btn(wl_add_row, "ADD", VIOLET)
wl_add_bf.pack(side="left", padx=(6, 0))
wl_add_bf.bind("<Button-1>", lambda e: wl_add())
wl_add_bl.bind("<Button-1>", lambda e: wl_add())
wl_entry.bind("<Return>", lambda e: wl_add())

_sec("GAMEPLAY")

for lbl, key, defval, hint in [
    ("Command Blocks", "enable-command-block", True,  "enable-command-block"),
    ("Monsters",       "spawn-monsters",        True,  "spawn-monsters"),
    ("Force Gamemode", "force-gamemode",         False, "force-gamemode"),
]:
    _toggle(key, defval, _row(lbl, hint))

rc = _row("Gamemode", "gamemode")
gm_bf_row = tk.Frame(rc, bg=BG2)
gm_bf_row.pack()
for mode in ["survival", "creative", "adventure", "spectator", "hardcore"]:
    active = mode == "survival"
    bf = tk.Frame(gm_bf_row, bg=CYAN if active else BG3, pady=1, padx=1)
    bf.pack(side="left", padx=(0, 3))
    bl = tk.Label(bf, text=mode.upper()[:4], bg=CYAN if active else BG3,
                  fg=BG0 if active else DIM, font=("Consolas", 8, "bold"),
                  padx=8, pady=5, cursor="hand2")
    bl.pack()
    gm_btns[mode] = (bf, bl)
    bf.bind("<Button-1>", lambda e, m=mode: set_gamemode(m))
    bl.bind("<Button-1>", lambda e, m=mode: set_gamemode(m))
    bf.bind("<MouseWheel>", _mwheel)
    bl.bind("<MouseWheel>", _mwheel)
gm_bf_row.bind("<MouseWheel>", _mwheel)

rc = _row("Difficulty", "difficulty")
df_bf_row = tk.Frame(rc, bg=BG2)
df_bf_row.pack()
for diff in ["peaceful", "easy", "normal", "hard"]:
    active = diff == "easy"
    c = diff_colors[diff]
    bf = tk.Frame(df_bf_row, bg=c if active else BG3, pady=1, padx=1)
    bf.pack(side="left", padx=(0, 3))
    bl = tk.Label(bf, text=diff.upper()[:4], bg=c if active else BG3,
                  fg=BG0 if active else DIM, font=("Consolas", 8, "bold"),
                  padx=8, pady=5, cursor="hand2")
    bl.pack()
    diff_btns[diff] = (bf, bl)
    bf.bind("<Button-1>", lambda e, d=diff: set_difficulty(d))
    bl.bind("<Button-1>", lambda e, d=diff: set_difficulty(d))
    bf.bind("<MouseWheel>", _mwheel)
    bl.bind("<MouseWheel>", _mwheel)
df_bf_row.bind("<MouseWheel>", _mwheel)

rc = _row("Spawn Protection", "spawn-protection")
_stepper("spawn-protection", 0, rc, lo=0, hi=999)

_sec("WORLD & SERVER")

for lbl, key, defval, hint in [
    ("Cracked (offline mode)", "online-mode",           False, "online-mode=false means cracked"),
    ("Flight",                  "allow-flight",           True,  "allow-flight"),
    ("Villagers",               "spawn-npcs",             True,  "spawn-npcs"),
    ("PVP",                     "pvp",                    True,  "pvp"),
    ("Animals",                 "spawn-animals",          True,  "spawn-animals"),
    ("Nether",                  "allow-nether",           True,  "allow-nether"),
    ("Resource Pack Required",  "require-resource-pack",  False, "require-resource-pack"),
]:
    _toggle(key, defval, _row(lbl, hint))

tk.Frame(pc, bg=BG1, height=24).pack()

def get_props_dict():
    d = {}
    for key, var in prop_vars.items():
        if isinstance(var, tk.BooleanVar):
            v = var.get()
            d[key] = ("false" if v else "true") if key == "online-mode" else ("true" if v else "false")
        else:
            d[key] = var.get()
    return d

def save_props_to_file():
    if not server_path:
        log("[ERROR] No server loaded — cannot save properties.\n")
        return
    prop_file = os.path.join(server_path, "server.properties")
    existing = {}
    if os.path.exists(prop_file):
        with open(prop_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    existing[k.strip()] = v.strip()
    existing.update(get_props_dict())
    with open(prop_file, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    log("[INFO] server.properties saved.\n")

def load_props_from_file(prop_file):
    if not os.path.exists(prop_file):
        return
    mapping = {}
    with open(prop_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                mapping[k.strip()] = v.strip()
    for key, var in prop_vars.items():
        if key not in mapping:
            continue
        val = mapping[key]
        if isinstance(var, tk.BooleanVar):
            var.set((val == "false") if key == "online-mode" else (val == "true"))
        else:
            var.set(val)
    if "gamemode"   in mapping: set_gamemode(mapping["gamemode"])
    if "difficulty" in mapping: set_difficulty(mapping["difficulty"])
    for k, sync_fn in toggle_syncers.items():
        sync_fn()

props_save_btn_f.bind("<Button-1>", lambda e: save_props_to_file())
props_save_btn_l.bind("<Button-1>", lambda e: save_props_to_file())

statusbar = tk.Frame(root, bg=BG1, height=26)
statusbar.place(x=0, relwidth=1, rely=1.0, y=-26, height=26)
tk.Frame(statusbar, bg=CYAN, width=3).pack(side="left", fill="y")
tk.Frame(statusbar, bg=BG0, width=1).pack(side="left", fill="y")
path_lbl = tk.Label(statusbar, text="  No server loaded", bg=BG1, fg=DIM, font=FONT_TINY)
path_lbl.pack(side="left")
uptime_lbl = tk.Label(statusbar, text="", bg=BG1, fg=DIM, font=FONT_TINY)
uptime_lbl.pack(side="right", padx=14)
tk.Label(statusbar, text="ServerWatcher PRO  v3.0", bg=BG1, fg=DIMMER, font=FONT_TINY).pack(side="right", padx=14)

server_start_time = [None]

def update_uptime():
    if server_start_time[0] and _server_online[0]:
        elapsed = int(time.time() - server_start_time[0])
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        uptime_lbl.config(text=f"UPTIME  {h:02d}:{m:02d}:{s:02d}", fg=GREEN)
    else:
        uptime_lbl.config(text="")
    root.after(1000, update_uptime)

BOOT_LINES = [
    "ServerWatcher PRO v3.0 — initializing...",
    "Loading core modules.............. [OK]",
    "Binding process monitor........... [OK]",
    "Starting RAM telemetry............. [OK]",
    "Connecting diagnostic bus.......... [OK]",
    "UI subsystems ready.",
    "─" * 52,
    "Ready. Import a server to begin.",
    "",
]

def play_boot_sequence(lines, idx=0):
    if idx < len(lines):
        def _insert():
            console.config(state="normal")
            console.insert(tk.END, lines[idx] + "\n", "boot")
            console.see(tk.END)
            console.config(state="disabled")
        ui(_insert)
        root.after(120, lambda: play_boot_sequence(lines, idx + 1))

def draw_sparkline(canvas, history, color, h=80):
    canvas.delete("all")
    W = canvas.winfo_width() or 800
    pts = history[-(W // 3):]
    if len(pts) < 2:
        return
    step = W / max(len(pts) - 1, 1)
    poly = []
    for i, v in enumerate(pts):
        x = i * step
        y = h - (v / 100 * (h - 10)) - 2
        poly.append((x, y))
    poly_fill = list(poly) + [(W, h), (0, h)]
    flat = [c for pair in poly_fill for c in pair]
    canvas.create_polygon(flat, fill=lerp_color(BG0, color, 0.08), outline="")
    for i in range(len(pts) - 1):
        frac = i / max(len(pts) - 1, 1)
        lc   = lerp_color(BG4, color, frac)
        x1   = i * step
        y1   = h - (pts[i] / 100 * (h - 10)) - 2
        x2   = (i + 1) * step
        y2   = h - (pts[i + 1] / 100 * (h - 10)) - 2
        canvas.create_line(x1, y1, x2, y2, fill=lc, width=2, smooth=True)
    lx = (len(pts) - 1) * step
    ly = h - (pts[-1] / 100 * (h - 10)) - 2
    canvas.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill=color, outline=BG1, width=2)
    canvas.create_text(lx - 2, ly - 14, text=f"{pts[-1]}%", fill=color,
                       font=("Consolas", 8, "bold"), anchor="center")

def insert_tree_nodes(parent, path):
    try:
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            icon = "▸ " if os.path.isdir(full) else "  "
            node = tree.insert(parent, "end", text=icon + item)
            if os.path.isdir(full):
                insert_tree_nodes(node, full)
    except:
        pass

def import_server():
    global server_path, bat_file
    folder = filedialog.askdirectory()
    if not folder:
        return
    server_path = folder
    tree.delete(*tree.get_children())
    insert_tree_nodes("", folder)
    bats = [f for f in os.listdir(folder) if f.endswith(".bat")]
    bat_file = bats[0] if bats else None
    log(f"[INFO] Imported: {folder}\n")
    path_lbl.config(text=f"  {folder}")
    prop_file = os.path.join(folder, "server.properties")
    load_props_from_file(prop_file)

def read_output():
    global players
    while server_process and server_process.poll() is None:
        line = server_process.stdout.readline()
        if not line:
            continue
        log(line)
        match = re.search(r"Players: (.+)", line)
        if match:
            players = [p for p in match.group(1).split(", ") if p]
    ui(lambda: set_status(False))

def update_ram():
    if server_process:
        try:
            p      = psutil.Process(server_process.pid)
            mem    = p.memory_info().rss / (1024 * 1024)
            total  = psutil.virtual_memory().total / (1024 * 1024)
            pct    = min(int(mem / total * 100), 100)
            ram_history.append(pct)
            if len(ram_history) > 300:
                ram_history.pop(0)
            cpu_pct = psutil.cpu_percent(interval=None)
            cpu_history.append(int(cpu_pct))
            if len(cpu_history) > 300:
                cpu_history.pop(0)

            def draw():
                rc = GREEN if pct < 50 else YELLOW if pct < 80 else RED
                ram_pct_lbl.config(text=f"{pct}%", fg=rc)
                ram_mb_lbl.config(text=f"{int(mem)} MB / {int(total)} MB")
                ram_fill.place(relwidth=pct / 100)
                ram_fill.config(bg=rc)
                draw_sparkline(ram_canvas, ram_history, rc)
                cc = CYAN if cpu_pct < 60 else YELLOW if cpu_pct < 85 else RED
                cpu_pct_lbl.config(text=f"{int(cpu_pct)}%", fg=cc)
                cpu_fill.place(relwidth=cpu_pct / 100)
                cpu_fill.config(bg=cc)
                draw_sparkline(cpu_canvas, cpu_history, cc)
            ui(draw)
        except:
            pass
    root.after(1000, update_ram)

def update_players():
    global players_imgs
    players_canvas.delete("all")
    players_imgs.clear()
    x = 16
    for p in players:
        try:
            r = requests.get(f"https://minotar.net/avatar/{p}/40.png", timeout=3)
            if r.status_code == 200:
                img = ImageTk.PhotoImage(Image.open(BytesIO(r.content)))
                players_imgs[p] = img
                players_canvas.create_oval(x - 3, 7, x + 43, 53, outline=VIOLET, width=2)
                players_canvas.create_oval(x - 6, 4, x + 46, 56, outline=DIMMER, width=1)
                players_canvas.create_image(x + 20, 30, image=img)
                players_canvas.create_text(x + 20, 64, text=p, fill=DIM, font=FONT_TINY)
                x += 76
        except:
            pass
    if not players:
        players_canvas.create_text(16, 30, text="No players currently online",
                                   fill=DIMMER, font=("Consolas", 10), anchor="w")
    else:
        player_count_lbl.config(text=f"{len(players)} online")
    root.after(5000, update_players)

def start_server():
    global server_process
    if not server_path:
        log("[ERROR] No server selected\n")
        return
    try:
        if bat_file:
            server_process = subprocess.Popen(
                [os.path.join(server_path, bat_file)],
                cwd=server_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                shell=True)
        else:
            jars = [f for f in os.listdir(server_path) if f.endswith(".jar")]
            if not jars:
                log("[ERROR] No .jar file found!\n")
                return
            server_process = subprocess.Popen(
                ["java", "-jar", jars[0], "nogui"],
                cwd=server_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True)
        threading.Thread(target=read_output, daemon=True).start()
        update_players()
        set_status(True)
        server_start_time[0] = time.time()
        log("[INFO] Server started\n")
    except Exception as e:
        log(f"[ERROR] {e}\n")

def stop_server():
    global server_process
    if server_process:
        try:
            server_process.stdin.write("stop\n")
            server_process.stdin.flush()
        except:
            server_process.terminate()
        server_process = None
        set_status(False)
        server_start_time[0] = None

def send_command(event=None):
    if server_process:
        cmd = command_entry.get()
        server_process.stdin.write(cmd + "\n")
        server_process.stdin.flush()
        log(f"> {cmd}\n")
        command_entry.delete(0, tk.END)

def on_close():
    global server_process
    confirm = messagebox.askyesno(
        "Exit ServerWatcher PRO",
        "Closing will terminate the server and all related processes.\nContinue?")
    if not confirm:
        return
    if server_process and server_process.poll() is None:
        try:
            server_process.stdin.write("stop\n")
            server_process.stdin.flush()
        except:
            server_process.terminate()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

start_btn_frame.bind("<Button-1>",  lambda e: start_server())
start_btn_lbl.bind("<Button-1>",    lambda e: start_server())
stop_btn_frame.bind("<Button-1>",   lambda e: stop_server())
stop_btn_lbl.bind("<Button-1>",     lambda e: stop_server())
import_btn_frame.bind("<Button-1>", lambda e: import_server())
import_btn_lbl.bind("<Button-1>",   lambda e: import_server())
send_btn_frame.bind("<Button-1>",   lambda e: send_command())
send_btn_lbl.bind("<Button-1>",     lambda e: send_command())
command_entry.bind("<Return>", send_command)

root.after(200, lambda: [
    draw_topbar_deco(),
    animate_logo_pulse(),
    animate_status_ring(),
    animate_scanlines(),
    update_ram(),
    update_uptime(),
    play_boot_sequence(BOOT_LINES),
])

root.mainloop()
