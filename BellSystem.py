# ==============================
#   PROFESSIONAL BELL SYSTEM
#   FINAL STABLE PRODUCTION v3
# ==============================

import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import hid
import time
import threading
from datetime import datetime, timedelta
import json
import os
import sys
import html.parser

# ---------------- SETTINGS ----------------
VENDOR_ID  = 0x16c0
PRODUCT_ID = 0x05df

DEFAULT_DURATION  = 3
LONG_DURATION     = 5        # overridden at runtime by long_seconds_var
ADMIN_PASSWORD    = "789"
WARNING_SECONDS  = 30
MAX_LOGO_SIZE    = 72

# ---------------- STATE ----------------
scheduler_running = False
manual_active     = False
schedule          = []
time_entries      = []
current_user_role = None   # None="guest" | "user" | "admin"

# ---------------- PATH SETUP ----------------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCHEDULES_FILE = os.path.join(BASE_DIR, "schedules.json")
LOG_FILE       = os.path.join(BASE_DIR, "bell_log.txt")
LOGO_FILE      = os.path.join(BASE_DIR, "logo.png")
INSTITUTE_FILE = os.path.join(BASE_DIR, "institute.html")
USER_PASS_FILE = os.path.join(BASE_DIR, "user_password.txt")

# ============================================================
#   PASSWORD HELPERS
# ============================================================

def _get_user_password():
    if os.path.exists(USER_PASS_FILE):
        with open(USER_PASS_FILE, "r") as f:
            return f.read().strip()
    return "1234"

def _save_user_password(new_pass):
    with open(USER_PASS_FILE, "w") as f:
        f.write(new_pass.strip())

def is_admin_password(p):
    return p == ADMIN_PASSWORD

def is_user_password(p):
    return p == _get_user_password()

def is_logged_in():
    """True if session is admin or user (not guest)."""
    return current_user_role in ("admin", "user")

# ============================================================
#   SESSION-AWARE PERMISSION CHECKS
#   Logged-in users/admins are NEVER re-prompted for routine
#   actions. Only truly admin-only actions (clear log, 7-day
#   clean) ask for the admin password when the session is
#   "user" level.
# ============================================================

def require_session(action_label="this action"):
    """Returns True immediately if already logged in. Blocks guests."""
    if is_logged_in():
        return True
    messagebox.showwarning(
        "Login Required",
        f"You must be logged in to use: {action_label}.\n\n"
        "Click 'Login Now' on the lock panel to sign in."
    )
    return False

def require_admin_session():
    """
    Admin session  → allowed immediately, no re-prompt.
    User session   → asks for admin password once.
    Guest          → blocked.
    """
    if current_user_role == "admin":
        return True
    if current_user_role == "user":
        pw = simpledialog.askstring(
            "Admin Required",
            "This action requires the Admin password:", show='*')
        return is_admin_password(pw)
    messagebox.showwarning("Login Required", "Please log in first.")
    return False

# ============================================================
#   CHANGE USER PASSWORD
# ============================================================

def change_user_password():
    if not is_logged_in():
        messagebox.showwarning("Login Required",
                               "Please log in to change the password.")
        return

    if current_user_role == "admin":
        # Admin resets without knowing old password
        new1 = simpledialog.askstring("Reset User Password",
                                      "Enter NEW user password:", show='*')
        if not new1:
            return
        new2 = simpledialog.askstring("Reset User Password",
                                      "Confirm NEW password:", show='*')
        if new1 != new2:
            messagebox.showerror("Mismatch", "Passwords do not match!")
            return
        _save_user_password(new1)
        messagebox.showinfo("Done", "User password reset by Admin.")
    else:
        # User must verify current password first
        old = simpledialog.askstring("Change Password",
                                     "Enter your CURRENT password:", show='*')
        if old is None:
            return
        if not is_user_password(old):
            messagebox.showerror("Access Denied", "Incorrect current password!")
            return
        new1 = simpledialog.askstring("Change Password",
                                      "Enter NEW password:", show='*')
        if not new1:
            return
        new2 = simpledialog.askstring("Change Password",
                                      "Confirm NEW password:", show='*')
        if new1 != new2:
            messagebox.showerror("Mismatch", "Passwords do not match!")
            return
        _save_user_password(new1)
        messagebox.showinfo("Done", "Password changed successfully.")

# ============================================================
#   STARTUP LOGIN DIALOG
# ============================================================

def show_login_dialog():
    dialog = tk.Toplevel()
    dialog.title("Bell System Login")
    dialog.geometry("360x230")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    role_result = [None]

    tk.Label(dialog, text="🔔  Professional Bell System",
             font=("Arial", 14, "bold")).pack(pady=(18, 4))
    tk.Label(dialog,
             text="Enter password for full access\n"
                  "or continue as Guest (manual bell only)",
             font=("Arial", 9), fg="#555").pack()

    pw_var   = tk.StringVar()
    pw_entry = tk.Entry(dialog, textvariable=pw_var, show='*',
                        width=22, font=("Arial", 11))
    pw_entry.pack(pady=10)
    pw_entry.focus()

    msg_label = tk.Label(dialog, text="", fg="red", font=("Arial", 9))
    msg_label.pack()

    def attempt_login(event=None):
        p = pw_var.get()
        if is_admin_password(p):
            role_result[0] = "admin"
            dialog.destroy()
        elif is_user_password(p):
            role_result[0] = "user"
            dialog.destroy()
        else:
            msg_label.config(text="⚠  Incorrect password – please try again.")
            pw_var.set("")

    def guest_mode():
        role_result[0] = None
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=6)
    tk.Button(btn_frame, text="Login", width=12,
              bg="#2e86de", fg="white", font=("Arial", 10, "bold"),
              command=attempt_login).grid(row=0, column=0, padx=8)
    tk.Button(btn_frame, text="Continue as Guest", width=16,
              font=("Arial", 10),
              command=guest_mode).grid(row=0, column=1, padx=8)

    pw_entry.bind("<Return>", attempt_login)
    dialog.wait_window()
    return role_result[0]

# ============================================================
#   RELAY CONTROL
# ============================================================

def relay_on():
    try:
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        device.send_feature_report([0x00, 0xFF, 0x01, 0x01])
        device.close()
    except:
        messagebox.showerror("Relay Error", "Relay not connected")

def relay_off():
    try:
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        device.send_feature_report([0x00, 0xFD, 0x01, 0x00])
        device.close()
    except:
        pass

def ring_bell(duration):
    relay_on()
    time.sleep(duration)
    relay_off()
    log_activity(duration)

# ============================================================
#   LOG SYSTEM
# ============================================================

def log_activity(duration):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{now}|{duration}\n")

def view_log():
    if not os.path.exists(LOG_FILE):
        messagebox.showinfo("Log", "No log file found.")
        return
    window = tk.Toplevel(root)
    window.title("Bell Activity Log")
    window.geometry("600x400")
    text = tk.Text(window)
    text.pack(expand=True, fill="both")
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    for line in lines:
        try:
            dt, dur = line.strip().split("|")
            text.insert("end", f"{dt} - Bell Rang ({dur} sec)\n")
        except:
            continue
    text.config(state="disabled")

def clear_log():
    if not require_admin_session():
        return
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
        messagebox.showinfo("Done", "Log cleared.")

def auto_clean_7_days():
    if not require_admin_session():
        return
    if not os.path.exists(LOG_FILE):
        return
    cutoff    = datetime.now() - timedelta(days=7)
    new_lines = []
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    for line in lines:
        try:
            dt_str, _ = line.strip().split("|")
            log_time  = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            if log_time >= cutoff:
                new_lines.append(line)
        except:
            continue
    with open(LOG_FILE, "w") as f:
        f.writelines(new_lines)
    messagebox.showinfo("Done", "Old logs removed.")

# ============================================================
#   HTML HEADER PARSER
# ============================================================

class _HtmlTextParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.segments  = []
        self._curr_tag = "p"

    def handle_starttag(self, tag, attrs):
        self._curr_tag = tag
        if tag == "br":
            self.segments.append(("\n", "br"))

    def handle_endtag(self, tag):
        if tag in ("h1","h2","h3","h4","h5","h6","p"):
            self.segments.append(("\n", "br"))

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.segments.append((text, self._curr_tag))

def _tag_to_font(tag):
    return {
        "h1": ("Arial", 20, "bold"),
        "h2": ("Arial", 17, "bold"),
        "h3": ("Arial", 15, "bold"),
        "h4": ("Arial", 13, "bold"),
        "h5": ("Arial", 12, "bold"),
        "h6": ("Arial", 11, "bold"),
        "b":  ("Arial", 13, "bold"),
        "strong": ("Arial", 13, "bold"),
    }.get(tag, ("Arial", 12))

def load_institute():
    for widget in header_frame.winfo_children():
        widget.destroy()
    if os.path.exists(LOGO_FILE):
        try:
            img  = Image.open(LOGO_FILE)
            img.thumbnail((MAX_LOGO_SIZE, MAX_LOGO_SIZE))
            logo = ImageTk.PhotoImage(img)
            lbl  = tk.Label(header_frame, image=logo)
            lbl.image = logo
            lbl.pack(pady=5)
        except:
            pass
    if os.path.exists(INSTITUTE_FILE):
        with open(INSTITUTE_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        parser = _HtmlTextParser()
        parser.feed(raw)
        for text, tag in parser.segments:
            if tag == "br" or text == "\n":
                continue
            tk.Label(header_frame, text=text, font=_tag_to_font(tag)).pack()

# ============================================================
#   MULTI-SCHEDULE MANAGER
# ============================================================

def _load_all_schedules():
    if not os.path.exists(SCHEDULES_FILE):
        return {}
    with open(SCHEDULES_FILE, "r") as f:
        return json.load(f)

def _save_all_schedules(data):
    with open(SCHEDULES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _current_entries_as_list():
    return [{"time": e.get(), "long": lv.get()} for e, lv in time_entries]

def _clear_time_rows():
    while time_entries:
        row = len(time_entries)
        entry, _ = time_entries.pop()
        entry.destroy()
        for w in scrollable_frame.grid_slaves(row=row):
            w.destroy()

def _populate_time_rows(items):
    _clear_time_rows()
    for item in items:
        add_time_row()
        time_entries[-1][0].insert(0, item["time"])
        time_entries[-1][1].set(item["long"])

def open_schedule_manager():
    if not require_session("Schedule Manager"):
        return

    win = tk.Toplevel(root)
    win.title("Schedule Manager")
    win.geometry("420x380")
    win.grab_set()

    tk.Label(win, text="📋  Saved Schedules",
             font=("Arial", 13, "bold")).pack(pady=8)

    lf = tk.Frame(win)
    lf.pack(fill="both", expand=True, padx=20)
    sb = tk.Scrollbar(lf)
    sb.pack(side="right", fill="y")
    listbox = tk.Listbox(lf, yscrollcommand=sb.set, height=10, font=("Arial", 10))
    listbox.pack(side="left", fill="both", expand=True)
    sb.config(command=listbox.yview)

    def refresh_list():
        listbox.delete(0, "end")
        for name in _load_all_schedules():
            listbox.insert("end", name)

    refresh_list()

    name_var = tk.StringVar()
    tk.Label(win, text="Schedule name:").pack()
    name_entry = tk.Entry(win, textvariable=name_var, width=28)
    name_entry.pack(pady=4)

    def on_select(evt=None):
        sel = listbox.curselection()
        if sel:
            name_var.set(listbox.get(sel[0]))

    listbox.bind("<<ListboxSelect>>", on_select)

    def do_save():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Name required", "Please enter a schedule name.")
            return
        all_s = _load_all_schedules()
        all_s[name] = _current_entries_as_list()
        _save_all_schedules(all_s)
        refresh_list()
        messagebox.showinfo("Saved", f'Schedule "{name}" saved.')

    def do_load():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Select", "Select or type a schedule name.")
            return
        all_s = _load_all_schedules()
        if name not in all_s:
            messagebox.showerror("Not found", f'"{name}" not found.')
            return
        _populate_time_rows(all_s[name])
        win.destroy()
        messagebox.showinfo("Loaded", f'Schedule "{name}" loaded.')

    def do_delete():
        name = name_var.get().strip()
        if not name:
            return
        all_s = _load_all_schedules()
        if name in all_s:
            if messagebox.askyesno("Delete", f'Delete schedule "{name}"?'):
                del all_s[name]
                _save_all_schedules(all_s)
                refresh_list()
                name_var.set("")

    bf = tk.Frame(win)
    bf.pack(pady=8)
    tk.Button(bf, text="💾 Save",   width=12, command=do_save).grid(row=0, column=0, padx=4)
    tk.Button(bf, text="📂 Load",   width=12, command=do_load).grid(row=0, column=1, padx=4)
    tk.Button(bf, text="🗑 Delete", width=12, command=do_delete).grid(row=0, column=2, padx=4)

# ============================================================
#   TIME ROW MANAGEMENT
# ============================================================

def add_time_row():
    # Session check — no password re-prompt if logged in
    if not require_session("Add Time"):
        return
    row = len(time_entries) + 1
    tk.Label(scrollable_frame, text=str(row), width=5).grid(row=row, column=0)
    time_entry = tk.Entry(scrollable_frame, width=10)
    time_entry.grid(row=row, column=1)
    long_var = tk.BooleanVar()
    tk.Checkbutton(scrollable_frame, variable=long_var).grid(row=row, column=2)
    time_entries.append((time_entry, long_var))

def remove_time_row():
    # Session check — no password re-prompt if logged in
    if not require_session("Remove Time"):
        return
    if not time_entries:
        return
    row = len(time_entries)
    entry, _ = time_entries.pop()
    entry.destroy()
    for w in scrollable_frame.grid_slaves(row=row):
        w.destroy()

# ============================================================
#   MANUAL OVERRIDE  (always available to everyone)
# ============================================================

def toggle_manual():
    global manual_active
    if not manual_active:
        relay_on()
        manual_button.config(text="⏹  STOP Manual Bell",
                             bg="#e74c3c", fg="white")
        manual_active = True
    else:
        relay_off()
        manual_button.config(text="🔔  Manual Override Bell",
                             bg="#27ae60", fg="white")
        manual_active = False

# ============================================================
#   SCHEDULER
# ============================================================

def toggle_scheduler():
    global scheduler_running, schedule
    if not require_session("Scheduler"):
        return
    if not scheduler_running:
        # Read user-defined long duration; fallback to default if blank/invalid
        try:
            user_long = int(long_seconds_var.get().strip())
            if user_long < 1 or user_long > 9:
                raise ValueError
        except ValueError:
            user_long = LONG_DURATION

        schedule.clear()
        for entry, long_var in time_entries:
            duration = user_long if long_var.get() else DEFAULT_DURATION
            schedule.append((entry.get(), duration))
        scheduler_running = True
        scheduler_button.config(text="⏹  Stop Scheduler",
                                bg="#e74c3c", fg="white")
        status_label.config(text="System Running", fg="green")
        threading.Thread(target=run_scheduler, daemon=True).start()
    else:
        scheduler_running = False
        scheduler_button.config(text="▶  Start Scheduler",
                                bg="#27ae60", fg="white")
        status_label.config(text="System Stopped", fg="red")
        countdown_label.config(text="")

def run_scheduler():
    now_start       = datetime.now()
    triggered_today = set()

    # Skip all bell times already in the past
    for time_value, _ in schedule:
        try:
            bt = datetime.strptime(time_value, "%H:%M").replace(
                year=now_start.year, month=now_start.month, day=now_start.day)
            if bt <= now_start:
                triggered_today.add(time_value)
        except:
            continue

    while scheduler_running:
        now = datetime.now()
        for time_value, duration in schedule:
            try:
                bell_time = datetime.strptime(time_value, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day)
            except:
                continue

            warning_time = bell_time - timedelta(seconds=WARNING_SECONDS)

            if warning_time <= now < bell_time:
                secs  = int((bell_time - now).total_seconds())
                color = "red" if secs % 2 == 0 else "black"
                countdown_label.config(
                    text=f"Next Bell in: {secs} sec", fg=color)

            if now >= bell_time and time_value not in triggered_today:
                countdown_label.config(text="")
                ring_bell(duration)
                triggered_today.add(time_value)

        time.sleep(1)

# ============================================================
#   NEXT BELL LABEL
# ============================================================

def update_next_bell():
    now = datetime.now()
    upcoming = []
    for entry, _ in time_entries:
        try:
            t = datetime.strptime(entry.get(), "%H:%M").replace(
                year=now.year, month=now.month, day=now.day)
            if t >= now:
                upcoming.append(t)
        except:
            continue
    if upcoming:
        next_bell_label.config(text=f"Next Bell: {min(upcoming).strftime('%H:%M')}")
    else:
        next_bell_label.config(text="Next Bell: --")
    root.after(60000, update_next_bell)

# ============================================================
#   GUEST OVERLAY  — professional lock panel over restricted area
# ============================================================

_overlay_frame = None

def build_guest_overlay():
    """Places a grey frosted-look overlay with padlock over locked_area_frame."""
    global _overlay_frame

    _overlay_frame = tk.Frame(locked_area_frame, bg="#d0d0d0", bd=2, relief="groove")
    _overlay_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    tk.Label(_overlay_frame, text="🔒",
             font=("Arial", 40), bg="#d0d0d0", fg="#555").pack(pady=(25, 4))

    tk.Label(_overlay_frame, text="Restricted Area",
             font=("Arial", 14, "bold"), bg="#d0d0d0", fg="#333").pack()

    tk.Label(_overlay_frame,
             text="Login to access schedule management,\n"
                  "scheduler, add/remove timings and logs.",
             font=("Arial", 9), bg="#d0d0d0", fg="#555",
             justify="center").pack(pady=6)

    tk.Button(_overlay_frame, text="🔑  Login Now",
              font=("Arial", 11, "bold"),
              bg="#2e86de", fg="white", width=14,
              command=do_runtime_login).pack(pady=10)

def do_runtime_login():
    """Lets a guest log in at runtime without restarting the app."""
    global current_user_role, _overlay_frame

    pw = simpledialog.askstring("Login", "Enter password:", show='*')
    if pw is None:
        return
    if is_admin_password(pw):
        current_user_role = "admin"
    elif is_user_password(pw):
        current_user_role = "user"
    else:
        messagebox.showerror("Access Denied", "Incorrect password!")
        return

    # Remove the overlay — full UI now visible
    if _overlay_frame:
        _overlay_frame.destroy()
        _overlay_frame = None

    # Update role badge in top bar
    role_label.config(
        text=f"Logged in as: {'Admin' if current_user_role == 'admin' else 'User'}",
        fg="green"
    )
    status_label.config(text="System Stopped", fg="red")
    messagebox.showinfo(
        "Welcome",
        f"Logged in as {'Admin' if current_user_role == 'admin' else 'User'}.\n"
        "Full access granted."
    )

# ============================================================
#   MAIN GUI
# ============================================================

root = tk.Tk()
root.withdraw()                          # hide while login dialog runs

current_user_role = show_login_dialog()
root.deiconify()

root.title("Professional Bell System")
root.geometry("700x820")
root.resizable(False, False)

# ── Top bar: role indicator ───────────────────────────────────
top_bar = tk.Frame(root, bg="#eaeaea", bd=1, relief="sunken")
top_bar.pack(fill="x")

role_text  = (f"Logged in as: {'Admin' if current_user_role == 'admin' else 'User'}"
              if current_user_role else "Guest Mode")
role_color = "green" if current_user_role else "darkorange"
role_label = tk.Label(top_bar, text=role_text,
                      font=("Arial", 9, "bold"),
                      fg=role_color, bg="#eaeaea")
role_label.pack(side="right", padx=12, pady=4)

# ── Institute header ──────────────────────────────────────────
header_frame = tk.Frame(root)
header_frame.pack(pady=8)
load_institute()

# ── Next bell display ─────────────────────────────────────────
next_bell_label = tk.Label(root, text="Next Bell: --",
                            font=("Arial", 14, "bold"), fg="purple")
next_bell_label.pack()

# ── Manual override — ALWAYS visible and active ───────────────
manual_button = tk.Button(
    root,
    text="🔔  Manual Override Bell",
    font=("Arial", 11, "bold"),
    bg="#27ae60", fg="white", width=24,
    command=toggle_manual
)
manual_button.pack(pady=8)

# ── LOCKED AREA — everything below needs login ────────────────
locked_area_frame = tk.Frame(root, bd=2, relief="groove")
locked_area_frame.pack(fill="both", expand=True, padx=10, pady=6)

# ── Split: LEFT (schedule list) | RIGHT (settings + logs) ────
split_frame = tk.Frame(locked_area_frame)
split_frame.pack(fill="both", expand=True, padx=4, pady=4)

# ════════════════════════════════
#   LEFT PANEL — schedule list
# ════════════════════════════════
left_panel = tk.Frame(split_frame, bd=1, relief="sunken")
left_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

# Compact column headers
hdr = tk.Frame(left_panel, bg="#dce3ec")
hdr.pack(fill="x")
tk.Label(hdr, text="No.", width=4,  font=("Arial", 9, "bold"),
         bg="#dce3ec", anchor="center").grid(row=0, column=0, padx=2, pady=3)
tk.Label(hdr, text="Time (HH:MM)", width=12, font=("Arial", 9, "bold"),
         bg="#dce3ec", anchor="center").grid(row=0, column=1, padx=2, pady=3)
tk.Label(hdr, text="Long", width=5, font=("Arial", 9, "bold"),
         bg="#dce3ec", anchor="center").grid(row=0, column=2, padx=2, pady=3)

# Scrollable rows
list_frame = tk.Frame(left_panel)
list_frame.pack(fill="both", expand=True)

canvas    = tk.Canvas(list_frame, height=180, highlightthickness=0)
scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

time_entries = []

# ════════════════════════════════
#   RIGHT PANEL — settings + logs
# ════════════════════════════════
right_panel = tk.Frame(split_frame, bd=1, relief="sunken", width=180)
right_panel.pack(side="right", fill="y", padx=(6, 0))
right_panel.pack_propagate(False)   # hold fixed width

# Long Bell Seconds box
tk.Label(right_panel, text="Long Bell (sec)",
         font=("Arial", 9, "bold")).pack(pady=(12, 2))

long_seconds_var = tk.StringVar(value=str(LONG_DURATION))

def _validate_single_digit(P):
    """Allow only a single digit 1–9."""
    return P == "" or (len(P) == 1 and P.isdigit() and P != "0")

vcmd = (root.register(_validate_single_digit), "%P")

long_seconds_entry = tk.Entry(
    right_panel,
    textvariable=long_seconds_var,
    width=4,
    font=("Arial", 14, "bold"),
    justify="center",
    validate="key",
    validatecommand=vcmd
)
long_seconds_entry.pack(pady=2)

tk.Label(right_panel, text="(1 – 9 seconds)",
         font=("Arial", 8), fg="#888").pack()

# Separator
tk.Frame(right_panel, height=1, bg="#bbb").pack(fill="x", padx=10, pady=10)

# Stacked log buttons
tk.Button(right_panel, text="📄  View Log",
          width=16, anchor="w", padx=6,
          command=view_log).pack(fill="x", padx=8, pady=3)

tk.Button(right_panel, text="🗑  Clear Log",
          width=16, anchor="w", padx=6,
          command=clear_log).pack(fill="x", padx=8, pady=3)

tk.Button(right_panel, text="🧹  Remove > 7 Days",
          width=16, anchor="w", padx=6,
          command=auto_clean_7_days).pack(fill="x", padx=8, pady=3)

# Separator
tk.Frame(right_panel, height=1, bg="#bbb").pack(fill="x", padx=10, pady=10)

# Password change in right panel
tk.Button(right_panel, text="🔑  Change Password",
          width=16, anchor="w", padx=6,
          command=change_user_password).pack(fill="x", padx=8, pady=3)

# ── Row: Add Time | Manage Schedules | Remove Last ───────────
row1_frame = tk.Frame(locked_area_frame)
row1_frame.pack(pady=5)

add_btn = tk.Button(row1_frame, text="+ Add Time",
                    width=15, command=add_time_row)
add_btn.grid(row=0, column=0, padx=8)

schedule_mgr_btn = tk.Button(row1_frame, text="📋 Manage Schedules",
                              width=18, command=open_schedule_manager)
schedule_mgr_btn.grid(row=0, column=1, padx=8)

remove_btn = tk.Button(row1_frame, text="− Remove Last",
                       width=15, command=remove_time_row)
remove_btn.grid(row=0, column=2, padx=8)

# ── Scheduler button ─────────────────────────────────────────
scheduler_button = tk.Button(locked_area_frame, text="▶  Start Scheduler",
                              font=("Arial", 11, "bold"),
                              bg="#27ae60", fg="white", width=22,
                              command=toggle_scheduler)
scheduler_button.pack(pady=5)

# ── Status & countdown ───────────────────────────────────────
status_label = tk.Label(
    locked_area_frame,
    text="System Stopped" if current_user_role else "Guest Mode – Manual Only",
    fg="red" if current_user_role else "darkorange",
    font=("Arial", 12, "bold")
)
status_label.pack()

countdown_label = tk.Label(locked_area_frame, text="",
                           font=("Arial", 14, "bold"))
countdown_label.pack(pady=(0, 4))

# ── Footer ────────────────────────────────────────────────────
tk.Label(root, text="Powered by SaSiE",
         font=("Arial", 10), fg="gray").pack(side="bottom", pady=8)

# ── Apply guest overlay after all widgets are placed ──────────
if current_user_role is None:
    root.update_idletasks()       # ensure frame has geometry before overlay
    build_guest_overlay()

# ── Load first saved schedule on startup ─────────────────────
if os.path.exists(SCHEDULES_FILE):
    all_s = _load_all_schedules()
    if all_s:
        _populate_time_rows(all_s[next(iter(all_s))])

update_next_bell()
root.mainloop()
