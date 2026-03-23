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

server_path = None
bat_file = None
server_process = None
players = []
players_imgs = {}
ram_history = []

root = tk.Tk()
root.title("ServerWatcher PRO")
root.geometry("1500x920")
root.configure(bg="#080c10")
root.resizable(True, True)

BG0        = "#080c10"
BG1        = "#0d1117"
BG2        = "#111820"
BG3        = "#1a2332"
BORDER     = "#1e3048"
ACCENT     = "#00e5ff"
ACCENT2    = "#00ff88"
ACCENT3    = "#ff6b35"
RED        = "#ff3b5c"
YELLOW     = "#f5c518"
FG         = "#e8f4f8"
FG2        = "#7a9bb5"
FG3        = "#3d5a73"

FONT_MONO   = ("Consolas", 11)
FONT_SMALL  = ("Consolas", 9)
FONT_TITLE  = ("Consolas", 13, "bold")
FONT_HEAD   = ("Consolas", 10, "bold")
FONT_LABEL  = ("Consolas", 9)

def ui(func):
    root.after(0, func)

def log(text):
    def _log():
        console.config(state="normal")
        tag = "info"
        if "[ERROR]" in text or "[WARN]" in text:
            tag = "error"
        elif "[INFO]" in text:
            tag = "info"
        elif text.startswith(">"):
            tag = "cmd"
        console.insert(tk.END, text, tag)
        console.see(tk.END)
        console.config(state="disabled")
    ui(_log)

def make_btn(parent, text, color, command=None, width=None):
    kw = dict(
        text=text,
        bg=color,
        fg=BG0,
        font=FONT_HEAD,
        relief="flat",
        bd=0,
        cursor="hand2",
        activebackground=ACCENT,
        activeforeground=BG0,
        padx=18,
        pady=8,
    )
    if width:
        kw["width"] = width
    if command:
        kw["command"] = command
    btn = tk.Button(parent, **kw)
    def _on(e): btn.config(bg=ACCENT)
    def _off(e): btn.config(bg=color)
    btn.bind("<Enter>", _on)
    btn.bind("<Leave>", _off)
    return btn

topbar = tk.Frame(root, bg=BG1, height=54)
topbar.pack(side="top", fill="x")
topbar.pack_propagate(False)

logo_frame = tk.Frame(topbar, bg=BG1)
logo_frame.pack(side="left", padx=20, pady=0)

dot_canvas = tk.Canvas(logo_frame, width=12, height=12, bg=BG1, highlightthickness=0)
dot_canvas.create_oval(0, 0, 12, 12, fill=ACCENT2, outline="")
dot_canvas.pack(side="left", padx=(0, 8), pady=20)

tk.Label(logo_frame, text="SERVER", bg=BG1, fg=FG,
         font=("Consolas", 14, "bold")).pack(side="left")
tk.Label(logo_frame, text="WATCHER", bg=BG1, fg=ACCENT,
         font=("Consolas", 14, "bold")).pack(side="left")
tk.Label(logo_frame, text=" PRO", bg=BG1, fg=FG2,
         font=("Consolas", 10)).pack(side="left", pady=4)

tk.Frame(topbar, bg=BORDER, width=1).pack(side="left", fill="y", pady=10, padx=20)

btn_frame = tk.Frame(topbar, bg=BG1)
btn_frame.pack(side="left", pady=10)

start_button = make_btn(btn_frame, "▶  START", ACCENT2)
start_button.pack(side="left", padx=(0, 8))

stop_button = make_btn(btn_frame, "■  STOP", RED)
stop_button.pack(side="left", padx=(0, 8))

import_button = make_btn(btn_frame, "⊕  IMPORT", ACCENT)
import_button.pack(side="left")

status_frame = tk.Frame(topbar, bg=BG1)
status_frame.pack(side="right", padx=24)

status_dot = tk.Canvas(status_frame, width=10, height=10, bg=BG1, highlightthickness=0)
status_dot.create_oval(1, 1, 9, 9, fill=FG3, outline="", tags="dot")
status_dot.pack(side="left", padx=(0, 6), pady=22)

status_label = tk.Label(status_frame, text="OFFLINE", bg=BG1, fg=FG3,
                        font=("Consolas", 9, "bold"))
status_label.pack(side="left")

def set_status(online: bool):
    c, t = (ACCENT2, "ONLINE") if online else (FG3, "OFFLINE")
    status_dot.itemconfig("dot", fill=c)
    status_label.config(text=t, fg=c)

glow_bar = tk.Canvas(root, height=2, bg=ACCENT, highlightthickness=0)
glow_bar.pack(side="top", fill="x")

body = tk.Frame(root, bg=BG0)
body.pack(side="top", fill="both", expand=True)

sidebar = tk.Frame(body, bg=BG1, width=230)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

tk.Label(sidebar, text="FILE TREE", bg=BG1, fg=FG3,
         font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(14, 4))

style = ttk.Style()
style.theme_use("clam")
style.configure("Dark.Treeview",
    background=BG2,
    foreground=FG2,
    fieldbackground=BG2,
    borderwidth=0,
    font=("Consolas", 9),
    rowheight=22,
)
style.configure("Dark.Treeview.Heading",
    background=BG3,
    foreground=FG3,
    font=("Consolas", 9, "bold"),
)
style.map("Dark.Treeview",
    background=[("selected", BG3)],
    foreground=[("selected", ACCENT)],
)

tree_frame = tk.Frame(sidebar, bg=BG2, bd=0)
tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

tree_scroll = tk.Scrollbar(tree_frame, bg=BG2, troughcolor=BG2,
                            activebackground=BORDER, width=6, bd=0)
tree_scroll.pack(side="right", fill="y")

tree = ttk.Treeview(tree_frame, style="Dark.Treeview",
                    yscrollcommand=tree_scroll.set, show="tree")
tree.pack(fill="both", expand=True)
tree_scroll.config(command=tree.yview)

content = tk.Frame(body, bg=BG0)
content.pack(side="left", fill="both", expand=True, padx=(1, 0))

style.configure("Dark.TNotebook",
    background=BG0,
    borderwidth=0,
    tabmargins=[0, 0, 0, 0],
)
style.configure("Dark.TNotebook.Tab",
    background=BG1,
    foreground=FG3,
    font=("Consolas", 10),
    padding=[20, 8],
    borderwidth=0,
)
style.map("Dark.TNotebook.Tab",
    background=[("selected", BG0)],
    foreground=[("selected", ACCENT)],
)

notebook = ttk.Notebook(content, style="Dark.TNotebook")
notebook.pack(fill="both", expand=True, padx=0, pady=0)

logs_tab = tk.Frame(notebook, bg=BG0)
notebook.add(logs_tab, text="  LOGS  ")

console_outer = tk.Frame(logs_tab, bg=BORDER, bd=1)
console_outer.pack(fill="both", expand=True, padx=16, pady=(14, 0))

console = tk.Text(
    console_outer,
    bg=BG1,
    fg=FG2,
    insertbackground=ACCENT,
    font=FONT_MONO,
    relief="flat",
    bd=0,
    padx=14,
    pady=10,
    state="disabled",
    selectbackground=BG3,
    selectforeground=FG,
)
console_scroll = tk.Scrollbar(console_outer, bg=BG1, troughcolor=BG1,
                               activebackground=BORDER, width=6, bd=0)
console_scroll.pack(side="right", fill="y")
console.pack(fill="both", expand=True)
console_scroll.config(command=console.yview)
console.config(yscrollcommand=console_scroll.set)

console.tag_config("info",  foreground=ACCENT2)
console.tag_config("error", foreground=RED)
console.tag_config("cmd",   foreground=ACCENT)
console.tag_config("default", foreground=FG2)

cmd_row = tk.Frame(logs_tab, bg=BG0)
cmd_row.pack(fill="x", padx=16, pady=10)

prompt_lbl = tk.Label(cmd_row, text="  ❯  ", bg=BG1, fg=ACCENT,
                       font=("Consolas", 12, "bold"))
prompt_lbl.pack(side="left")

command_entry = tk.Entry(
    cmd_row,
    bg=BG1,
    fg=FG,
    insertbackground=ACCENT,
    font=FONT_MONO,
    relief="flat",
    bd=0,
)
command_entry.pack(side="left", fill="x", expand=True, ipady=8)

send_button = make_btn(cmd_row, "SEND", ACCENT)
send_button.pack(side="left", padx=(8, 0))

diag_tab = tk.Frame(notebook, bg=BG0)
notebook.add(diag_tab, text="  DIAGNOSTICS  ")

ram_card = tk.Frame(diag_tab, bg=BG1)
ram_card.pack(fill="x", padx=16, pady=(16, 0))

ram_header = tk.Frame(ram_card, bg=BG1)
ram_header.pack(fill="x", padx=14, pady=(12, 6))
tk.Label(ram_header, text="RAM USAGE", bg=BG1, fg=FG3,
         font=("Consolas", 8, "bold")).pack(side="left")
ram_pct_label = tk.Label(ram_header, text="0%", bg=BG1, fg=ACCENT,
                          font=("Consolas", 11, "bold"))
ram_pct_label.pack(side="right")
ram_mb_label = tk.Label(ram_header, text="0 MB / 0 MB", bg=BG1, fg=FG3,
                         font=("Consolas", 8))
ram_mb_label.pack(side="right", padx=14)

ram_track = tk.Frame(ram_card, bg=BG3, height=6)
ram_track.pack(fill="x", padx=14, pady=(0, 4))
ram_track.pack_propagate(False)

ram_fill = tk.Frame(ram_track, bg=ACCENT2, height=6)
ram_fill.place(x=0, y=0, height=6, relwidth=0.0)

ram_canvas = tk.Canvas(ram_card, height=70, bg=BG1, highlightthickness=0)
ram_canvas.pack(fill="x", padx=14, pady=(4, 12))

tk.Label(diag_tab, text="ONLINE PLAYERS", bg=BG0, fg=FG3,
         font=("Consolas", 8, "bold")).pack(anchor="w", padx=30, pady=(18, 6))

players_card = tk.Frame(diag_tab, bg=BG1)
players_card.pack(fill="both", expand=True, padx=16, pady=(0, 16))

players_canvas = tk.Canvas(players_card, bg=BG1, highlightthickness=0)
players_canvas.pack(fill="both", expand=True, padx=10, pady=10)

props_tab = tk.Frame(notebook, bg=BG0)
notebook.add(props_tab, text="  PROPERTIES  ")

props_outer = tk.Frame(props_tab, bg=BORDER)
props_outer.pack(fill="both", expand=True, padx=16, pady=14)

props_text = tk.Text(
    props_outer,
    bg=BG1,
    fg=ACCENT2,
    insertbackground=ACCENT,
    font=FONT_MONO,
    relief="flat",
    bd=0,
    padx=14,
    pady=10,
    selectbackground=BG3,
)
props_text.pack(fill="both", expand=True)

statusbar = tk.Frame(root, bg=BG1, height=26)
statusbar.pack(side="bottom", fill="x")
statusbar.pack_propagate(False)

tk.Frame(statusbar, bg=ACCENT, width=3).pack(side="left", fill="y")

path_label = tk.Label(statusbar, text="No server loaded",
                      bg=BG1, fg=FG3, font=("Consolas", 8))
path_label.pack(side="left", padx=10)

tk.Label(statusbar, text="ServerWatcher PRO  v2.0",
         bg=BG1, fg=FG3, font=("Consolas", 8)).pack(side="right", padx=14)

def insert_tree_nodes(parent, path):
    try:
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            node = tree.insert(parent, "end", text=("📁 " if os.path.isdir(full) else "  ") + item)
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
    path_label.config(text=folder)
    props_text.delete("1.0", tk.END)
    prop_file = os.path.join(folder, "server.properties")
    if os.path.exists(prop_file):
        with open(prop_file, "r") as f:
            props_text.insert(tk.END, f.read())
    else:
        props_text.insert(tk.END, "# server.properties not found")

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
            p = psutil.Process(server_process.pid)
            mem = p.memory_info().rss / (1024 * 1024)
            max_ram = psutil.virtual_memory().total / (1024 * 1024)
            percent = min(int(mem / max_ram * 100), 100)

            ram_history.append(percent)
            if len(ram_history) > 120:
                ram_history.pop(0)

            def draw():
                ram_pct_label.config(text=f"{percent}%")
                ram_mb_label.config(text=f"{int(mem)} MB / {int(max_ram)} MB")

                color = ACCENT2 if percent < 50 else YELLOW if percent < 80 else RED
                ram_pct_label.config(fg=color)

                rel = percent / 100
                ram_fill.place(relwidth=rel)
                ram_fill.config(bg=color)

                ram_canvas.delete("all")
                W = ram_canvas.winfo_width() or 460
                H = 70
                pts = ram_history[-W:]
                if len(pts) < 2:
                    return

                step = W / max(len(pts) - 1, 1)

                poly = []
                for i, v in enumerate(pts):
                    x = i * step
                    y = H - (v / 100 * (H - 8)) - 2
                    poly.append((x, y))
                poly_fill = list(poly) + [(W, H), (0, H)]
                flat = [c for pair in poly_fill for c in pair]
                ram_canvas.create_polygon(flat, fill=BG3, outline="")

                for i in range(len(pts) - 1):
                    x1 = i * step
                    y1 = H - (pts[i] / 100 * (H - 8)) - 2
                    x2 = (i + 1) * step
                    y2 = H - (pts[i + 1] / 100 * (H - 8)) - 2
                    ram_canvas.create_line(x1, y1, x2, y2, fill=color, width=1.5, smooth=True)

                lx = (len(pts) - 1) * step
                ly = H - (pts[-1] / 100 * (H - 8)) - 2
                ram_canvas.create_oval(lx - 3, ly - 3, lx + 3, ly + 3,
                                       fill=color, outline=BG1, width=2)

            ui(draw)
        except:
            pass
    root.after(1000, update_ram)

def update_players():
    global players_imgs
    players_canvas.delete("all")
    players_imgs.clear()
    x = 14
    for p in players:
        try:
            r = requests.get(f"https://minotar.net/avatar/{p}/40.png", timeout=3)
            if r.status_code == 200:
                img = ImageTk.PhotoImage(Image.open(BytesIO(r.content)))
                players_imgs[p] = img
                players_canvas.create_oval(x - 2, 8, x + 44, 54, outline=ACCENT, width=1.5)
                players_canvas.create_image(x + 21, 31, image=img)
                players_canvas.create_text(x + 21, 62, text=p,
                                           fill=FG2, font=("Consolas", 8))
                x += 72
        except:
            pass

    if not players:
        players_canvas.create_text(20, 30, text="No players online",
                                   fill=FG3, font=FONT_SMALL, anchor="w")

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
                shell=True
            )
        else:
            jars = [f for f in os.listdir(server_path) if f.endswith(".jar")]
            if not jars:
                log("[ERROR] No .jar file found!\n")
                return
            jar = jars[0]
            server_process = subprocess.Popen(
                ["java", "-jar", jar, "nogui"],
                cwd=server_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True
            )
        threading.Thread(target=read_output, daemon=True).start()
        update_players()
        set_status(True)
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
        "Closing will terminate the server and all related processes.\nContinue?"
    )
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

start_button.config(command=start_server)
stop_button.config(command=stop_server)
import_button.config(command=import_server)
send_button.config(command=send_command)
command_entry.bind("<Return>", send_command)

update_ram()
root.mainloop()
