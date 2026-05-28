import base64
import os
import random
import time
from datetime import timezone, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

_DISPLAY_TZ = timezone(timedelta(hours=2))


def _fmt_ts(ts) -> str:
    try:
        return ts.astimezone(_DISPLAY_TZ).strftime("%d %b, %H:%M")
    except Exception:
        return str(ts)


from charts import line_chart
from data import indoor_history, latest_indoor, latest_outdoor, recent_events

# ============================================================
# CONFIG
# ============================================================
API_BASE = os.getenv(
    "API_BASE",
    "https://weather-ingestion-api-972242315876.europe-west6.run.app",
)

st.set_page_config(page_title="Weather Monitor", page_icon="🌤️", layout="wide")

# ============================================================
# GLOBAL CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #0F172A !important; }

/* ── Header : dark theme instead of hiding (keeps native sidebar toggle) ── */
header[data-testid="stHeader"] {
    background: #0D1424 !important;
    border-bottom: 1px solid rgba(148,163,184,0.07) !important;
}
header[data-testid="stHeader"] button svg { fill: #94A3B8 !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 1rem !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0D1424 !important;
    border-right: 1px solid rgba(148,163,184,0.07) !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: #94A3B8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2  { color: #E2E8F0 !important; }

/* Hide Streamlit chrome */
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }
#MainMenu { visibility: hidden !important; }

/* Headings */
h1 { color: #F1F5F9 !important; font-weight: 800 !important; letter-spacing: -0.02em; }
h2 { color: #E2E8F0 !important; font-weight: 700 !important; }
h3 { color: #CBD5E1 !important; font-weight: 600 !important; }
p, li { color: #CBD5E1; }

/* Metric tiles */
[data-testid="stMetric"] {
    background: rgba(30,41,59,0.65) !important;
    border: 1px solid rgba(148,163,184,0.1) !important;
    border-radius: 16px !important;
    padding: 20px 22px !important;
    backdrop-filter: blur(8px);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
}

/* Buttons */
.stButton > button {
    background: rgba(56,189,248,0.07) !important;
    color: #7DD3FC !important;
    border: 1px solid rgba(56,189,248,0.22) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: rgba(56,189,248,0.16) !important;
    border-color: rgba(56,189,248,0.45) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(56,189,248,0.12) !important;
}

/* Text input */
.stTextInput > div > div > input {
    background: #1E293B !important;
    border: 1px solid rgba(148,163,184,0.2) !important;
    color: #E2E8F0 !important;
    border-radius: 10px !important;
}
.stTextInput > div > div > input::placeholder { color: #64748B !important; }
.stTextInput > div > div > input:focus {
    border-color: rgba(56,189,248,0.4) !important;
    box-shadow: 0 0 0 2px rgba(56,189,248,0.1) !important;
}

/* Alerts */
.stSuccess { background: rgba(74,222,128,0.07) !important; border-left: 3px solid #4ADE80 !important; color: #86EFAC !important; border-radius: 10px !important; }
.stWarning { background: rgba(250,204,21,0.07) !important; border-left: 3px solid #FACC15 !important; color: #FDE68A !important; border-radius: 10px !important; }
.stError   { background: rgba(248,113,113,0.07) !important; border-left: 3px solid #F87171 !important; color: #FCA5A5 !important; border-radius: 10px !important; }
.stInfo    { background: rgba(56,189,248,0.07) !important; border-left: 3px solid #38BDF8 !important; color: #7DD3FC !important; border-radius: 10px !important; }

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid rgba(148,163,184,0.1) !important;
    border-radius: 12px !important;
    background: rgba(15,23,42,0.5) !important;
}

/* Divider / caption */
hr { border-color: rgba(148,163,184,0.07) !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }

/* Dataframe */
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }

/* Audio widget */
audio { width: 100%; border-radius: 8px; }

/* ═══════════════ CREATURE ANIMATIONS ═══════════════ */

/* 🐌 Snail waddle */
@keyframes snail-walk {
    0%, 100% { transform: translateX(0) scaleX(1); }
    45%      { transform: translateX(7px) scaleX(1); }
    50%      { transform: translateX(7px) scaleX(-1); }
    95%      { transform: translateX(0) scaleX(-1); }
}
.snail-anim { animation: snail-walk 4s ease-in-out infinite; display: inline-block; }

/* ☀️ Sun pulse */
@keyframes sun-pulse {
    0%, 100% { transform: scale(1) rotate(0deg);
               filter: drop-shadow(0 0 8px rgba(250,204,21,.45)); }
    50%      { transform: scale(1.14) rotate(14deg);
               filter: drop-shadow(0 0 20px rgba(250,204,21,.75)); }
}
.sun-anim { animation: sun-pulse 3.5s ease-in-out infinite; display: inline-block; }

/* ❄️ Snow bob */
@keyframes snow-bob {
    0%, 100% { transform: translateY(0) rotate(-5deg); }
    50%      { transform: translateY(-7px) rotate(5deg); }
}
.snow-anim { animation: snow-bob 2.2s ease-in-out infinite; display: inline-block; }

/* ☁️ Cloud drift */
@keyframes cloud-drift {
    0%, 100% { transform: translateX(0); }
    50%      { transform: translateX(9px); }
}
.cloud-anim { animation: cloud-drift 5s ease-in-out infinite; display: inline-block; }

/* 👻 Ghost float */
@keyframes ghost-float {
    0%, 100% { transform: translateY(0) rotate(-3deg); opacity: .85; }
    50%      { transform: translateY(-8px) rotate(3deg); opacity: 1; }
}
.ghost-anim { animation: ghost-float 3s ease-in-out infinite; display: inline-block; }

/* ⚡ Lightning flash */
@keyframes lightning-flash {
    0%, 87%, 100% { opacity: 0; }
    89%, 92%      { opacity: 1; }
}
.lightning-anim { animation: lightning-flash 4s ease infinite; display: inline-block; }

/* 🐸 Frog bounce */
@keyframes frog-bounce {
    0%, 100% { transform: translateY(0) scaleY(1); }
    40%      { transform: translateY(-9px) scaleY(1.08); }
    55%      { transform: translateY(0) scaleY(.94); }
}
.frog-anim { animation: frog-bounce 2s ease-in-out infinite; display: inline-block; }

/* 📈 Chart bounce (History page) */
@keyframes chart-bounce {
    0%, 100% { transform: translateY(0) scale(1); }
    50%      { transform: translateY(-6px) scale(1.1); }
}
.chart-anim { animation: chart-bounce 2.8s ease-in-out infinite; display: inline-block; }

/* 🔔 Bell ring (Events page) */
@keyframes bell-ring {
    0%, 85%, 100%  { transform: rotate(0); }
    87%  { transform: rotate(16deg); }
    90%  { transform: rotate(-13deg); }
    93%  { transform: rotate(9deg); }
    96%  { transform: rotate(-5deg); }
}
.bell-anim {
    animation: bell-ring 3.5s ease-in-out infinite;
    display: inline-block;
    transform-origin: top center;
}

/* 🎙️ Mic pulse (Voice QA page) */
@keyframes mic-pulse {
    0%, 100% { transform: scale(1);
               filter: drop-shadow(0 0 4px rgba(56,189,248,.3)); }
    50%      { transform: scale(1.15);
               filter: drop-shadow(0 0 12px rgba(56,189,248,.7)); }
}
.mic-anim { animation: mic-pulse 2.2s ease-in-out infinite; display: inline-block; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# WEATHER HELPERS
# ============================================================

def _weather_emoji(main: str, size: str = "3.5rem") -> str:
    """Return a large animated weather emoji (HTML span) matching the condition."""
    m = main.lower()
    if "thunderstorm" in m:
        emoji, anim, shadow = "⛈️", "lightning-anim", "rgba(167,139,250,.5)"
    elif "snow" in m:
        emoji, anim, shadow = "🌨️", "snow-anim",      "rgba(186,230,253,.5)"
    elif "drizzle" in m:
        emoji, anim, shadow = "🌦️", "frog-anim",      "rgba(56,189,248,.4)"
    elif "rain" in m:
        emoji, anim, shadow = "🌧️", "snail-anim",     "rgba(56,189,248,.5)"
    elif "clear" in m:
        emoji, anim, shadow = "☀️",  "sun-anim",       "rgba(250,204,21,.55)"
    elif "cloud" in m:
        emoji, anim, shadow = "⛅",  "cloud-anim",     "rgba(148,163,184,.4)"
    elif any(w in m for w in ["mist", "fog", "haze", "smoke"]):
        emoji, anim, shadow = "🌫️", "ghost-anim",     "rgba(148,163,184,.3)"
    else:
        emoji, anim, shadow = "🌤️", "cloud-anim",     "rgba(148,163,184,.3)"
    return (
        f'<span class="{anim}" '
        f'style="font-size:{size};filter:drop-shadow(0 0 14px {shadow});'
        f'line-height:1;display:inline-block">{emoji}</span>'
    )


def _creature_html(main: str) -> str:
    """Smaller companion creature for the weather banner."""
    m = main.lower()
    if "thunderstorm" in m: return '<span class="lightning-anim" style="font-size:2rem">⚡</span>'
    if "snow"         in m: return '<span class="snow-anim"      style="font-size:2rem">🐧</span>'
    if "drizzle"      in m: return '<span class="frog-anim"      style="font-size:2rem">🐸</span>'
    if "rain"         in m: return '<span class="snail-anim"     style="font-size:2rem">🐌</span>'
    if "clear"        in m: return '<span class="sun-anim"       style="font-size:2rem">🦎</span>'
    if "cloud"        in m: return '<span class="cloud-anim"     style="font-size:2rem">🐑</span>'
    if any(w in m for w in ["mist", "fog", "haze"]):
        return '<span class="ghost-anim" style="font-size:2rem">👻</span>'
    return '<span style="font-size:2rem">🌈</span>'


def _banner_bg(main: str):
    m = main.lower()
    if "thunderstorm" in m: return "linear-gradient(135deg,#180826 0%,#0F172A 100%)", "rgba(167,139,250,0.22)"
    if "snow"         in m: return "linear-gradient(135deg,#0C1E35 0%,#0F172A 100%)", "rgba(186,230,253,0.22)"
    if "rain"         in m or "drizzle" in m:
        return "linear-gradient(135deg,#071F3A 0%,#0F172A 100%)", "rgba(56,189,248,0.22)"
    if "clear"        in m: return "linear-gradient(135deg,#1C1400 0%,#0F172A 100%)", "rgba(250,204,21,0.22)"
    if "cloud"        in m: return "linear-gradient(135deg,#111827 0%,#0F172A 100%)", "rgba(148,163,184,0.15)"
    return "linear-gradient(135deg,#1E293B 0%,#0F172A 100%)", "rgba(148,163,184,0.12)"


def _rain_drops_html() -> str:
    drops = "".join(
        f'<span style="position:absolute;left:{p}%;top:-30px;width:1.5px;height:{h}px;'
        f'background:linear-gradient(to bottom,transparent,rgba(147,197,253,.55));'
        f'border-radius:1px;animation:_rfall {d}s linear {dl}s infinite"></span>'
        for p, h, d, dl in [
            (5,  20, 1.1, 0.0), (12, 26, 1.4, 0.3), (20, 18, 1.0, 0.6),
            (30, 23, 1.3, 0.1), (39, 29, 1.2, 0.5), (49, 21, 1.0, 0.8),
            (58, 25, 1.4, 0.2), (67, 19, 1.1, 0.4), (77, 27, 1.3, 0.0),
            (86, 22, 1.0, 0.7), (93, 17, 1.2, 0.3),
        ]
    )
    return (
        "<style>@keyframes _rfall{"
        "0%{top:-30px;opacity:0}8%{opacity:.6}92%{opacity:.35}100%{top:140px;opacity:0}"
        "}</style>" + drops
    )


def _snow_flakes_html() -> str:
    flakes = "".join(
        f'<span style="position:absolute;left:{p}%;top:-20px;font-size:{s}px;'
        f'color:rgba(224,242,254,.8);animation:_sfall {d}s linear {dl}s infinite">❄</span>'
        for p, s, d, dl in [
            (8,14,3.0,0.0),(22,11,3.6,0.6),(38,16,2.8,1.1),
            (54,12,3.3,0.3),(70,15,3.0,0.9),(85,13,2.9,0.2),
        ]
    )
    return (
        "<style>@keyframes _sfall{"
        "0%{top:-20px;opacity:0}10%{opacity:.9}90%{opacity:.55}"
        "100%{top:140px;transform:translateX(12px);opacity:0}"
        "}</style>" + flakes
    )


_WEATHER_ADVICE: dict[str, list[str]] = {
    "thunderstorm": [
        "Stay inside and stay safe! ⚡",
        "Thunder and lightning — best to stay indoors today.",
        "Severe weather — avoid going outside if you can.",
    ],
    "drizzle": [
        "A light jacket and small umbrella should do!",
        "Just a sprinkle — but better safe than sorry.",
        "Light drizzle — don't forget a rain jacket.",
    ],
    "rain": [
        "Don't forget your umbrella! ☂️",
        "Stay dry today — grab a raincoat.",
        "Perfect day to stay cozy inside with a hot drink.",
        "It's going to be wet out there — dress accordingly.",
    ],
    "snow": [
        "Bundle up warm! ❄️",
        "Roads may be icy — drive carefully.",
        "Dress in layers and watch your step outside.",
        "Snow day! Don't forget gloves and a warm hat.",
    ],
    "mist": [
        "Reduced visibility — give extra space on the road.",
        "Misty morning — take it slow out there.",
    ],
    "fog": [
        "Dense fog — allow extra travel time.",
        "Foggy conditions — headlights on and drive carefully.",
    ],
    "haze": [
        "Hazy skies — stay hydrated and protect your eyes.",
        "Air quality may be affected — sensitive groups take care.",
    ],
    "smoke": [
        "Smoky air — consider staying indoors.",
        "Poor air quality — an N95 mask may help outdoors.",
    ],
    "clear": [
        "Great day for a walk! ☀️",
        "Perfect conditions for outdoor activities!",
        "Don't forget sunscreen — UV index may be high.",
        "Beautiful weather — enjoy the sunshine!",
        "Ideal day to spend time outdoors.",
    ],
    "cloud": [
        "Light layers recommended today.",
        "Overcast but comfortable — good for a stroll.",
        "Cloudy skies — no umbrella needed just yet.",
        "A mild day, perfect for outdoor activities.",
    ],
}


def _weather_advice_random(main: str) -> str:
    """Return a random piece of advice matching the weather condition."""
    m = main.lower()
    for key, advices in _WEATHER_ADVICE.items():
        if key in m:
            return random.choice(advices)
    return "Have a great day! 🌈"


def _forecast_widget(api_base: str) -> None:
    """Fetch the 5-day forecast from the cloud API and render day cards."""
    _now = time.time()
    _FORECAST_TTL = 600  # 10 minutes — same as outdoor cache
    if (
        "forecast_cache" not in st.session_state
        or _now - st.session_state.get("forecast_ts", 0) >= _FORECAST_TTL
    ):
        try:
            r = requests.get(
                f"{api_base}/v1/weather/forecast",
                params={"days": 5},
                timeout=10,
            )
            r.raise_for_status()
            st.session_state.forecast_cache = r.json().get("forecast", {}).get("daily", [])
            st.session_state.forecast_ts    = _now
        except Exception:
            st.session_state.forecast_cache = []
            st.session_state.forecast_ts    = _now

    daily = st.session_state.get("forecast_cache", [])
    if not daily:
        return

    from datetime import datetime as _dt
    _section_label("📅 5-Day Forecast")
    cols = st.columns(len(daily))
    for i, (col, day) in enumerate(zip(cols, daily)):
        date_str = day.get("date", "")
        try:
            day_label = "Today" if i == 0 else _dt.strptime(date_str, "%Y-%m-%d").strftime("%A")
        except Exception:
            day_label = date_str[-5:] if date_str else "?"

        main  = day.get("weather_main") or ""
        desc  = (day.get("weather_description") or main).capitalize()
        tmin  = day.get("temp_min_c")
        tmax  = day.get("temp_max_c")
        emoji = _weather_emoji(main, "2.2rem")
        _, border = _banner_bg(main)
        tmax_s = f"{tmax:.0f}°C" if tmax is not None else "--"
        tmin_s = f"{tmin:.0f}°C" if tmin is not None else "--"

        with col:
            st.markdown(f"""
<div style="background:rgba(30,41,59,0.55);border:1px solid {border};
            border-radius:14px;padding:16px 10px;text-align:center;height:100%">
  <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
              color:#64748B;font-weight:700;margin-bottom:8px">{day_label}</div>
  <div style="margin-bottom:9px;line-height:1">{emoji}</div>
  <div style="font-size:.74rem;color:#94A3B8;margin-bottom:10px;
              min-height:2.6em;line-height:1.3">{desc}</div>
  <div style="font-size:.95rem;font-weight:800;color:#F1F5F9">{tmax_s}</div>
  <div style="font-size:.78rem;color:#64748B;margin-top:1px">{tmin_s}</div>
</div>""", unsafe_allow_html=True)


def _weather_banner(row, advice: str = "") -> None:
    try:
        main = str(row["weather_main"] or "Clear")
        desc = str(row["weather_description"] or main).capitalize()
        temp = row["temperature_c"]
        hum  = row["humidity_pct"]
    except Exception:
        return

    bg, border  = _banner_bg(main)
    big_emoji   = _weather_emoji(main, "4rem")
    creature    = _creature_html(main)

    particles = ""
    ml = main.lower()
    if any(w in ml for w in ["rain", "drizzle", "thunderstorm"]):
        particles = _rain_drops_html()
    elif "snow" in ml:
        particles = _snow_flakes_html()

    temp_str   = f"{temp:.1f}°C" if temp is not None else "--°C"
    hum_str    = f"{hum:.0f} %"  if hum is not None else "-- %"
    advice_html = (
        f'<div style="font-size:.82rem;color:#7DD3FC;margin-top:6px;font-style:italic">'
        f'{advice}</div>'
    ) if advice else ""

    st.markdown(f"""
<div style="position:relative;overflow:hidden;border-radius:20px;
            background:{bg};border:1px solid {border};
            padding:22px 28px;margin-bottom:12px;
            display:flex;align-items:center;gap:20px;min-height:110px;">
  {particles}
  <div style="position:relative;z-index:1">{big_emoji}</div>
  <div style="position:relative;z-index:1;flex:1">
    <div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;
                color:#64748B;font-weight:700;margin-bottom:5px">
      🌍 Lausanne, CH · Outdoor
    </div>
    <div style="font-size:1.35rem;font-weight:800;color:#F1F5F9">{desc}</div>
    <div style="font-size:.85rem;color:#94A3B8;margin-top:3px">
      Humidity {hum_str}
    </div>
    {advice_html}
  </div>
  <div style="position:relative;z-index:1;margin:0 10px">{creature}</div>
  <div style="position:relative;z-index:1;
              font-size:2.8rem;font-weight:800;color:#38BDF8;
              text-shadow:0 0 22px rgba(56,189,248,.35)">{temp_str}</div>
</div>
""", unsafe_allow_html=True)


def _page_header(icon_html: str, title: str, subtitle: str = "") -> None:
    sub = f'<div style="font-size:.85rem;color:#64748B;margin-top:4px">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
<div style="margin-bottom:22px;padding-bottom:14px;border-bottom:1px solid rgba(148,163,184,0.07)">
  <div style="font-size:1.75rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.02em;
              display:flex;align-items:center;gap:10px">
    {icon_html} {title}
  </div>
  {sub}
</div>""", unsafe_allow_html=True)


def _section_label(text: str) -> None:
    st.markdown(
        f'<div style="font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;'
        f'color:#94A3B8;font-weight:700;margin:18px 0 10px 0">{text}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# API HELPERS
# ============================================================

def _api_stt(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    r = requests.post(
        f"{API_BASE}/v1/stt",
        json={"audio_base64": audio_b64, "mime_type": mime_type, "language": "en"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("text", "")


def _api_qa(device_id: str, question: str) -> str:
    r = requests.post(
        f"{API_BASE}/v1/qa",
        json={"device_id": device_id, "question": question},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("answer", "")


def _api_tts(text: str) -> bytes | None:
    r = requests.post(
        f"{API_BASE}/v1/tts",
        json={"text": text, "voice": "alloy", "audio_format": "wav"},
        timeout=30,
    )
    r.raise_for_status()
    audio_b64 = r.json().get("audio_base64", "")
    return base64.b64decode(audio_b64) if audio_b64 else None


def _mic_button_widget(dev_id: str, compact: bool = False) -> str:
    """Click-to-record voice QA widget — no PIR dependency."""
    answer_css  = "" if compact else """
#ans{margin-top:8px;padding:10px 14px;background:rgba(74,222,128,.07);
  border-left:3px solid #4ADE80;border-radius:8px;font-size:.84em;
  color:#86EFAC;display:none;word-wrap:break-word;line-height:1.45}"""
    answer_html = "" if compact else '<div id="ans"></div>'
    ans_js      = "null" if compact else "document.getElementById('ans')"

    return f"""<!DOCTYPE html><html><head><style>
*{{box-sizing:border-box}}
body{{margin:0;padding:6px 8px;background:transparent;font-family:sans-serif;color:#fff}}
#btn{{width:100%;padding:9px 16px;background:rgba(56,189,248,.1);color:#7DD3FC;
  border:1px solid rgba(56,189,248,.28);border-radius:10px;cursor:pointer;
  font-size:.92em;font-weight:600;transition:all .15s}}
#btn:hover:not(:disabled){{background:rgba(56,189,248,.2)}}
#btn.rec{{background:rgba(220,38,38,.18);color:#FCA5A5;
  border-color:rgba(220,38,38,.4);animation:pulse .9s infinite}}
#btn.proc{{background:rgba(234,179,8,.1);color:#FDE68A;
  border-color:rgba(234,179,8,.3);cursor:default}}
#st{{font-size:.78em;color:#94A3B8;margin-top:5px;min-height:16px}}
{answer_css}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
</style></head><body>
<button id="btn" onclick="toggle()">🎙️ Start recording</button>
<div id="st">Click to record your question</div>
{answer_html}
<script>
const API="{API_BASE}",DEV="{dev_id}";
const btn=document.getElementById("btn"),st=document.getElementById("st");
const ans={ans_js};
let stream=null,rec=null,chunks=[],recording=false,busy=false;

async function toggle(){{
  if(busy)return;
  if(!recording)await startRec();else stopRec();
}}
async function startRec(){{
  if(!stream){{
    try{{stream=await navigator.mediaDevices.getUserMedia({{audio:true}})}}
    catch(e){{st.textContent="Mic denied: "+e.message;return}}
  }}
  chunks=[];rec=new MediaRecorder(stream);
  rec.ondataavailable=e=>{{if(e.data.size>0)chunks.push(e.data)}};
  rec.onstop=process;rec.start(100);recording=true;
  btn.textContent="⏹ Stop & send";btn.className="rec";
  st.textContent="Recording… click stop when done";
  if(ans)ans.style.display="none";
}}
function stopRec(){{
  if(rec&&rec.state!=="inactive")rec.stop();
  recording=false;busy=true;
  btn.textContent="⚙️ Processing…";btn.className="proc";
  st.textContent="Transcribing…";
}}
async function process(){{
  const mime=rec.mimeType||"audio/webm";
  const blob=new Blob(chunks,{{type:mime}});
  const b64=await blobToB64(blob);
  try{{
    const stt=await post(`${{API}}/v1/stt`,{{audio_base64:b64,mime_type:mime,language:"en"}});
    const txt=stt.text||"";
    if(!txt){{setErr("Nothing heard — try again");return}}
    st.textContent="🗣️ "+txt;
    btn.textContent="🤔 Thinking…";btn.className="proc";
    const qa=await post(`${{API}}/v1/qa`,{{device_id:DEV,question:txt}});
    const answer=qa.answer||"";
    if(ans){{ans.textContent="💬 "+answer;ans.style.display="block"}}
    post(`${{API}}/v1/device/${{DEV}}/answer`,{{answer}}).catch(()=>{{}});
    btn.textContent="🔊 Speaking…";
    const tts=await post(`${{API}}/v1/tts`,{{text:answer,voice:"alloy",audio_format:"mp3"}});
    if(tts.audio_base64)new Audio("data:audio/mp3;base64,"+tts.audio_base64).play();
  }}catch(e){{setErr(e.message);return}}
  btn.textContent="🎙️ Start recording";btn.className="";busy=false;
}}
function setErr(m){{
  st.textContent="❌ "+m;
  btn.textContent="🎙️ Start recording";btn.className="";busy=false;
}}
function blobToB64(b){{return new Promise(r=>{{const fr=new FileReader();
  fr.onloadend=()=>r(fr.result.split(",")[1]);fr.readAsDataURL(b)}})}}
async function post(url,body){{const r=await fetch(url,{{method:"POST",
  headers:{{"Content-Type":"application/json"}},body:JSON.stringify(body)}});
  if(!r.ok)throw new Error(r.status+" "+r.statusText);return r.json()}}
</script></body></html>"""


def _run_qa_flow(question: str, device_id: str, push_to_device: bool = False) -> None:
    with st.spinner("Asking the assistant…"):
        try:
            answer = _api_qa(device_id, question)
        except Exception as e:
            st.error(f"QA error: {e}")
            return

    st.success(f"**Answer:** {answer}")

    if push_to_device:
        try:
            requests.post(
                f"{API_BASE}/v1/device/{device_id}/answer",
                json={"answer": answer},
                timeout=5,
            )
        except Exception:
            pass

    with st.spinner("Generating audio response…"):
        try:
            audio_bytes = _api_tts(answer)
        except Exception as e:
            st.warning(f"TTS unavailable: {e}")
            return

    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav", autoplay=True)


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("""
<div style="padding:6px 0 18px 0">
  <div style="font-size:1.35rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.02em">
    🌤️ Weather Monitor
  </div>
  <div style="font-size:.75rem;color:#64748B;margin-top:3px">Cloud IoT Dashboard</div>
</div>
""", unsafe_allow_html=True)

device_id    = st.sidebar.selectbox("Device", ["core2-main", "core2-alex"])
history_days = st.sidebar.slider("History (days)", min_value=1, max_value=30, value=7)
page         = st.sidebar.radio(
    "Navigation",
    ["📡 Realtime", "📈 History", "🔔 Events", "🎙️ Voice QA"],
    label_visibility="collapsed",
)
st.sidebar.markdown(
    f'<div style="font-size:.68rem;color:#334155;margin-top:8px;word-break:break-all">'
    f'API: {API_BASE[:45]}…</div>',
    unsafe_allow_html=True,
)


# ============================================================
# GLOBAL ALERT BANNER (visible on every page)
# Always queries latest indoor data — autorefresh controls frequency.
# ============================================================
st_autorefresh(interval=30_000, key="global_alert_refresh")

_adf  = latest_indoor(device_id)
_alert_msgs: list[str] = []
if not _adf.empty:
    _ar   = _adf.iloc[0]
    _ah   = _ar.get("humidity_pct")
    _atvoc = int(_ar.get("tvoc_ppb") or 0)
    _aeco2 = int(_ar.get("eco2_ppm") or 0)
    if _ah is not None and float(_ah) < 40:
        _alert_msgs.append("💧 Low humidity — use a humidifier")
    if _atvoc > 500:
        _alert_msgs.append("🌿 Poor air quality (TVOC)")
    if _aeco2 > 1000:
        _alert_msgs.append("💨 High CO₂ — ventilate the room")

_prev_alert = st.session_state.get("prev_global_alert", False)
_has_alert  = len(_alert_msgs) > 0

if _has_alert:
    _msgs_html = " &nbsp;·&nbsp; ".join(_alert_msgs)
    st.markdown(f"""
<div style="background:linear-gradient(90deg,rgba(220,38,38,.82),rgba(153,27,27,.82));
            border:1px solid rgba(248,113,113,.35);border-radius:14px;
            padding:13px 22px;margin-bottom:18px;
            display:flex;align-items:center;gap:14px;backdrop-filter:blur(8px)">
  <span style="font-size:1.5rem;animation:bell-ring 3.5s ease-in-out infinite;
               display:inline-block;transform-origin:top center">🔔</span>
  <div>
    <div style="font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;
                color:rgba(252,165,165,.75);font-weight:700">Indoor Alert</div>
    <div style="font-size:.92rem;font-weight:700;color:#FCA5A5">{_msgs_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)
    # Play alarm sound only on transition (no-alert → alert)
    if not _prev_alert:
        components.html("""<script>
(function() {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    function beep(t) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = 'square'; o.frequency.value = 880;
      g.gain.setValueAtTime(0.22, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.4);
      o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.45);
    }
    beep(0); beep(0.6); beep(1.2);
  } catch(e) { console.warn('Alert sound blocked by browser policy:', e); }
})();
</script>""", height=0)
    st.session_state.prev_global_alert = True
else:
    st.session_state.prev_global_alert = False


# ============================================================
# PAGE: REALTIME
# ============================================================
if page == "📡 Realtime":
    st_autorefresh(interval=5_000, key="realtime_refresh")
    # Outdoor cached 10 min (full page rerun only)
    _now = time.time()
    _OUTDOOR_TTL = 600
    if (
        "outdoor_cache" not in st.session_state
        or "outdoor_ts" not in st.session_state
        or _now - st.session_state.outdoor_ts >= _OUTDOOR_TTL
    ):
        st.session_state.outdoor_cache = latest_outdoor()
        st.session_state.outdoor_ts    = _now
        _m0 = (
            str(st.session_state.outdoor_cache.iloc[0]["weather_main"])
            if not st.session_state.outdoor_cache.empty else ""
        )
        st.session_state.outdoor_advice = _weather_advice_random(_m0)

    outdoor = st.session_state.outdoor_cache
    if not outdoor.empty:
        _weather_banner(outdoor.iloc[0], advice=st.session_state.get("outdoor_advice", ""))

    # ── Live metrics fragment: indoor re-fetched every 3 s ───
    @st.fragment(run_every=3)
    def _live_metrics():
        indoor  = latest_indoor(device_id)
        _outdoor = st.session_state.get("outdoor_cache", None)

        col_in, col_out = st.columns(2, gap="large")

        # Indoor
        with col_in:
            if indoor is None or indoor.empty:
                st.warning("No indoor data yet.")
            else:
                row = indoor.iloc[0]
                _section_label(f"🏠 Indoor · {_fmt_ts(row['event_ts'])}")
                c1, c2 = st.columns(2)
                t    = row["temperature_c"]
                h    = row["humidity_pct"]
                tvoc = int(row["tvoc_ppb"]) if row["tvoc_ppb"] is not None else None
                eco2 = int(row["eco2_ppm"]) if row["eco2_ppm"] is not None else None
                c1.metric("🌡️ Temperature", f"{t:.1f} °C" if t is not None else "n/a")
                c2.metric("💧 Humidity",    f"{h:.0f} %"  if h is not None else "n/a")
                c3, c4 = st.columns(2)
                c3.metric("🌿 TVOC",  f"{tvoc} ppb" if tvoc is not None else "n/a")
                c4.metric("💨 eCO₂",  f"{eco2} ppm" if eco2 is not None else "n/a")
                badges = []
                if h is not None and h < 40:
                    badges.append(('rgba(248,113,113,.13)', '#FCA5A5', 'rgba(248,113,113,.3)', '⚠️ Low humidity — use a humidifier'))
                if tvoc is not None and tvoc > 500:
                    badges.append(('rgba(248,113,113,.13)', '#FCA5A5', 'rgba(248,113,113,.3)', '⚠️ Poor air quality (TVOC)'))
                if eco2 is not None and eco2 > 1000:
                    badges.append(('rgba(250,204,21,.13)',  '#FDE68A', 'rgba(250,204,21,.3)',  '⚠️ High CO₂ — ventilate'))
                if badges:
                    html = "".join(
                        f'<span style="display:inline-block;margin:3px;padding:5px 13px;'
                        f'border-radius:999px;font-size:.8rem;font-weight:600;'
                        f'background:{bg};color:{fg};border:1px solid {bd}">{txt}</span>'
                        for bg, fg, bd, txt in badges
                    )
                    st.markdown(f'<div style="margin-top:12px">{html}</div>', unsafe_allow_html=True)

        # Outdoor (from cache)
        with col_out:
            if _outdoor is None or _outdoor.empty:
                st.warning("No outdoor data yet.")
            else:
                row = _outdoor.iloc[0]
                _section_label(f"🌍 Outdoor · {_fmt_ts(row['weather_ts'])}")
                c1, c2 = st.columns(2)
                c1.metric("🌡️ Temperature", f"{row['temperature_c']:.1f} °C")
                c2.metric("💧 Humidity",    f"{row['humidity_pct']:.0f} %")
                main  = str(row["weather_main"] or "")
                desc  = str(row["weather_description"] or main).capitalize()
                big_w = _weather_emoji(main, "3.8rem")
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:16px;margin-top:14px;
            background:rgba(30,41,59,0.5);border:1px solid rgba(148,163,184,0.1);
            border-radius:14px;padding:16px 20px">
  {big_w}
  <div>
    <div style="font-size:1.1rem;font-weight:700;color:#E2E8F0">{main}</div>
    <div style="font-size:.87rem;color:#94A3B8;margin-top:3px">{desc}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    _live_metrics()

    # 5-day forecast cards (full width, below indoor/outdoor columns)
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    _forecast_widget(API_BASE)


# ============================================================
# PAGE: HISTORY
# ============================================================
elif page == "📈 History":
    _page_header(
        '<span class="chart-anim">📈</span>',
        "Historical Trends",
        f'Last {history_days} day(s) · device '
        f'<code style="background:#1E293B;padding:2px 7px;border-radius:5px;'
        f'color:#38BDF8;font-size:.82rem">{device_id}</code>',
    )

    history = indoor_history(device_id=device_id, days=history_days)
    if history.empty:
        st.warning("No historical data for this period.")
    else:
        line_chart(history, "event_ts", "temperature_c", "🌡️ Indoor Temperature", "°C")
        line_chart(history, "event_ts", "humidity_pct",  "💧 Indoor Humidity",     "%")
        line_chart(history, "event_ts", "eco2_ppm",      "💨 Indoor eCO₂",         "ppm")
        line_chart(history, "event_ts", "tvoc_ppb",      "🌿 Indoor TVOC",         "ppb")


# ============================================================
# PAGE: EVENTS
# ============================================================
elif page == "🔔 Events":
    st_autorefresh(interval=10_000, key="events_refresh")
    _page_header(
        '<span class="bell-anim">🔔</span>',
        "Alerts & Events",
        f'Device <code style="background:#1E293B;padding:2px 7px;border-radius:5px;'
        f'color:#38BDF8;font-size:.82rem">{device_id}</code>',
    )

    events = recent_events(device_id=device_id, limit=100)
    if events.empty:
        st.info("No events recorded yet.")
    else:
        _SEV = {
            "critical": ("rgba(248,113,113,.1)", "#FCA5A5", "rgba(248,113,113,.28)", "🔴"),
            "warning":  ("rgba(250,204,21,.1)",  "#FDE68A", "rgba(250,204,21,.28)",  "🟡"),
            "info":     ("rgba(56,189,248,.09)", "#93C5FD", "rgba(56,189,248,.25)",  "🔵"),
        }
        for _, ev in events.iterrows():
            sev             = str(ev.get("severity", "info")).lower()
            bg, fg, bd, dot = _SEV.get(sev, _SEV["info"])
            ts              = _fmt_ts(ev["event_ts"])
            etype           = str(ev.get("event_type", ""))
            msg             = str(ev.get("message", ""))
            st.markdown(f"""
<div style="display:flex;align-items:flex-start;gap:14px;padding:12px 16px;
            margin-bottom:6px;background:{bg};border:1px solid {bd};border-radius:12px;">
  <span style="font-size:.95rem;margin-top:2px">{dot}</span>
  <div style="flex:1;min-width:0">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <span style="font-size:.83rem;font-weight:700;color:{fg}">{etype}</span>
      <span style="font-size:.73rem;color:#64748B;white-space:nowrap">{ts}</span>
    </div>
    <div style="font-size:.84rem;color:#94A3B8;margin-top:3px;
                overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{msg}</div>
  </div>
</div>""", unsafe_allow_html=True)


# ============================================================
# PAGE: VOICE QA
# ============================================================
elif page == "🎙️ Voice QA":
    _page_header(
        '<span class="mic-anim">🎙️</span>',
        "Voice Assistant",
        "Click the button, ask your question, get a spoken answer",
    )

    _section_label("🎙️ Microphone")
    components.html(_mic_button_widget(device_id, compact=False), height=200)

    st.divider()

    _section_label("⌨️ Ask by text")
    typed_q = st.text_input(
        "Your question",
        placeholder="e.g. What is the forecast for tomorrow?",
        key="text_question",
        label_visibility="collapsed",
    )
    if st.button("Ask ›", key="ask_text") and typed_q.strip():
        _run_qa_flow(typed_q.strip(), device_id, push_to_device=True)

    st.divider()

    _section_label("⚡ Quick questions")
    presets = [
        "What was the temperature at home yesterday?",
        "Did humidity exceed 50% yesterday?",
        "Brief weather update and advice.",
        "What is the current indoor air quality?",
    ]
    cols = st.columns(2)
    for i, q in enumerate(presets):
        if cols[i % 2].button(q, key=f"preset_{i}", use_container_width=True):
            st.markdown(
                f'<div style="font-size:.83rem;color:#64748B;margin:4px 0 8px 0">'
                f'Asking: <em style="color:#94A3B8">{q}</em></div>',
                unsafe_allow_html=True,
            )
            _run_qa_flow(q, device_id, push_to_device=True)
