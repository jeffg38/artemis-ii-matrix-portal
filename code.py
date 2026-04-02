# code.py  —  Artemis II Mission Display  v8
# Adafruit Matrix Portal M4  +  64x32 RGB LED Matrix
#
# STATE MACHINE:
#   PRE_LAUNCH   → "ARTEMIS II" + "COUNTDOWN" + live T-minus clock
#   IN_FLIGHT    → "ARTEMIS II" + "** LIVE **" + scrolling AROW telemetry
#   POST_MISSION → "ARTEMIS II" + "SPLASHDOWN!" + scrolling crew message
#
# WiFi credentials → /CIRCUITPY/settings.toml:
#   CIRCUITPY_WIFI_SSID = "your_ssid"
#   CIRCUITPY_WIFI_PASSWORD = "your_password"
#
# AROW telemetry fetched in two small chunks to stay within M4 RAM limits:
#   Chunk 1 (bytes 0-2047):    position 2003/2004/2005, velocity 2009/2010/2011
#   Chunk 2 (bytes 15000-17000): timestamps 5010/5011/5012

import time
import board
import terminalio
import math
import gc
from adafruit_matrixportal.matrixportal import MatrixPortal

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

AROW_URL = "https://storage.googleapis.com/storage/v1/b/p-2-cen1/o/October%2F1%2FOctober_105_1.txt?alt=media"

# Launch: April 1 2026 22:24:00 UTC
LAUNCH_EPOCH     = 1775060640
SPLASHDOWN_EPOCH = LAUNCH_EPOCH + (10 * 24 * 3600)

FETCH_INTERVAL = 120   # seconds between AROW polls
SCROLL_DELAY   = 0.03  # seconds per pixel

COL_ORANGE = 0xFF6600
COL_WHITE  = 0xFFFFFF
COL_CYAN   = 0x00FFFF
COL_YELLOW = 0xFFFF00
COL_RED    = 0xFF2200
COL_GREEN  = 0x00FF44

# ── DISPLAY SETUP ─────────────────────────────────────────────────────────────

matrixportal = MatrixPortal(
    status_neopixel=board.NEOPIXEL,
    bit_depth=2,
    debug=False,
)

# Slot 0 — top row: "ARTEMIS II" (static)
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 4),
    text_color=COL_ORANGE,
    scrolling=False,
)
matrixportal.set_text("ARTEMIS II", 0)

# Slot 1 — middle row: phase label
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 14),
    text_color=COL_CYAN,
    scrolling=False,
)
matrixportal.set_text("LOADING...", 1)

# Slot 2 — bottom row: scrolling telemetry or countdown
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(0, 25),
    text_color=COL_WHITE,
    scrolling=True,
)
matrixportal.set_text("PLEASE WAIT", 2)

# ── TIME HELPERS ──────────────────────────────────────────────────────────────

def now_epoch():
    return time.time()

def sync_time():
    try:
        matrixportal.get_local_time()
        print("Time synced:", time.localtime())
    except Exception as e:
        print("Time sync failed:", e)

def format_countdown(secs):
    if secs <= 0:
        return "LIFTOFF!"
    d = int(secs // 86400)
    h = int((secs % 86400) // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    if d > 0:
        return f"T-{d}D {h:02}:{m:02}:{s:02}"
    return f"T-{h:02}:{m:02}:{s:02}"

# ── AROW DATA ─────────────────────────────────────────────────────────────────

def extract(t, key):
    """Find key in raw JSON text and return its Value string."""
    idx = t.find('"' + key + '"')
    if idx < 0:
        return None
    idx = t.find('"Value"', idx)
    if idx < 0:
        return None
    idx = t.find(':', idx) + 1
    while t[idx] in ' "':
        idx += 1
    end = idx
    while end < len(t) and t[end] not in '",\n}':
        end += 1
    return t[idx:end].strip()

def fetch_and_format():
    """
    Fetch AROW telemetry in two small chunks to stay within M4 RAM limits.
    Chunk 1 (top of file): position 2003/2004/2005 and velocity 2009/2010/2011
    Chunk 2 (end of file): timestamps 5010/5011/5012 for MET
    Altitude is computed from the position vector (ft) — Parameter_5001 is
    no longer present in the telemetry after the early mission phase.
    """
    try:
        gc.collect()
        gc.collect()

        # ── Chunk 1: position + velocity (first 2KB) ──
        response = matrixportal.network.fetch(
            AROW_URL,
            headers={"Range": "bytes=0-2047"}
        )
        if response.status_code not in (200, 206):
            response.close()
            print("AROW HTTP status:", response.status_code)
            return None
        chunk1 = response.text
        response.close()
        gc.collect()

        px = extract(chunk1, "Parameter_2003")
        py = extract(chunk1, "Parameter_2004")
        pz = extract(chunk1, "Parameter_2005")
        vx = extract(chunk1, "Parameter_2009")
        vy = extract(chunk1, "Parameter_2010")
        vz = extract(chunk1, "Parameter_2011")
        del chunk1
        gc.collect()
        gc.collect()

        # ── Chunk 2: timestamps (end of file) ──
        response = matrixportal.network.fetch(
            AROW_URL,
            headers={"Range": "bytes=15000-17000"}
        )
        if response.status_code not in (200, 206):
            response.close()
            print("AROW HTTP status:", response.status_code)
            return None
        chunk2 = response.text
        response.close()
        gc.collect()

        ts = (extract(chunk2, "Parameter_5010") or
              extract(chunk2, "Parameter_5011") or
              extract(chunk2, "Parameter_5012") or
              extract(chunk2, "Parameter_5000"))
        del chunk2
        gc.collect()

        # ── Format results ──

        # Altitude from position vector (ft -> km -> miles)
        if px and py and pz:
            dist_km = math.sqrt(
                float(px)**2 + float(py)**2 + float(pz)**2
            ) * 0.0003048
            alt_miles = int((dist_km - 6371) * 0.621371)
            alt_str = f"{alt_miles:,}" if alt_miles > 0 else "---"
        else:
            alt_str = "---"

        # Speed from velocity vector (ft/s -> mph)
        if vx and vy and vz:
            speed = int(
                math.sqrt(float(vx)**2 + float(vy)**2 + float(vz)**2) * 0.681818
            )
            speed_str = f"{speed:,}"
        else:
            speed_str = "---"

        # MET from timestamp
        if ts:
            met = int(float(ts) - 1775082240)
            if 0 < met < 864000:
                met_str = f"T+{met//3600}h{(met%3600)//60:02}m"
            else:
                met_str = "---"
        else:
            met_str = "---"

        print(f"ALT:{alt_str} SPD:{speed_str} {met_str}")
        return f"  ALT:{alt_str}mi SPD:{speed_str}mph {met_str}   "

    except Exception as e:
        print("Fetch error:", e)
        return None

# ── STATE DETERMINATION ───────────────────────────────────────────────────────

def get_state():
    t = now_epoch()
    if t < LAUNCH_EPOCH:
        return "PRE_LAUNCH"
    if t < SPLASHDOWN_EPOCH:
        return "IN_FLIGHT"
    return "POST_MISSION"

# ── PRE-LAUNCH MODE ───────────────────────────────────────────────────────────

def run_pre_launch():
    matrixportal.set_text("COUNTDOWN", 1)
    matrixportal.set_text_color(COL_CYAN, 1)
    matrixportal.set_text_color(COL_WHITE, 2)
    print("State: PRE_LAUNCH")
    last_second = 0
    while get_state() == "PRE_LAUNCH":
        remaining = LAUNCH_EPOCH - now_epoch()
        current_second = int(remaining)
        if current_second != last_second:
            matrixportal.set_text(format_countdown(remaining), 2)
            last_second = current_second
        time.sleep(0.1)

# ── IN-FLIGHT MODE ────────────────────────────────────────────────────────────

def run_in_flight():
    matrixportal.set_text("** LIVE **", 1)
    matrixportal.set_text_color(COL_GREEN, 1)
    matrixportal.set_text_color(COL_WHITE, 2)
    print("State: IN_FLIGHT")

    last_update = time.monotonic() - FETCH_INTERVAL  # fetch immediately on entry
    scroll_text = "  CONNECTING TO AROW...   "
    gc.collect()
    matrixportal.set_text(scroll_text, 2)

    while get_state() == "IN_FLIGHT":
        matrixportal.scroll_text(SCROLL_DELAY)

        if time.monotonic() > last_update + FETCH_INTERVAL:
            print("Retrieving data...")
            result = fetch_and_format()
            if result:
                scroll_text = result
                matrixportal.set_text_color(COL_WHITE, 2)
            else:
                scroll_text = "  AWAITING AROW DATA...   "
                matrixportal.set_text_color(COL_YELLOW, 2)
            gc.collect()
            matrixportal.set_text(scroll_text, 2)
            last_update = time.monotonic()

# ── POST-MISSION MODE ─────────────────────────────────────────────────────────

def run_post_mission():
    matrixportal.set_text("SPLASHDOWN!", 1)
    matrixportal.set_text_color(COL_CYAN, 1)
    gc.collect()
    matrixportal.set_text(
        "  CREW SAFE! WELCOME HOME WISEMAN GLOVER KOCH HANSEN   ", 2
    )
    matrixportal.set_text_color(COL_GREEN, 2)
    print("State: POST_MISSION")
    while True:
        matrixportal.scroll_text(SCROLL_DELAY)

# ── BOOT ──────────────────────────────────────────────────────────────────────

sync_time()

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

while True:
    state = get_state()
    print("Entering state:", state)
    try:
        if state == "PRE_LAUNCH":
            run_pre_launch()
        elif state == "IN_FLIGHT":
            run_in_flight()
        else:
            run_post_mission()
    except Exception as e:
        print("Error:", e)
        matrixportal.set_text("ERROR", 1)
        matrixportal.set_text_color(COL_RED, 1)
        gc.collect()
        matrixportal.set_text("  " + str(e)[:30] + "   ", 2)
        matrixportal.scroll_text(SCROLL_DELAY)
        time.sleep(5)
