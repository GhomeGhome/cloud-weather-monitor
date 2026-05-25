# ============================================================
# main.py - M5Stack Core2 Weather Monitor v1.5.0
# UIFlow 1.x / MicroPython
# Hardware: ENV III + SGP30 on PORTA (I2C splitter)
# Buttons : A = record / stop mic   B = next WiFi + connect   C = cycle pages
# ============================================================

from m5stack import *
from m5stack_ui import *
from uiflow import *
from machine import I2C, Pin, RTC, I2S
import gc
import ubinascii
import time
import utime
import unit
import urequests
import ujson
import network

try:
    import ntptime
    _HAS_NTP = True
except:
    _HAS_NTP = False

# ============================================================
# CONFIG - edit WIFI_NETWORKS before flashing
# ============================================================
DEVICE_ID    = "core2-main"
FIRMWARE_VER = "1.5.0"
API_BASE     = "https://weather-ingestion-api-972242315876.europe-west6.run.app"

# VIDEO DEMO — credentials inlined for flashing via UIFlow (do not commit)
# TODO: revert to config.py pattern after demo
INGEST_SECRET = "iuvxiquoxbpq28e382fd92owexb9823gdp2icduweobx"
WIFI_NETWORKS = [
    ("iPhone de Guillaume (2)", "d2kcrrd4rx9x"),
    ("iot-unil", "4u6uch4hpY9pJ2f9"),
]

UTC_OFFSET_H = 2  # Switzerland CEST; change to 1 for CET winter

INGEST_INTERVAL_SEC  = 60
WEATHER_INTERVAL_SEC = 300

# Voice QA (on-device recording)
MIC_RATE     = 18000           # Hz — avoids 18 540 default pitch shift
MIC_MAX_SECS = 15              # max recording length (8 MB PSRAM, 540 KB)
MIC_CHUNK    = MIC_RATE * 2 // 4  # ~0.25 s per chunk ≈ 9 000 bytes

# ============================================================
# COLORS  -  autumn palette
# ============================================================
C_BG     = 0x1A0800   # deep mahogany         (background)
C_WHITE  = 0xE8C09A   # warm parchment        (primary text / time)
C_GREEN  = 0x90C060   # sage green            (good / normal values)
C_RED    = 0xFF4422   # autumn flame          (alerts / bad)
C_ORANGE = 0xD06828   # burnt orange          (warnings)
C_YELLOW = 0xF0A028   # golden maple          (outdoor / forecast)
C_CYAN   = 0xC85828   # terracotta            (section headers / title)
C_GRAY   = 0xB08060   # warm mocha            (secondary / date)
C_LBLUE  = 0xD09050   # amber copper          (page titles)

# ============================================================
# DISPLAY MODES
# ============================================================
MODE_NORMAL   = 0
MODE_FORECAST = 1
MODE_WIFI     = 2
MODE_ANSWER   = 3

mode     = MODE_NORMAL
wifi_idx = 0

# ============================================================
# INIT SCREEN
# 320 x 240 px  — autumn layout
# y=2       title header (FONT_14, left)
# y=20      time HH:MM:SS  centered  (FONT_14)
# y=32      date YYYY/MM/DD centered  (FONT_14)
# y=52      section label (changes per page)
# y=68-116  4 content rows  key (x=5) / value (x=95)
# y=132     alert banner   (FONT_10)
# y=142     soft separator (FONT_10)
# y=152     outdoor header / answer overflow slot 5
# y=166     outdoor temp+desc / answer overflow slot 6
# y=180     outdoor humidity / answer overflow slot 7
# y=190     button divider (FONT_10)
# y=200     button labels A / B / C
# y=220     status bar     (FONT_10)
# ============================================================
screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(C_BG)

# --- Header ---
lbl_title = M5Label('Cozy Weather', x=5, y=2, color=C_CYAN, font=FONT_MONT_14, parent=None)

# --- Time & date — centered focal point ---
lbl_time  = M5Label('--:--:--',   x=115, y=20, color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_date  = M5Label('----/--/--', x=105, y=32, color=C_GRAY,  font=FONT_MONT_14, parent=None)

# --- Section header ---
lbl_section = M5Label('~ inside ~', x=5, y=52, color=C_LBLUE, font=FONT_MONT_14, parent=None)

# --- 4 content rows (reused across all pages) ---
lbl_r0_k = M5Label('warmth',   x=5,  y=68,  color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_r0_v = M5Label('--.-C',    x=95, y=68,  color=C_GREEN, font=FONT_MONT_14, parent=None)
lbl_r1_k = M5Label('moisture', x=5,  y=84,  color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_r1_v = M5Label('--.-%',    x=95, y=84,  color=C_GREEN, font=FONT_MONT_14, parent=None)
lbl_r2_k = M5Label('air vibe', x=5,  y=100, color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_r2_v = M5Label('--- ppb',  x=95, y=100, color=C_GREEN, font=FONT_MONT_14, parent=None)
lbl_r3_k = M5Label('breath',   x=5,  y=116, color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_r3_v = M5Label('---- ppm', x=95, y=116, color=C_GREEN, font=FONT_MONT_14, parent=None)

# --- Alert banner ---
lbl_alert = M5Label('', x=5, y=132, color=C_RED, font=FONT_MONT_10, parent=None)

# --- Outdoor section (home page) / answer overflow lines 5-8 ---
lbl_sep      = M5Label('. ' * 20,    x=0,   y=142, color=C_GRAY,   font=FONT_MONT_10, parent=None)
lbl_out_hdr  = M5Label('~ outside ~',x=5,   y=152, color=C_LBLUE,  font=FONT_MONT_14, parent=None)
lbl_out_temp = M5Label('--.-C',      x=5,   y=166, color=C_YELLOW, font=FONT_MONT_14, parent=None)
lbl_out_desc = M5Label('---',        x=100, y=166, color=C_YELLOW, font=FONT_MONT_14, parent=None)
lbl_out_hum  = M5Label('hum: --%',   x=5,   y=180, color=C_YELLOW, font=FONT_MONT_10, parent=None)

# --- Button label divider ---
lbl_btn_sep = M5Label('- ' * 21, x=0, y=190, color=C_GRAY, font=FONT_MONT_10, parent=None)

# --- 3 button labels (centered above A / B / C touch buttons) ---
# Core2 button centers: A~x=53  B~x=160  C~x=267
lbl_btn_a = M5Label('refresh', x=10,  y=200, color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_btn_b = M5Label('wifi',    x=133, y=200, color=C_WHITE, font=FONT_MONT_14, parent=None)
lbl_btn_c = M5Label('next >',  x=236, y=200, color=C_WHITE, font=FONT_MONT_14, parent=None)

# --- Status bar ---
lbl_status = M5Label('starting up...', x=5, y=220, color=C_GRAY, font=FONT_MONT_10, parent=None)

# ============================================================
# INIT SENSORS
# Direct I2C at low frequency (100 kHz) to avoid bus errors with splitter.
# PORTA on Core2 : SDA=GPIO32, SCL=GPIO33
# ============================================================
time.sleep(1)  # let all sensors power up before touching the bus

_I2C_PORTA = I2C(1, scl=Pin(33), sda=Pin(32), freq=100000)

# --- SHT30 (temp + humidity inside ENV III) - address 0x44 ---
_SHT30_ADDR = 0x44

def _read_sht30():
    """Returns (temperature_c, humidity_pct) or (None, None)."""
    try:
        _I2C_PORTA.writeto(_SHT30_ADDR, b'\x2C\x06')  # single-shot, high repeatability
        time.sleep_ms(50)
        data = _I2C_PORTA.readfrom(_SHT30_ADDR, 6)
        t_raw = (data[0] << 8) | data[1]
        h_raw = (data[3] << 8) | data[4]
        return round(-45.0 + 175.0 * t_raw / 65535.0, 1), round(100.0 * h_raw / 65535.0, 1)
    except Exception as e:
        print("[SHT30] error:", e)
        return None, None

# --- SGP30 (TVOC + eCO2) - address 0x58 ---
_SGP30_ADDR = 0x58

def _init_sgp30():
    try:
        _I2C_PORTA.writeto(_SGP30_ADDR, b'\x20\x03')  # init_air_quality
        time.sleep_ms(10)
        print("[SGP30] init ok")
        return True
    except Exception as e:
        print("[SGP30] init error:", e)
        return False

def _read_sgp30():
    """Returns (tvoc_ppb, eco2_ppm) or (None, None)."""
    try:
        _I2C_PORTA.writeto(_SGP30_ADDR, b'\x20\x08')  # measure_air_quality
        time.sleep_ms(12)
        data = _I2C_PORTA.readfrom(_SGP30_ADDR, 6)
        eco2 = (data[0] << 8) | data[1]
        tvoc = (data[3] << 8) | data[4]
        return tvoc, eco2
    except Exception as e:
        print("[SGP30] read error:", e)
        return None, None

# Scan bus and init
_found = _I2C_PORTA.scan()
print("[I2C] devices found:", [hex(a) for a in _found])

_sgp30_ok = _SGP30_ADDR in _found and _init_sgp30()
_sht30_ok = _SHT30_ADDR in _found
print("[SENSOR] SHT30:", "ok" if _sht30_ok else "NOT FOUND")
print("[SENSOR] SGP30:", "ok" if _sgp30_ok else "NOT FOUND")

# ============================================================
# UTILITIES
# ============================================================
def set_status(msg, color=C_GRAY):
    lbl_status.set_text(str(msg)[:42])
    lbl_status.set_text_color(color)

def set_btn_labels(a, b, c):
    lbl_btn_a.set_text(a)
    lbl_btn_b.set_text(b)
    lbl_btn_c.set_text(c)

def safe_float(val, decimals=1):
    try:
        return round(float(val), decimals)
    except:
        return None

def color_for_temp(t):
    if t is None: return C_GRAY
    if t < 18:    return C_LBLUE
    if t < 26:    return C_GREEN
    return C_RED

def color_for_hum(h):
    if h is None: return C_GRAY
    if h < 30:    return C_RED
    if h < 40:    return C_ORANGE
    if h <= 70:   return C_GREEN
    return C_LBLUE

def color_for_tvoc(v):
    if v is None: return C_GRAY
    if v < 220:   return C_GREEN
    if v < 660:   return C_YELLOW
    return C_RED

def color_for_co2(v):
    if v is None: return C_GRAY
    if v < 1000:  return C_GREEN
    if v < 2000:  return C_YELLOW
    return C_RED

# ============================================================
# NTP + TIME
# ============================================================
_time_offset = 0

def _iso_to_epoch(ts):
    """ISO UTC string -> seconds since MicroPython epoch (2000-01-01)."""
    y  = int(ts[0:4]); mo = int(ts[5:7]); d  = int(ts[8:10])
    h  = int(ts[11:13]); mi = int(ts[14:16]); s  = int(ts[17:19])
    days = 0
    for yr in range(2000, y):
        days += 366 if yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0) else 365
    dm = [31, 29 if y%4==0 and (y%100!=0 or y%400==0) else 28,
          31,30,31,30,31,31,30,31,30,31]
    for m in range(1, mo):
        days += dm[m-1]
    days += d - 1
    return days * 86400 + h * 3600 + mi * 60 + s

def sync_ntp():
    """Sync time: NTP first, then verify utime.time() is valid, then /live API fallback.

    Problem: ntptime.settime() may set the RTC but utime.time() on UIFlow1 doesn't
    always reflect it immediately, leaving the clock at 2000-01-01.
    Fix: always check the result and fall through to the API offset method if needed.
    """
    global _time_offset
    if _HAS_NTP:
        try:
            ntptime.settime()
            print("[NTP] settime() called")
        except Exception as e:
            print("[NTP] failed:", e)
    # Check if utime.time() is now valid (year >= 2024)
    if utime.localtime(utime.time())[0] >= 2024:
        _time_offset = 0
        print("[TIME] clock ok via NTP, year:", utime.localtime(utime.time())[0])
        return
    # utime.time() still wrong — compute offset from API /live timestamp
    try:
        r = urequests.get(API_BASE + "/live")
        ts = ujson.loads(r.text).get("ts", "")
        r.close()
        if len(ts) >= 19:
            _time_offset = _iso_to_epoch(ts) - utime.time()
            print("[TIME] offset from API:", _time_offset)
    except Exception as e:
        print("[TIME] all sync failed:", e)

def _real_utc():
    return utime.time() + _time_offset

def _local_time():
    return utime.localtime(_real_utc() + UTC_OFFSET_H * 3600)

def get_time_str():
    t = _local_time()
    return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])

def get_date_str():
    t = _local_time()
    return "{:04d}/{:02d}/{:02d}".format(t[0], t[1], t[2])

# ============================================================
# SENSORS
# ============================================================
def read_sensors():
    r = {
        "temperature_c": None, "humidity_pct": None,
        "pressure_hpa": None,  "tvoc_ppb": None,
        "eco2_ppm": None,      "motion": False,
    }
    if _sht30_ok:
        t, h = _read_sht30()
        r["temperature_c"] = t
        r["humidity_pct"]  = h
    if _sgp30_ok:
        tvoc, eco2 = _read_sgp30()
        r["tvoc_ppb"] = tvoc
        r["eco2_ppm"] = eco2
    return r

# ============================================================
# DISPLAY - INDOOR MODE
# ============================================================
def show_indoor_mode(r):
    t    = r["temperature_c"]
    h    = r["humidity_pct"]
    tvoc = r["tvoc_ppb"]
    co2  = r["eco2_ppm"]

    lbl_section.set_text("~ inside ~")
    lbl_section.set_text_color(C_LBLUE)

    lbl_r0_k.set_text("warmth")
    lbl_r0_v.set_text("{:.1f} C".format(t) if t is not None else "-- C")
    lbl_r0_v.set_text_color(color_for_temp(t))

    lbl_r1_k.set_text("moisture")
    lbl_r1_v.set_text("{:.0f} %".format(h) if h is not None else "-- %")
    lbl_r1_v.set_text_color(color_for_hum(h))

    lbl_r2_k.set_text("air vibe")
    lbl_r2_v.set_text("{} ppb".format(tvoc) if tvoc is not None else "--- ppb")
    lbl_r2_v.set_text_color(color_for_tvoc(tvoc))

    lbl_r3_k.set_text("breath")
    lbl_r3_v.set_text("{} ppm".format(co2) if co2 is not None else "---- ppm")
    lbl_r3_v.set_text_color(color_for_co2(co2))

    # Alert banner: highest-priority alert only
    alerts = []
    if h is not None and h < 40:
        alerts.append("  air is dry  ({:.0f}%)".format(h))
    if tvoc is not None and tvoc >= 660:
        alerts.append("  air feels stuffy  (TVOC hi)")
    if co2 is not None and co2 >= 2000:
        alerts.append("  open a window! ({} ppm)".format(co2))
    lbl_alert.set_text(alerts[0][:42] if alerts else "")
    lbl_alert.set_text_color(C_RED)

    # Show outdoor section
    lbl_sep.set_text('. ' * 20)
    lbl_out_hdr.set_text('~ outside ~')
    set_btn_labels("micro", "wifi", "next >")

# ============================================================
# DISPLAY - FORECAST MODE
# ============================================================
def show_forecast_mode(forecast_data):
    lbl_section.set_text("~ coming up ~")
    lbl_section.set_text_color(C_CYAN)
    lbl_alert.set_text("")
    lbl_sep.set_text("")
    lbl_out_hdr.set_text("")
    lbl_out_temp.set_text("")
    lbl_out_desc.set_text("")
    lbl_out_hum.set_text("")

    row_keys = [lbl_r0_k, lbl_r1_k, lbl_r2_k, lbl_r3_k]
    row_vals = [lbl_r0_v, lbl_r1_v, lbl_r2_v, lbl_r3_v]

    days = []
    if isinstance(forecast_data, dict):
        fc = forecast_data.get("forecast", {})
        if isinstance(fc, dict):
            days = fc.get("daily", [])
        elif isinstance(fc, list):
            days = fc

    _months = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

    for i in range(4):
        if i < len(days):
            d    = days[i]
            date = str(d.get("date", ""))
            tmin = d.get("temp_min_c")
            tmax = d.get("temp_max_c")
            desc = str(d.get("weather_main") or d.get("weather_description") or "")[:10]
            try:
                m_idx = int(date[5:7]) - 1
                date_short = "{} {}".format(int(date[8:10]), _months[m_idx])
            except:
                date_short = date[:6]
            row_keys[i].set_text(date_short)
            row_keys[i].set_text_color(C_WHITE)
            if tmin is not None and tmax is not None:
                temp_str = "{:.0f}/{:.0f}C {}".format(tmin, tmax, desc)
            else:
                temp_str = "--/--C {}".format(desc)
            row_vals[i].set_text(temp_str[:22])
            row_vals[i].set_text_color(C_YELLOW)
        else:
            row_keys[i].set_text("--")
            row_vals[i].set_text("no data")

    set_btn_labels("refresh", "wifi", "wifi >")

# ============================================================
# DISPLAY - WIFI MODE
# ============================================================
def show_wifi_mode(conn_status=""):
    lbl_section.set_text("~ wifi ~")
    lbl_section.set_text_color(C_ORANGE)
    lbl_sep.set_text("")
    lbl_out_hdr.set_text("")
    lbl_out_temp.set_text("")
    lbl_out_desc.set_text("")
    lbl_out_hum.set_text("")
    lbl_alert.set_text("")

    ssid, pw = WIFI_NETWORKS[wifi_idx]
    net_num  = "{} / {}".format(wifi_idx + 1, len(WIFI_NETWORKS))

    is_ok = _wlan.isconnected()
    try:
        live_ssid = _wlan.config("essid") if is_ok else "--"
    except:
        live_ssid = "--"

    lbl_r0_k.set_text("network")
    lbl_r0_v.set_text(ssid[:22])
    lbl_r0_v.set_text_color(C_WHITE)
    lbl_r1_k.set_text("connected")
    lbl_r1_v.set_text(live_ssid[:22])
    lbl_r1_v.set_text_color(C_GREEN if is_ok else C_GRAY)
    lbl_r2_k.set_text("slot")
    lbl_r2_v.set_text(net_num)
    lbl_r2_v.set_text_color(C_GRAY)

    if not conn_status:
        conn_status = "all good :)" if is_ok else "not connected"
    lbl_r3_k.set_text("status")
    lbl_r3_v.set_text(conn_status[:18])
    lbl_r3_v.set_text_color(C_GREEN if is_ok else C_ORANGE)

    set_btn_labels("connect", "next", "home >")

# ============================================================
# OUTDOOR DISPLAY
# ============================================================
def update_outdoor_display(w):
    try:
        wd   = w.get("weather", {}) if isinstance(w, dict) else {}
        temp = wd.get("temperature_c")
        desc = str(wd.get("weather_description") or "n/a")
        hum  = wd.get("humidity_pct")
        lbl_out_temp.set_text("{:.1f}C".format(float(temp)) if temp is not None else "--.-C")
        lbl_out_desc.set_text(desc[:16])
        lbl_out_hum.set_text("hum: {}%".format(int(hum)) if hum is not None else "hum: --%")
    except Exception as e:
        print("[DISPLAY] outdoor error:", e)

# ============================================================
# API CALLS
# ============================================================

def _get_json(url):
    try:
        r = urequests.get(url)
        txt = r.text
        r.close()
        return ujson.loads(txt)
    except Exception as e:
        set_status(str(e)[:42], C_RED)
        return None

def api_weather_current():
    return _get_json(API_BASE + "/v1/weather/current?refresh=true")

def api_weather_forecast(days=4):
    return _get_json(API_BASE + "/v1/weather/forecast?days={}".format(days))

def api_latest():
    return _get_json(API_BASE + "/v1/device/{}/latest".format(DEVICE_ID))

def api_ingest(reading):
    t_c   = reading["temperature_c"]
    h_pct = reading["humidity_pct"]
    if t_c is None or h_pct is None:
        return None
    try:
        t = utime.localtime(_real_utc())
        if t[0] < 2024:
            return None
        body = ujson.dumps({
            "secret":    INGEST_SECRET,
            "device_id": DEVICE_ID,
            "timestamp": "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(*t[:6]),
            "indoor":  {"temperature_c": t_c, "humidity_pct": h_pct,
                        "tvoc_ppb": reading["tvoc_ppb"], "eco2_ppm": reading["eco2_ppm"]},
            "motion":  {"detected": reading["motion"], "pir_sensor_id": "pir-portb"},
            "meta":    {"firmware_version": FIRMWARE_VER, "wifi_ssid": WIFI_SSID},
        })
        r = urequests.post(API_BASE + "/v1/ingest",
                           data=body,
                           headers={"Content-Type": "application/json"})
        code = r.status_code
        r.close()
        if code != 200:
            set_status("ingest HTTP " + str(code), C_RED)
            return False
        return True
    except Exception as e:
        set_status("ingest err: " + str(e)[:30], C_RED)
        return False

def api_qa(question):
    try:
        body = ujson.dumps({"device_id": DEVICE_ID, "question": question})
        r = urequests.post(API_BASE + "/v1/qa",
                           data=body,
                           headers={"Content-Type": "application/json"})
        if r.status_code == 200:
            d = ujson.loads(r.text)
            r.close()
            return d.get("answer", "")
        r.close()
        return None
    except Exception as e:
        set_status(str(e)[:42], C_RED)
        return None

# ============================================================
# VOICE QA SCREEN HELPERS
# ============================================================

def _show_answer_screen(answer):
    """
    Display the QA answer using up to 8 display slots for full text.

    Slots and approx char capacity (word-wrapped):
      0-3  : lbl_r0_k .. lbl_r3_k  (FONT_MONT_14, y=68..116, ~30 chars each)
      4    : lbl_alert              (FONT_MONT_10, y=132,      ~42 chars)
      5    : lbl_out_hdr            (FONT_MONT_14, y=152,      ~30 chars)
      6    : lbl_out_temp           (FONT_MONT_14, y=166,      ~30 chars)
      7    : lbl_out_hum            (FONT_MONT_10, y=180,      ~42 chars)
    Total capacity ~260 chars -- enough for any QA response.
    """
    lbl_section.set_text("~ answer ~")
    lbl_section.set_text_color(C_GREEN)
    lbl_sep.set_text("")
    lbl_out_desc.set_text("")
    # Clear all value labels so key labels span full width
    for lbl in [lbl_r0_v, lbl_r1_v, lbl_r2_v, lbl_r3_v]:
        lbl.set_text("")

    SLOTS  = [lbl_r0_k, lbl_r1_k, lbl_r2_k, lbl_r3_k,
              lbl_alert, lbl_out_hdr, lbl_out_temp, lbl_out_hum]
    WIDTHS = [30, 30, 30, 30, 42, 30, 30, 42]
    COLORS = [C_GREEN,  C_GREEN,  C_GREEN,  C_GREEN,
              C_WHITE,  C_WHITE,  C_WHITE,  C_WHITE]
    N = len(SLOTS)

    words    = answer.split()
    lines    = [""] * N
    li       = 0
    overflow = False

    for w in words:
        if li >= N:
            overflow = True
            break
        if lines[li] and len(lines[li]) + 1 + len(w) > WIDTHS[li]:
            li += 1
            if li >= N:
                overflow = True
                break
        lines[li] = (lines[li] + " " + w).strip() if lines[li] else w

    # If text overflowed, mark last line with ellipsis
    if overflow and lines[N - 1]:
        max_w = WIDTHS[N - 1] - 3
        if len(lines[N - 1]) > max_w:
            lines[N - 1] = lines[N - 1][:max_w]
        lines[N - 1] = lines[N - 1].rstrip() + "..."

    for lbl, color, text in zip(SLOTS, COLORS, lines):
        lbl.set_text(text)
        lbl.set_text_color(color)

    set_status("", C_GRAY)


def _beep(n=1):
    """Short audio feedback: n beeps via speaker.tone() -- silently ignored if unavailable."""
    try:
        for _ in range(n):
            speaker.tone(880, 150)
            utime.sleep_ms(250)
    except Exception:
        pass


# ============================================================
# VOICE QA — on-device pipeline (button A to start, button A to stop)
# Record → STT → QA → TTS → speaker.playRaw()
# ============================================================
def _voice_qa_local():
    """
    Full on-device voice pipeline — variable-duration recording.
      1. Record via I2S PDM mic at MIC_RATE Hz until button A pressed again
         (or MIC_MAX_SECS reached)
      2. POST /v1/stt  (Whisper) → transcript
      3. POST /v1/qa   (GPT)     → answer  → displayed immediately
      4. POST /v1/tts  (OpenAI, device=True) → 8 kHz PCM → speaker.playRaw()
      5. Switch to MODE_ANSWER; button C returns home
    gc.collect() is called after each large buffer to avoid OOM.
    """
    global mode

    max_bytes = MIC_RATE * 2 * MIC_MAX_SECS  # 540 KB — safe with Core2 8 MB PSRAM

    # ---- 1. Record (variable duration) ----------------------------
    lbl_section.set_text("~ listening ~")
    lbl_section.set_text_color(C_CYAN)
    for lbl in [lbl_r0_k, lbl_r0_v, lbl_r1_k, lbl_r1_v,
                lbl_r2_k, lbl_r2_v, lbl_r3_k, lbl_r3_v, lbl_alert]:
        lbl.set_text("")
    lbl_r0_k.set_text("press A to stop")
    lbl_r1_k.set_text("speak now!")
    lbl_sep.set_text("")
    lbl_out_hdr.set_text("")
    lbl_out_temp.set_text("")
    lbl_out_desc.set_text("")
    lbl_out_hum.set_text("")
    set_btn_labels("stop", "wifi", "")
    set_status("mic open...", C_CYAN)
    _beep(1)

    raw = None
    try:
        mic = I2S(0,
                  ws=Pin(0),
                  sdin=Pin(34),
                  mode=I2S.MASTER_PDM,
                  dataformat=I2S.B16,
                  channelformat=I2S.ONLY_RIGHT,
                  samplerate=MIC_RATE)
        buf = bytearray(max_bytes)
        tmp = bytearray(MIC_CHUNK)
        pos = 0
        utime.sleep_ms(200)          # let mic stabilise
        while pos + MIC_CHUNK <= max_bytes:
            n = mic.readinto(tmp)
            buf[pos:pos + n] = tmp[:n]
            pos += n
            elapsed = pos // (MIC_RATE * 2)
            lbl_r2_k.set_text("{}s  (max {}s)".format(elapsed, MIC_MAX_SECS))
            if btnA.wasPressed():    # second press → stop recording
                break
        mic.deinit()
        del tmp
        raw = bytes(buf[:pos])
        del buf
    except Exception as e:
        set_status("mic error: " + str(e)[:30], C_RED)
        return
    gc.collect()
    _beep(2)

    # ---- 2. STT ---------------------------------------------------
    lbl_r0_k.set_text("transcribing...")
    lbl_r1_k.set_text("")
    set_status("sending to Whisper...", C_YELLOW)
    transcript = ""
    try:
        b64   = ubinascii.b2a_base64(raw).decode().strip()
        del raw;  gc.collect()
        body  = ujson.dumps({"audio_base64": b64, "mime_type": "audio/pcm", "language": "en"})
        del b64;  gc.collect()
        r     = urequests.post(API_BASE + "/v1/stt",
                               data=body,
                               headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200:
            transcript = ujson.loads(r.text).get("text", "")
        r.close();  gc.collect()
    except Exception as e:
        set_status("STT error: " + str(e)[:28], C_RED)
        return

    if not transcript:
        set_status("nothing heard — try again", C_ORANGE)
        return

    lbl_r0_k.set_text("heard:")
    lbl_r1_k.set_text(transcript[:28])
    set_status("thinking...", C_YELLOW)

    # ---- 3. QA ----------------------------------------------------
    answer = ""
    try:
        body  = ujson.dumps({"device_id": DEVICE_ID, "question": transcript})
        del transcript; gc.collect()
        r     = urequests.post(API_BASE + "/v1/qa",
                               data=body,
                               headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200:
            answer = ujson.loads(r.text).get("answer", "")
        r.close(); gc.collect()
    except Exception as e:
        set_status("QA error: " + str(e)[:28], C_RED)
        return

    # Display answer right away — don't wait for TTS
    _show_answer_screen(answer if answer else "no answer received")

    # ---- 4. TTS → speaker -----------------------------------------
    set_status("speaking...", C_CYAN)
    try:
        body     = ujson.dumps({"text": answer, "voice": "alloy",
                                "audio_format": "pcm", "device": True})
        del answer; gc.collect()
        r        = urequests.post(API_BASE + "/v1/tts",
                                  data=body,
                                  headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200:
            audio_b64 = ujson.loads(r.text).get("audio_base64")
            r.close()
            if audio_b64:
                audio_raw = ubinascii.a2b_base64(audio_b64)
                del audio_b64; gc.collect()
                speaker.playRaw(audio_raw,
                                sample_rate=8000,
                                data_format=speaker.F16B,
                                channel=speaker.CHN_L)
                del audio_raw; gc.collect()
        else:
            r.close()
        set_status("done  :)", C_GREEN)
    except Exception as e:
        # TTS failure is non-fatal — answer is already on screen
        set_status("TTS skip: " + str(e)[:28], C_ORANGE)

    # Switch to dedicated answer page; button C returns home
    mode = MODE_ANSWER
    set_btn_labels("", "wifi", "home")


# ============================================================
# WIFI
# ============================================================
WIFI_SSID     = WIFI_NETWORKS[0][0]
WIFI_PASSWORD = WIFI_NETWORKS[0][1]

_wlan = network.WLAN(network.STA_IF)
_wlan.active(True)

def connect_wifi(ssid, password, retries=5):
    global WIFI_SSID, WIFI_PASSWORD
    set_status("wifi: " + ssid[:20] + "...", C_YELLOW)
    if _wlan.isconnected():
        try:
            if _wlan.config("essid") == ssid:
                WIFI_SSID, WIFI_PASSWORD = ssid, password
                ip = _wlan.ifconfig()[0]
                set_status("wifi: " + ip, C_GREEN)
                return True
        except:
            pass
        _wlan.disconnect()
        time.sleep_ms(300)
    _wlan.connect(ssid, password)
    for i in range(retries * 10):
        if _wlan.isconnected():
            WIFI_SSID, WIFI_PASSWORD = ssid, password
            ip = _wlan.ifconfig()[0]
            set_status("wifi: " + ip, C_GREEN)
            print("[WIFI] connected ip=", ip)
            return True
        time.sleep_ms(500)
        if i % 10 == 9:
            print("[WIFI] waiting attempt", (i // 10) + 1)
    set_status("wifi failed: " + ssid[:16], C_RED)
    return False

# ============================================================
# MAIN
# ============================================================
def main():
    global mode, wifi_idx

    print("[BOOT] v" + FIRMWARE_VER)
    wifi_ok = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    last_ingest_ts    = 0
    last_weather_ts   = 0
    last_reconnect_ts = 0
    last_ntp_ts       = 0
    cached_weather    = {}
    cached_forecast   = {}
    last_reading      = read_sensors()

    if wifi_ok:
        sync_ntp()

        set_status("syncing data...", C_YELLOW)
        latest = api_latest()
        if latest:
            indoor = latest.get("indoor", {})
            if isinstance(indoor, str):
                try:
                    indoor = ujson.loads(indoor)
                except:
                    indoor = {}
            last_reading.update({
                "temperature_c": indoor.get("temperature_c"),
                "humidity_pct":  indoor.get("humidity_pct"),
                "tvoc_ppb":      indoor.get("tvoc_ppb"),
                "eco2_ppm":      indoor.get("eco2_ppm"),
            })
            print("[SYNC] loaded from BigQuery")

        show_indoor_mode(last_reading)

        set_status("peeking outside...", C_YELLOW)
        w = api_weather_current()
        if w:
            cached_weather  = w
            update_outdoor_display(w)
            last_weather_ts = utime.time()
            set_status("cozy and ready  :)", C_GREEN)
        else:
            set_status("no weather data", C_ORANGE)
    else:
        show_indoor_mode(last_reading)
        set_status("offline mode  :(", C_ORANGE)

    # --------------------------------------------------------
    # Main loop
    # A = context-sensitive refresh   B = next WiFi + connect   C = cycle pages
    # --------------------------------------------------------
    wifi_conn_status = ""

    while True:
        now = utime.time()

        # Always update clock
        lbl_time.set_text(get_time_str())
        lbl_date.set_text(get_date_str())

        # --- WiFi keepalive ---
        if wifi_ok and not _wlan.isconnected():
            wifi_ok = False
            set_status("signal lost, reconnecting...", C_ORANGE)
        if not wifi_ok and (now - last_reconnect_ts) >= 30:
            last_reconnect_ts = now
            wifi_ok = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
            if wifi_ok:
                sync_ntp()
                last_ntp_ts = now
                w = api_weather_current()
                if w:
                    cached_weather = w
                    last_weather_ts = now

        # --- NTP retry every 30 s until clock is valid ---
        if wifi_ok and _local_time()[0] < 2024 and (now - last_ntp_ts) >= 30:
            last_ntp_ts = now
            sync_ntp()
            if _local_time()[0] >= 2024:
                set_status("clock is set!", C_GREEN)

        # Read sensors every cycle
        last_reading = read_sensors()

        # --- Render current page ---
        if mode == MODE_NORMAL:
            show_indoor_mode(last_reading)

        elif mode == MODE_FORECAST:
            show_forecast_mode(cached_forecast)

        elif mode == MODE_WIFI:
            show_wifi_mode(wifi_conn_status)

        # MODE_ANSWER: static — _voice_qa_local() already drew everything

        # --- Periodic ingest ---
        if wifi_ok and (now - last_ingest_ts >= INGEST_INTERVAL_SEC):
            ok = api_ingest(last_reading)
            last_ingest_ts = now
            if mode == MODE_NORMAL and ok is True:
                set_status("all good  :)", C_GREEN)

        # --- Periodic background weather refresh ---
        if wifi_ok and (now - last_weather_ts >= WEATHER_INTERVAL_SEC):
            w = api_weather_current()
            if w:
                cached_weather = w
                if mode == MODE_NORMAL:
                    update_outdoor_display(w)
                last_weather_ts = now

        # ---- Button A: micro (home) / refresh forecast / connect wifi ----
        if btnA.wasPressed():
            if mode == MODE_NORMAL:
                if wifi_ok:
                    _voice_qa_local()
                else:
                    set_status("no wifi  :(", C_RED)
            elif mode == MODE_FORECAST:
                if wifi_ok:
                    set_status("peeking at forecast...", C_YELLOW)
                    fc = api_weather_forecast(days=4)
                    if fc:
                        cached_forecast = fc
                    show_forecast_mode(cached_forecast)
                    set_status("forecast fresh!" if fc else "unavailable", C_GREEN if fc else C_ORANGE)
                else:
                    set_status("no wifi  :(", C_RED)
            elif mode == MODE_WIFI:
                ssid, pw = WIFI_NETWORKS[wifi_idx]
                wifi_ok = connect_wifi(ssid, pw)
                if wifi_ok:
                    sync_ntp()
                wifi_conn_status = "all good :)" if wifi_ok else "failed :("
                show_wifi_mode(wifi_conn_status)

        # ---- Button B: cycle to next WiFi network + connect ----
        if btnB.wasPressed():
            wifi_idx = (wifi_idx + 1) % len(WIFI_NETWORKS)
            ssid, pw = WIFI_NETWORKS[wifi_idx]
            wifi_conn_status = "connecting..."
            mode = MODE_WIFI
            show_wifi_mode(wifi_conn_status)
            wifi_ok = connect_wifi(ssid, pw)
            if wifi_ok:
                sync_ntp()
            wifi_conn_status = "all good :)" if wifi_ok else "failed :("
            show_wifi_mode(wifi_conn_status)

        # ---- Button C: cycle pages  Home -> Forecast -> WiFi -> Home / Answer -> Home ----
        if btnC.wasPressed():
            if mode == MODE_ANSWER:
                mode = MODE_NORMAL
                show_indoor_mode(last_reading)
                update_outdoor_display(cached_weather)
                set_status("back home  :)", C_GREEN)
            elif mode == MODE_NORMAL:
                mode = MODE_FORECAST
                wifi_conn_status = ""
                set_status("peeking at forecast...", C_YELLOW)
                if wifi_ok:
                    fc = api_weather_forecast(days=4)
                    if fc:
                        cached_forecast = fc
                show_forecast_mode(cached_forecast)
                set_status("forecast ready!" if cached_forecast else "no data", C_GREEN if cached_forecast else C_ORANGE)
            elif mode == MODE_FORECAST:
                mode = MODE_WIFI
                wifi_conn_status = ""
                show_wifi_mode(wifi_conn_status)
                set_status("wifi settings", C_ORANGE)
            else:  # MODE_WIFI -> HOME
                mode = MODE_NORMAL
                wifi_conn_status = ""
                show_indoor_mode(last_reading)
                update_outdoor_display(cached_weather)
                set_status("back home  :)", C_GREEN)

        time.sleep(0.2)


main()
