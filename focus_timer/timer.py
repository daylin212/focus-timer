#!/usr/bin/env python3
"""Focus Timer — a terminal Pomodoro timer with session tracking."""

import sys
import time
import signal
import json
import os
from datetime import datetime, date

# ── Config ────────────────────────────────────────────────────────────────────
WORK_MINUTES   = 25
SHORT_BREAK    = 5
LONG_BREAK     = 15
SESSIONS_UNTIL_LONG = 4

DATA_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")
BAR_WIDTH  = 40

# ── ANSI colors ───────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"
CLEAR  = "\033[2J\033[H"

# ── Session data ──────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"sessions": [], "total_focus_minutes": 0}

def save_session(label, minutes):
    data = load_data()
    data["sessions"].append({
        "date": datetime.now().isoformat(),
        "label": label,
        "minutes": minutes,
    })
    data["total_focus_minutes"] = data.get("total_focus_minutes", 0) + minutes
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def today_stats():
    data = load_data()
    today = date.today().isoformat()
    today_sessions = [s for s in data["sessions"] if s["date"].startswith(today) and s["label"] == "work"]
    mins = sum(s["minutes"] for s in today_sessions)
    return len(today_sessions), mins, data.get("total_focus_minutes", 0)

# ── Display ───────────────────────────────────────────────────────────────────
def progress_bar(elapsed, total, color):
    filled = int(BAR_WIDTH * elapsed / total)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    pct = int(100 * elapsed / total)
    return f"{color}[{bar}]{RESET} {pct:3d}%"

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def render(phase, elapsed, total, session_count, color, label):
    remaining = total - elapsed
    bar = progress_bar(elapsed, total, color)
    sys.stdout.write(CLEAR)
    print(f"\n  {BOLD}🍅 Focus Timer{RESET}\n")
    print(f"  {color}{BOLD}{label}{RESET}")
    print(f"  {bar}")
    print(f"  {BOLD}{format_time(remaining)}{RESET} remaining  {DIM}({format_time(elapsed)} elapsed){RESET}")
    today, today_mins, total_mins = today_stats()
    print(f"\n  {DIM}Today: {today} sessions · {today_mins} min  |  All-time: {total_mins} min{RESET}")
    print(f"  {DIM}Session #{session_count}  ·  Press Ctrl+C to skip{RESET}\n")
    sys.stdout.flush()

def bell():
    sys.stdout.write("\a")
    sys.stdout.flush()

# ── Timer loop ────────────────────────────────────────────────────────────────
def run_phase(label, minutes, session_count, color):
    total = minutes * 60
    start = time.time()
    skipped = False
    try:
        while True:
            elapsed = time.time() - start
            if elapsed >= total:
                break
            render(phase=label, elapsed=elapsed, total=total,
                   session_count=session_count, color=color, label=label)
            time.sleep(0.5)
    except KeyboardInterrupt:
        skipped = True

    render(phase=label, elapsed=total, total=total,
           session_count=session_count, color=color, label=label)
    bell()
    return not skipped

def confirm(prompt):
    try:
        sys.stdout.write(CLEAR)
        ans = input(f"\n  {BOLD}{prompt}{RESET} [Enter / q to quit] ").strip().lower()
        return ans != "q"
    except (KeyboardInterrupt, EOFError):
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    sys.stdout.write(CLEAR)
    print(f"\n  {BOLD}{CYAN}🍅 Focus Timer{RESET}")
    print(f"  {DIM}{WORK_MINUTES}m work · {SHORT_BREAK}m short break · {LONG_BREAK}m long break every {SESSIONS_UNTIL_LONG} sessions{RESET}\n")
    print(f"  Press {BOLD}Enter{RESET} to start, {BOLD}Ctrl+C{RESET} during a phase to skip it.\n")
    try:
        input("  > ")
    except (KeyboardInterrupt, EOFError):
        return

    completed_work = 0

    while True:
        # ── Work phase ──
        session_num = completed_work + 1
        finished = run_phase(
            label=f"Work Session #{session_num}",
            minutes=WORK_MINUTES,
            session_count=session_num,
            color=GREEN,
        )
        if finished:
            save_session("work", WORK_MINUTES)
            completed_work += 1
        else:
            save_session("work-partial", int((time.time()) % 60))  # rough

        # ── Decide break length ──
        if completed_work > 0 and completed_work % SESSIONS_UNTIL_LONG == 0:
            break_label = f"Long Break ({LONG_BREAK}m)"
            break_mins  = LONG_BREAK
            break_color = YELLOW
        else:
            break_label = f"Short Break ({SHORT_BREAK}m)"
            break_mins  = SHORT_BREAK
            break_color = CYAN

        if not confirm(f"Session done! Time for a {break_label}."):
            break

        run_phase(label=break_label, minutes=break_mins,
                  session_count=completed_work, color=break_color)

        if not confirm("Break over. Start another work session?"):
            break

    sys.stdout.write(CLEAR)
    today, today_mins, total_mins = today_stats()
    print(f"\n  {BOLD}Session complete!{RESET}")
    print(f"  Today: {BOLD}{today}{RESET} sessions · {BOLD}{today_mins}{RESET} minutes focused")
    print(f"  All-time: {BOLD}{total_mins}{RESET} minutes\n")

if __name__ == "__main__":
    main()
