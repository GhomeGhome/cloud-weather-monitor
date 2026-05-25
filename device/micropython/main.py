# ============================================================
# main.py  —  M5Stack Core2 Weather Monitor v2.0.0
# Pure MicroPython, NO UIFlow UI framework
# Display : lcd primitives (fillRect / print / line)
# Volume  : direct I2C → AW88298 amplifier (max gain)
# Buttons : A = micro   B = wifi cycle   C = next page
# Themes  : autumn / night / rain / snow  (time + weather)
# ============================================================

from m5stack import lcd, speaker, btnA, btnB, btnC
from machine import I2C, Pin, I2S
import gc, struct, ubinascii, time, utime, network, urequests, ujson

try:
    import ntptime; _HAS_NTP = True
except:
    _HAS_NTP = False

# ============================================================
# CONFIG
# ============================================================
DEVICE_ID    = "core2-main"
FIRMWARE_VER = "2.0.0"
API_BASE     = "https://weather-ingestion-api-972242315876.europe-west6.run.app"

try:
    from config import INGEST_SECRET, WIFI_NETWORKS
except ImportError:
    INGEST_SECRET = "changeme"
    WIFI_NETWORKS = [("YourSSID", "YourPassword")]

UTC_OFFSET_H         = 2
INGEST_INTERVAL_SEC  = 60
WEATHER_INTERVAL_SEC = 300
MIC_RATE             = 18000
MIC_MAX_SECS         = 15
MIC_CHUNK            = MIC_RATE * 2 // 4   # ~0.25 s per chunk

# ============================================================
# COLORS  (RGB565)
# ============================================================
def _rgb(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# ============================================================
# THEMES  — autumn / night / rain / snow
# ============================================================
_THEMES = {
    "autumn": dict(
        bg    = _rgb( 22,  8,  2),
        fg    = _rgb(230,190,150),
        accent= _rgb(200,100, 35),
        good  = _rgb(130,185, 80),
        warn  = _rgb(235,155, 35),
        bad   = _rgb(250, 60, 30),
        card  = _rgb( 40, 15,  3),
        dim   = _rgb(120, 80, 45),
        icon  = "Autumn",
    ),
    "night": dict(
        bg    = _rgb(  4,  8, 28),
        fg    = _rgb(175,200,235),
        accent= _rgb( 90,130,215),
        good  = _rgb( 70,175,135),
        warn  = _rgb(175,155, 55),
        bad   = _rgb(215, 75, 75),
        card  = _rgb(  8, 18, 48),
        dim   = _rgb( 80,100,150),
        icon  = "Night",
    ),
    "rain": dict(
        bg    = _rgb( 12, 22, 38),
        fg    = _rgb(155,185,210),
        accent= _rgb( 50,125,175),
        good  = _rgb( 75,175,155),
        warn  = _rgb(175,155, 55),
        bad   = _rgb(195, 75, 75),
        card  = _rgb( 18, 32, 52),
        dim   = _rgb( 75,110,145),
        icon  = "Rain",
    ),
    "snow": dict(
        bg    = _rgb( 10, 18, 35),
        fg    = _rgb(200,220,240),
        accent= _rgb(150,200,240),
        good  = _rgb(100,200,180),
        warn  = _rgb(200,180,100),
        bad   = _rgb(220,100,100),
        card  = _rgb( 15, 25, 50),
        dim   = _rgb(100,130,170),
        icon  = "Snow",
    ),
}

_theme_name = "autumn"

def T(k):
    return _THEMES[_theme_name][k]

def pick_theme(hour, weather_main=""):
    w = (weather_main or "").lower()
    if hour >= 20 or hour < 7:
        return "night"
    if any(x in w for x in ("snow", "sleet", "blizzard")):
        return "snow"
    if any(x in w for x in ("rain", "drizzle", "thunder", "storm")):
        return "rain"
    return "autumn"

def weather_emoji(main=""):
    m = (main or "").lower()
    if "thunder" in m: return "[storm]"
    if "snow"    in m: return "[snow]"
    if "drizzle" in m: return "[drizzle]"
    if "rain"    in m: return "[rain]"
    if "clear"   in m: return "[sun]"
    if "cloud"   in m: return "[cloud]"
    if any(x in m for x in ("mist","fog","haze")): return "[fog]"
    return "[sky]"

def weather_advice(main=""):
    m = (main or "").lower()
    if any(x in m for x in ("thunder", "storm")): return "Stay inside!"
    if any(x in m for x in ("rain", "drizzle")):  return "Take an umbrella"
    if "snow" in m:                                return "Dress warm"
    if "clear" in m:                               return "Great day outside"
    return ""

# ============================================================
# DISPLAY MODES
# ============================================================
MODE_HOME      = 0
MODE_FORECAST  = 1
MODE_WIFI      = 2
MODE_RECORDING = 3
MODE_ANSWER    = 4

mode     = MODE_HOME
wifi_idx = 0

# ============================================================
# LCD PRIMITIVES
# ============================================================
W, H = 320, 240

lcd.setBrightness(100)

def fill(x, y, w, h, col):
    lcd.fillRect(x, y, w, h, col)

def cls():
    fill(0, 0, W, H, T("bg"))

def hline(y, col=None):
    lcd.line(0, y, W - 1, y, col if col is not None else T("dim"))

def txt(x, y, s, fg, bg, font=lcd.FONT_Default):
    lcd.font(font)
    lcd.setColor(fg, bg)
    lcd.print(str(s), x, y)

def txt_c(y, s, fg, bg, font=lcd.FONT_Default):
    """Print text centered on screen, clearing its row first."""
    lcd.font(font)
    w = lcd.textWidth(str(s))
    x = max(0, (W - w) // 2)
    fill(0, y, W, 26, bg)
    lcd.setColor(fg, bg)
    lcd.print(str(s), x, y)

def btn_bar(a="", b="", c=""):
    fill(0, 200, W, 40, T("card"))
    hline(200)
    lcd.line(106, 203, 106, 237, T("dim"))
    lcd.line(213, 203, 213, 237, T("dim"))
    if a: txt(8,   212, a, T("fg"),  T("card"))
    if b: txt(118, 212, b, T("fg"),  T("card"))
    if c: txt(220, 212, c, T("fg"),  T("card"))

# ============================================================
# AW88298 — direct I2C for maximum volume
# Register 0x0C bits[14:8] = VOL (0 = 0 dB = loudest)
# ============================================================
_amp = None
try:
    _amp = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    _amp.writeto_mem(0x36, 0x0C, b'\x00\x00')
    print("[AMP] AW88298 set to max volume")
except Exception as e:
    print("[AMP] init error:", e)
    _amp = None

def amp_max():
    try:
        if _amp:
            _amp.writeto_mem(0x36, 0x0C, b'\x00\x00')
    except:
        pass
    speaker.setVolume(10)

# ============================================================
# SENSORS  (SHT30 + SGP30 on PORTA — I2C bus 1)
# ============================================================
_I2C1 = I2C(1, scl=Pin(33), sda=Pin(32), freq=100000)
_SHT30, _SGP30 = 0x44, 0x58

def _sht30():
    try:
        _I2C1.writeto(_SHT30, b'\x2C\x06'); time.sleep_ms(50)
        d = _I2C1.readfrom(_SHT30, 6)
        return (round(-45 + 175 * ((d[0]<<8)|d[1]) / 65535, 1),
                round(100 * ((d[3]<<8)|d[4]) / 65535, 1))
    except:
        return None, None

def _sgp30_init():
    try: _I2C1.writeto(_SGP30, b'\x20\x03'); time.sleep_ms(10); return True
    except: return False

def _sgp30():
    try:
        _I2C1.writeto(_SGP30, b'\x20\x08'); time.sleep_ms(12)
        d = _I2C1.readfrom(_SGP30, 6)
        return (d[3]<<8)|d[4], (d[0]<<8)|d[1]   # tvoc, eco2
    except:
        return None, None

_found    = _I2C1.scan()
_sht30_ok = _SHT30 in _found
_sgp30_ok = _SGP30 in _found and _sgp30_init()
print("[I2C] found:", [hex(a) for a in _found])

def read_sensors():
    r = {"temperature_c":None,"humidity_pct":None,
         "tvoc_ppb":None,"eco2_ppm":None,"motion":False}
    if _sht30_ok: r["temperature_c"], r["humidity_pct"] = _sht30()
    if _sgp30_ok: r["tvoc_ppb"],      r["eco2_ppm"]     = _sgp30()
    return r

def c_temp(v):
    if v is None: return T("dim")
    return T("good") if 18 <= v <= 26 else T("warn") if v < 30 else T("bad")

def c_hum(v):
    if v is None: return T("dim")
    if v < 30:    return T("bad")
    if v < 40:    return T("warn")
    if v <= 70:   return T("good")
    return T("warn")

def c_tvoc(v):
    if v is None: return T("dim")
    return T("good") if v < 220 else T("warn") if v < 660 else T("bad")

def c_co2(v):
    if v is None: return T("dim")
    return T("good") if v < 1000 else T("warn") if v < 2000 else T("bad")

# ============================================================
# NTP + TIME
# ============================================================
_time_offset = 0

def _iso_epoch(ts):
    y,mo,d = int(ts[0:4]),int(ts[5:7]),int(ts[8:10])
    h,mi,s = int(ts[11:13]),int(ts[14:16]),int(ts[17:19])
    days = sum(366 if yr%4==0 and (yr%100!=0 or yr%400==0) else 365
               for yr in range(2000, y))
    dm = [31, 29 if y%4==0 and (y%100!=0 or y%400==0) else 28,
          31,30,31,30,31,31,30,31,30,31]
    for m in range(1, mo): days += dm[m-1]
    return (days + d - 1) * 86400 + h*3600 + mi*60 + s

def sync_ntp():
    global _time_offset
    if _HAS_NTP:
        try: ntptime.settime()
        except: pass
    if utime.localtime(utime.time())[0] >= 2024:
        _time_offset = 0; return
    try:
        r = urequests.get(API_BASE + "/live")
        ts = ujson.loads(r.text).get("ts", ""); r.close()
        if len(ts) >= 19:
            _time_offset = _iso_epoch(ts) - utime.time()
    except:
        pass

def _utc():
    return utime.time() + _time_offset

def _local():
    return utime.localtime(_utc() + UTC_OFFSET_H * 3600)

_DAYS   = ("Mon","Tue","Wed","Thu","Fri","Sat","Sun")
_MONTHS = ("Jan","Feb","Mar","Apr","May","Jun",
           "Jul","Aug","Sep","Oct","Nov","Dec")

def time_hm():  t = _local(); return "{:02d}:{:02d}".format(t[3], t[4])
def time_sec(): t = _local(); return ":{:02d}".format(t[5])
def date_str(): t = _local(); return "{} {} {}".format(_DAYS[t[6]], t[2], _MONTHS[t[1]-1])

# ============================================================
# DISPLAY — HOME  (réveil style)
#
#  y=0-27   indoor strip  (temp / hum / tvoc / co2)
#  y=28     separator
#  y=30-107 clock  HH:MM  DejaVu72 centered
#  y=107    seconds  :SS  DejaVu18
#  y=118    date  DejaVu18 centered
#  y=136    separator
#  y=138-195 outdoor  (emoji + temp + desc + advice)
#  y=196    separator
#  y=200-239 button bar
# ============================================================
def draw_home(r, weather=None, status=""):
    global _theme_name
    t_now  = _local()
    w_main = ""
    if weather:
        w_main = str(weather.get("weather", {}).get("weather_main", ""))
    _theme_name = pick_theme(t_now[3], w_main)

    cls()

    # ── Indoor strip ─────────────────────────────────────────
    fill(0, 0, W, 28, T("card"))
    t_c  = r["temperature_c"]
    h_p  = r["humidity_pct"]
    tvoc = r["tvoc_ppb"]
    co2  = r["eco2_ppm"]

    def fv(v, fmt, fb): return fmt.format(v) if v is not None else fb

    metrics = [
        (fv(t_c,  "T:{:.0f}C",  "T:--"),  c_temp(t_c)),
        (fv(h_p,  "H:{:.0f}%",  "H:--"),  c_hum(h_p)),
        (fv(tvoc, "V:{}ppb",    "V:---"),  c_tvoc(tvoc)),
        (fv(co2,  "C:{}ppm",    "C:----"), c_co2(co2)),
    ]
    cw = W // 4
    for i, (val, col) in enumerate(metrics):
        txt(i * cw + 4, 6, val, col, T("card"))

    hline(28)

    # ── Clock  HH:MM ─────────────────────────────────────────
    fill(0, 30, W, 90, T("bg"))
    hm = time_hm()
    lcd.font(lcd.FONT_DejaVu72)
    hw = lcd.textWidth(hm)
    hx = (W - hw) // 2
    lcd.setColor(T("fg"), T("bg"))
    lcd.print(hm, hx, 30)

    # Seconds :SS  (smaller, bottom-right of clock)
    sc = time_sec()
    lcd.font(lcd.FONT_DejaVu18)
    sw = lcd.textWidth(sc)
    fill(hx + hw, 95, sw + 4, 20, T("bg"))
    lcd.setColor(T("dim"), T("bg"))
    lcd.print(sc, hx + hw + 2, 97)

    # ── Date ─────────────────────────────────────────────────
    txt_c(120, date_str(), T("accent"), T("bg"), lcd.FONT_DejaVu18)

    # ── Outdoor ──────────────────────────────────────────────
    hline(140)
    fill(0, 141, W, 57, T("card"))

    if weather:
        wd      = weather.get("weather", {})
        out_t   = wd.get("temperature_c")
        out_h   = wd.get("humidity_pct")
        out_desc = str(wd.get("weather_description") or w_main or "").capitalize()[:18]
        emj     = weather_emoji(w_main)
        advice  = weather_advice(w_main)
        temp_s  = "{:.0f}C".format(out_t)  if out_t is not None else "--C"
        hum_s   = "hum {:.0f}%".format(out_h) if out_h is not None else ""
        txt(6, 144, emj + " " + temp_s + "  " + out_desc, T("warn"),   T("card"))
        if advice:
            txt(6, 160, advice,                              T("accent"), T("card"))
        txt(6, 176, hum_s,                                   T("dim"),   T("card"))
    else:
        txt(6, 158, "no outdoor data", T("dim"), T("card"))

    hline(198)
    btn_bar("micro", "wifi", "forecast")
    if status:
        fill(0, 226, W, 14, T("card"))
        txt(8, 226, status, T("dim"), T("card"))


def _update_clock_only():
    """Partial update: redraw only clock + seconds, no full cls()."""
    fill(0, 30, W, 90, T("bg"))
    hm = time_hm()
    lcd.font(lcd.FONT_DejaVu72)
    hw = lcd.textWidth(hm)
    hx = (W - hw) // 2
    lcd.setColor(T("fg"), T("bg"))
    lcd.print(hm, hx, 30)

    sc = time_sec()
    lcd.font(lcd.FONT_DejaVu18)
    sw = lcd.textWidth(sc)
    fill(hx + hw, 95, sw + 6, 22, T("bg"))
    lcd.setColor(T("dim"), T("bg"))
    lcd.print(sc, hx + hw + 2, 97)


# ============================================================
# DISPLAY — FORECAST
# ============================================================
def draw_forecast(fc_data, status=""):
    cls()
    fill(0, 0, W, 28, T("card"))
    txt(6, 6, "Forecast  4 days", T("accent"), T("card"))
    hline(28)

    days = []
    if isinstance(fc_data, dict):
        fc = fc_data.get("forecast", {})
        if isinstance(fc, dict):   days = fc.get("daily", [])
        elif isinstance(fc, list): days = fc

    ROW_H = 38
    for i in range(4):
        y = 32 + i * (ROW_H + 2)
        fill(0, y, W, ROW_H, T("card"))
        if i < len(days):
            d    = days[i]
            date = str(d.get("date", ""))
            tmin = d.get("temp_min_c"); tmax = d.get("temp_max_c")
            w_m  = str(d.get("weather_main") or "")
            desc = str(d.get("weather_description") or w_m or "")[:16]
            try:   date_s = "{} {}".format(int(date[8:10]), _MONTHS[int(date[5:7])-1])
            except: date_s = date[:6]
            temp_s = "{:.0f}/{:.0f}C".format(tmin, tmax) if tmin and tmax else "--/--C"
            txt(6,   y+5,  weather_emoji(w_m), T("warn"),   T("card"))
            txt(28,  y+5,  date_s,             T("accent"),  T("card"))
            txt(100, y+5,  temp_s,             T("fg"),      T("card"))
            txt(6,   y+20, desc,               T("dim"),     T("card"))
        else:
            txt(6, y + 12, "no data", T("dim"), T("card"))
        hline(y + ROW_H)

    btn_bar("refresh", "wifi", "wifi >")
    if status:
        fill(0, 226, W, 14, T("card"))
        txt(8, 226, status, T("dim"), T("card"))


# ============================================================
# DISPLAY — WIFI
# ============================================================
def draw_wifi(conn_status=""):
    cls()
    fill(0, 0, W, 28, T("card"))
    txt(6, 6, "WiFi settings", T("accent"), T("card"))
    hline(28)

    ssid, _ = WIFI_NETWORKS[wifi_idx]
    is_ok   = _wlan.isconnected()
    try:    live = _wlan.config("essid") if is_ok else "--"
    except: live = "--"

    rows = [
        ("network",   ssid[:22],
         T("fg")),
        ("connected", live[:22],
         T("good") if is_ok else T("dim")),
        ("slot",      "{} / {}".format(wifi_idx + 1, len(WIFI_NETWORKS)),
         T("fg")),
        ("status",    (conn_status or ("ok :)" if is_ok else "not connected"))[:20],
         T("good") if is_ok else T("warn")),
    ]
    for i, (lbl, val, col) in enumerate(rows):
        y = 32 + i * 38
        fill(0, y, W, 36, T("card"))
        txt(6,  y + 5, lbl, T("dim"), T("card"))
        txt(96, y + 5, val, col,      T("card"))
        hline(y + 36)

    btn_bar("connect", "next", "home")


# ============================================================
# DISPLAY — RECORDING
# ============================================================
def draw_recording(elapsed=0):
    fill(0, 30, W, 168, T("bg"))
    # Central REC card
    fill(W//2 - 55, 45, 110, 72, T("card"))
    lcd.drawRect(W//2 - 55, 45, 110, 72, T("accent"))
    lcd.font(lcd.FONT_DejaVu40)
    lcd.setColor(T("accent"), T("card"))
    rw = lcd.textWidth("REC")
    lcd.print("REC", W//2 - rw//2, 55)
    # Elapsed
    es = "{}s / {}s".format(elapsed, MIC_MAX_SECS)
    lcd.font(lcd.FONT_DejaVu18)
    ew = lcd.textWidth(es)
    fill(0, 125, W, 22, T("bg"))
    lcd.setColor(T("warn"), T("bg"))
    lcd.print(es, (W - ew)//2, 126)
    # Hint
    lcd.font(lcd.FONT_Default)
    hw = lcd.textWidth("press A to stop")
    fill(0, 152, W, 14, T("bg"))
    lcd.setColor(T("dim"), T("bg"))
    lcd.print("press A to stop", (W - hw)//2, 153)


# ============================================================
# DISPLAY — ANSWER
# ============================================================
def draw_answer(answer, status=""):
    cls()
    fill(0, 0, W, 28, T("card"))
    txt(6, 6, "Answer", T("accent"), T("card"))
    hline(28)
    fill(0, 30, W, 168, T("card"))

    # Word-wrap into ~38-char lines
    words = (answer or "").split()
    lines = []; line = ""
    for w in words:
        if len(line) + 1 + len(w) > 38 and line:
            lines.append(line); line = w
        else:
            line = (line + " " + w).strip() if line else w
    if line: lines.append(line)

    for i, ln in enumerate(lines[:9]):
        col = T("good") if i < 3 else T("fg")
        txt(8, 33 + i * 18, ln, col, T("card"))

    hline(198)
    btn_bar("", "wifi", "home")
    if status:
        fill(0, 226, W, 14, T("card"))
        txt(8, 226, status, T("dim"), T("card"))


# ============================================================
# STATUS BAR
# ============================================================
def set_status(msg, color=None):
    fill(0, 226, W, 14, T("card"))
    txt(8, 226, str(msg)[:48], color if color is not None else T("dim"), T("card"))


# ============================================================
# API CALLS
# ============================================================
def _get_json(url):
    try:
        r = urequests.get(url); s = r.text; r.close()
        return ujson.loads(s)
    except Exception as e:
        set_status(str(e)[:46], T("bad")); return None

def api_weather_current():     return _get_json(API_BASE + "/v1/weather/current?refresh=true")
def api_weather_forecast(d=4): return _get_json(API_BASE + "/v1/weather/forecast?days={}".format(d))
def api_latest():              return _get_json(API_BASE + "/v1/device/{}/latest".format(DEVICE_ID))

def api_ingest(reading):
    tc = reading["temperature_c"]; hp = reading["humidity_pct"]
    if tc is None or hp is None: return None
    try:
        t = utime.localtime(_utc())
        if t[0] < 2024: return None
        body = ujson.dumps({
            "secret": INGEST_SECRET, "device_id": DEVICE_ID,
            "timestamp": "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(*t[:6]),
            "indoor":  {"temperature_c": tc, "humidity_pct": hp,
                        "tvoc_ppb": reading["tvoc_ppb"], "eco2_ppm": reading["eco2_ppm"]},
            "motion":  {"detected": False, "pir_sensor_id": "none"},
            "meta":    {"firmware_version": FIRMWARE_VER, "wifi_ssid": WIFI_SSID},
        })
        r    = urequests.post(API_BASE + "/v1/ingest", data=body,
                              headers={"Content-Type": "application/json"})
        code = r.status_code; r.close()
        return code == 200
    except Exception as e:
        set_status("ingest: " + str(e)[:34], T("bad")); return False


# ============================================================
# AUDIO HELPERS
# ============================================================
def _wav_hdr(n, rate=18000):
    br = rate * 2
    return (b'RIFF' + struct.pack('<I', 36 + n) + b'WAVEfmt ' +
            struct.pack('<IHHIIHH', 16, 1, 1, rate, br, 2, 16) +
            b'data'  + struct.pack('<I', n))

def _beep(n=1):
    try:
        for _ in range(n):
            speaker.tone(880, 150)
            utime.sleep_ms(250)
    except:
        pass


# ============================================================
# VOICE QA PIPELINE
# ============================================================
def _voice_qa():
    global mode
    max_bytes = MIC_RATE * 2 * MIC_MAX_SECS

    # ── 1. Recording screen ───────────────────────────────────
    fill(0, 0, W, 28, T("card"))
    txt(6, 6, "Listening...", T("accent"), T("card"))
    hline(28)
    draw_recording(0)
    btn_bar("stop", "wifi", "")
    set_status("mic open...", T("accent"))
    _beep(1)

    raw = None
    try:
        mic = I2S(0, ws=Pin(0), sdin=Pin(34), mode=I2S.MASTER_PDM,
                  dataformat=I2S.B16, channelformat=I2S.ONLY_RIGHT,
                  samplerate=MIC_RATE)
        buf = bytearray(max_bytes); tmp = bytearray(MIC_CHUNK); pos = 0
        utime.sleep_ms(200)
        while pos + MIC_CHUNK <= max_bytes:
            n = mic.readinto(tmp)
            buf[pos:pos + n] = tmp[:n]; pos += n
            draw_recording(pos // (MIC_RATE * 2))
            if btnA.wasPressed(): break
        mic.deinit(); del tmp
        pcm = bytes(buf[:pos]); del buf
        raw = _wav_hdr(len(pcm), MIC_RATE) + pcm; del pcm
    except Exception as e:
        set_status("mic: " + str(e)[:34], T("bad")); return
    gc.collect(); _beep(2)

    # ── 2. STT ───────────────────────────────────────────────
    set_status("transcribing...", T("warn"))
    transcript = ""
    try:
        b64  = ubinascii.b2a_base64(raw).decode().strip(); del raw; gc.collect()
        body = ujson.dumps({"audio_base64": b64, "mime_type": "audio/wav", "language": "en"})
        del b64; gc.collect()
        r = urequests.post(API_BASE + "/v1/stt", data=body,
                           headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200: transcript = ujson.loads(r.text).get("text", "")
        r.close(); gc.collect()
    except Exception as e:
        set_status("STT: " + str(e)[:34], T("bad")); return

    if not transcript:
        set_status("nothing heard  — try again", T("warn")); return
    set_status("heard: " + transcript[:30], T("fg"))

    # ── 3. QA ────────────────────────────────────────────────
    answer = ""
    try:
        body = ujson.dumps({"device_id": DEVICE_ID, "question": transcript})
        del transcript; gc.collect()
        r = urequests.post(API_BASE + "/v1/qa", data=body,
                           headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200: answer = ujson.loads(r.text).get("answer", "")
        r.close(); gc.collect()
    except Exception as e:
        set_status("QA: " + str(e)[:34], T("bad")); return

    draw_answer(answer if answer else "no answer received")

    # ── 4. TTS → speaker ─────────────────────────────────────
    set_status("loading audio...", T("warn"))
    try:
        body = ujson.dumps({"text": answer, "voice": "alloy",
                            "audio_format": "pcm", "device": True})
        del answer; gc.collect()
        r = urequests.post(API_BASE + "/v1/tts", data=body,
                           headers={"Content-Type": "application/json"})
        del body; gc.collect()
        if r.status_code == 200:
            ab = ujson.loads(r.text).get("audio_base64"); r.close()
            if ab:
                audio = ubinascii.a2b_base64(ab); del ab; gc.collect()
                set_status("speaking...", T("accent"))
                amp_max()
                speaker.playRaw(audio, sample_rate=8000,
                                data_format=speaker.F16B,
                                channel=speaker.CHN_LR)
                del audio; gc.collect()
        else:
            r.close()
        set_status("done  :)", T("good"))
    except Exception as e:
        set_status("TTS: " + str(e)[:34], T("warn"))

    mode = MODE_ANSWER


# ============================================================
# WIFI
# ============================================================
WIFI_SSID     = WIFI_NETWORKS[0][0]
WIFI_PASSWORD = WIFI_NETWORKS[0][1]

_wlan = network.WLAN(network.STA_IF)
_wlan.active(True)

def connect_wifi(ssid, pw, retries=5):
    global WIFI_SSID, WIFI_PASSWORD
    set_status("wifi: " + ssid[:20] + "...", T("warn"))
    if _wlan.isconnected():
        try:
            if _wlan.config("essid") == ssid:
                WIFI_SSID, WIFI_PASSWORD = ssid, pw
                set_status(_wlan.ifconfig()[0], T("good")); return True
        except:
            pass
        _wlan.disconnect(); time.sleep_ms(300)
    _wlan.connect(ssid, pw)
    for i in range(retries * 10):
        if _wlan.isconnected():
            WIFI_SSID, WIFI_PASSWORD = ssid, pw
            set_status(_wlan.ifconfig()[0], T("good"))
            print("[WIFI] connected ip=", _wlan.ifconfig()[0])
            return True
        time.sleep_ms(500)
    set_status("wifi failed: " + ssid[:14], T("bad")); return False


# ============================================================
# MAIN
# ============================================================
def main():
    global mode, wifi_idx

    print("[BOOT] v" + FIRMWARE_VER)
    cls()
    set_status("connecting...", T("warn"))

    wifi_ok = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    last_ingest_ts    = 0
    last_weather_ts   = 0
    last_reconnect_ts = 0
    last_ntp_ts       = 0
    cached_weather    = {}
    cached_forecast   = {}
    last_reading      = read_sensors()
    _need_redraw      = True
    _last_hm          = ""
    _last_sc          = ""
    wifi_conn_status  = ""

    if wifi_ok:
        sync_ntp()
        set_status("syncing...", T("warn"))
        latest = api_latest()
        if latest:
            indoor = latest.get("indoor", {})
            if isinstance(indoor, str):
                try: indoor = ujson.loads(indoor)
                except: indoor = {}
            last_reading.update({k: indoor.get(k) for k in
                ("temperature_c","humidity_pct","tvoc_ppb","eco2_ppm")})
        set_status("peeking outside...", T("warn"))
        w = api_weather_current()
        if w: cached_weather = w; last_weather_ts = utime.time()

    draw_home(last_reading, cached_weather,
              "ready :)" if wifi_ok else "offline :(")
    _need_redraw = False

    while True:
        now = utime.time()

        # ── WiFi keepalive ────────────────────────────────────
        if wifi_ok and not _wlan.isconnected():
            wifi_ok = False; set_status("signal lost...", T("warn"))
        if not wifi_ok and (now - last_reconnect_ts) >= 30:
            last_reconnect_ts = now
            wifi_ok = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
            if wifi_ok: sync_ntp(); last_ntp_ts = now; _need_redraw = True

        # ── NTP retry ─────────────────────────────────────────
        if wifi_ok and _local()[0] < 2024 and (now - last_ntp_ts) >= 30:
            last_ntp_ts = now; sync_ntp()

        # ── Periodic ingest ───────────────────────────────────
        if wifi_ok and (now - last_ingest_ts) >= INGEST_INTERVAL_SEC:
            last_reading = read_sensors()
            api_ingest(last_reading); last_ingest_ts = now
            if mode == MODE_HOME: _need_redraw = True

        # ── Periodic weather ──────────────────────────────────
        if wifi_ok and (now - last_weather_ts) >= WEATHER_INTERVAL_SEC:
            w = api_weather_current()
            if w: cached_weather = w; last_weather_ts = now
            if mode == MODE_HOME: _need_redraw = True

        # ── Full page redraw ──────────────────────────────────
        if _need_redraw:
            if   mode == MODE_HOME:     draw_home(last_reading, cached_weather)
            elif mode == MODE_FORECAST: draw_forecast(cached_forecast)
            elif mode == MODE_WIFI:     draw_wifi(wifi_conn_status)
            _need_redraw = False

        # ── Partial clock update (home page only) ─────────────
        if mode == MODE_HOME:
            hm = time_hm(); sc = time_sec()
            if hm != _last_hm or sc != _last_sc:
                _update_clock_only()
                _last_hm, _last_sc = hm, sc

        # ── Buttons ───────────────────────────────────────────
        if btnA.wasPressed():
            if mode == MODE_HOME:
                if wifi_ok: _voice_qa()
                else: set_status("no wifi :(", T("bad"))
            elif mode == MODE_FORECAST:
                if wifi_ok:
                    set_status("refreshing...", T("warn"))
                    fc = api_weather_forecast(4)
                    if fc: cached_forecast = fc
                    draw_forecast(cached_forecast, "ok")
            elif mode == MODE_WIFI:
                ssid, pw = WIFI_NETWORKS[wifi_idx]
                wifi_ok = connect_wifi(ssid, pw)
                if wifi_ok: sync_ntp()
                wifi_conn_status = "ok :)" if wifi_ok else "failed :("
                draw_wifi(wifi_conn_status)

        if btnB.wasPressed():
            wifi_idx = (wifi_idx + 1) % len(WIFI_NETWORKS)
            ssid, pw = WIFI_NETWORKS[wifi_idx]
            mode = MODE_WIFI; wifi_conn_status = "connecting..."
            draw_wifi(wifi_conn_status)
            wifi_ok = connect_wifi(ssid, pw)
            if wifi_ok: sync_ntp()
            wifi_conn_status = "ok :)" if wifi_ok else "failed :("
            draw_wifi(wifi_conn_status)

        if btnC.wasPressed():
            if mode == MODE_ANSWER:
                mode = MODE_HOME; _need_redraw = True
                set_status("ready :)", T("good"))
            elif mode == MODE_HOME:
                mode = MODE_FORECAST
                if wifi_ok:
                    set_status("loading...", T("warn"))
                    fc = api_weather_forecast(4)
                    if fc: cached_forecast = fc
                draw_forecast(cached_forecast)
            elif mode == MODE_FORECAST:
                mode = MODE_WIFI; draw_wifi()
            else:   # WIFI -> HOME
                mode = MODE_HOME; _need_redraw = True
                wifi_conn_status = ""
                set_status("home :)", T("good"))

        time.sleep(0.2)


main()
