import base64
import os
from datetime import timezone, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components

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

/* ── Kill the white header bar ── */
header[data-testid="stHeader"],
[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1.5rem !important; }

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


def _weather_banner(row) -> None:
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

    temp_str = f"{temp:.1f}°C" if temp is not None else "--°C"
    hum_str  = f"{hum:.0f} %"  if hum is not None else "-- %"

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


def _pir_auto_widget(dev_id: str) -> str:
    return f"""<!DOCTYPE html><html><head><style>
*{{box-sizing:border-box}}
body{{margin:0;padding:6px 8px;background:transparent;font-family:sans-serif;color:#fff}}
#setup button{{padding:7px 16px;background:#4FC3F7;color:#000;border:none;border-radius:6px;
  cursor:pointer;font-size:.9em;font-weight:600}}
#setup span{{color:#94a3b8;font-size:.82em;margin-left:8px}}
#wrap{{display:none}}
#st{{padding:10px 14px;border-radius:8px;font-size:.93em;font-weight:600;margin-bottom:4px}}
#dt{{font-size:.8em;color:#94a3b8;padding:3px 6px;background:#111827;border-radius:5px;
  display:none;word-wrap:break-word}}
.idle{{background:#1e2130;color:#94a3b8}}
.rec {{background:#cc2200;color:#fff;animation:pulse .9s infinite}}
.proc{{background:#4d3800;color:#ffd}}
.done{{background:#004d1a;color:#0f9}}
.err {{background:#4d0000;color:#faa}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
</style></head><body>
<div id="setup">
  <button onclick="init()">🎙️ Enable microphone (PIR auto-recording)</button>
  <span>Click once — auto-records when PIR fires</span>
</div>
<div id="wrap">
  <div id="st" class="idle">⏳ Waiting for PIR motion…</div>
  <div id="dt"></div>
</div>
<script>
const API="{API_BASE}",DEV="{dev_id}";
let stream=null,rec=null,chunks=[],pir="off",busy=false;
function ss(m,c){{document.getElementById("st").textContent=m;document.getElementById("st").className=c}}
function sd(m){{const d=document.getElementById("dt");if(m){{d.textContent=m;d.style.display="block"}}else d.style.display="none"}}
async function init(){{
  try{{stream=await navigator.mediaDevices.getUserMedia({{audio:true}});
    document.getElementById("setup").style.display="none";
    document.getElementById("wrap").style.display="block";poll();
  }}catch(e){{alert("Microphone denied: "+e.message)}}
}}
async function poll(){{
  if(!busy){{try{{
    const r=await fetch(`${{API}}/v1/pir/state/${{DEV}}`);
    const d=await r.json();const s=d.state||"off";
    if(s==="on"&&pir!=="on"){{pir="on";startRec()}}
    else if(s==="off"&&pir==="on"){{pir="off";stopRec()}}
    else pir=s;
  }}catch(e){{}}}}
  setTimeout(poll,1000);
}}
function startRec(){{chunks=[];rec=new MediaRecorder(stream);
  rec.ondataavailable=e=>{{if(e.data.size>0)chunks.push(e.data)}};
  rec.onstop=process;rec.start(100);
  ss("🔴 Recording your question…","rec");sd("");}}
function stopRec(){{if(rec&&rec.state!=="inactive")rec.stop();ss("⚙️ Processing…","proc")}}
async function process(){{
  busy=true;const mime=rec.mimeType||"audio/webm";
  const blob=new Blob(chunks,{{type:mime}});const b64=await blobToB64(blob);
  try{{
    sd("Transcribing…");
    const stt=await post(`${{API}}/v1/stt`,{{audio_base64:b64,mime_type:mime,language:"en"}});
    const txt=stt.text||"";
    if(!txt){{ss("⚠️ Could not transcribe — try again","err");sd("");busy=false;return}}
    sd("🗣️ "+txt);
    ss("🤔 Getting answer…","proc");
    const qa=await post(`${{API}}/v1/qa`,{{device_id:DEV,question:txt}});
    const ans=qa.answer||"";
    ss("✅ "+ans,"done");sd("🗣️ "+txt);
    post(`${{API}}/v1/device/${{DEV}}/answer`,{{answer:ans}}).catch(()=>{{}});
    const tts=await post(`${{API}}/v1/tts`,{{text:ans,voice:"alloy",audio_format:"mp3"}});
    if(tts.audio_base64)new Audio("data:audio/mp3;base64,"+tts.audio_base64).play();
    setTimeout(()=>{{ss("⏳ Waiting for PIR motion…","idle");sd("")}},12000);
  }}catch(e){{ss("❌ "+e.message,"err");sd("")}}
  busy=false;
}}
function blobToB64(blob){{return new Promise(res=>{{const r=new FileReader();
  r.onloadend=()=>res(r.result.split(",")[1]);r.readAsDataURL(blob)}})}}
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

device_id    = st.sidebar.text_input("Device ID", value="core2-main")
history_days = st.sidebar.slider("History (days)", min_value=1, max_value=30, value=7)
page         = st.sidebar.radio(
    "Navigation",
    ["📡 Realtime", "📈 History", "🔔 Events", "🎙️ Voice QA"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
with st.sidebar.expander("🎙️ PIR Auto-Recording", expanded=True):
    components.html(_pir_auto_widget(device_id), height=100)
st.sidebar.markdown(
    f'<div style="font-size:.68rem;color:#334155;margin-top:8px;word-break:break-all">'
    f'API: {API_BASE[:45]}…</div>',
    unsafe_allow_html=True,
)


# ============================================================
# PAGE: REALTIME
# ============================================================
if page == "📡 Realtime":

    indoor  = latest_indoor(device_id)
    outdoor = latest_outdoor()

    # Animated weather banner (full width)
    if not outdoor.empty:
        _weather_banner(outdoor.iloc[0])

    col_in, col_out = st.columns(2, gap="large")

    # ── Indoor ──────────────────────────────────────────────
    with col_in:
        if indoor.empty:
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

            # Alert badges
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

    # ── Outdoor ─────────────────────────────────────────────
    with col_out:
        if outdoor.empty:
            st.warning("No outdoor data yet.")
        else:
            row = outdoor.iloc[0]
            _section_label(f"🌍 Outdoor · {_fmt_ts(row['weather_ts'])}")

            c1, c2 = st.columns(2)
            c1.metric("🌡️ Temperature", f"{row['temperature_c']:.1f} °C")
            c2.metric("💧 Humidity",    f"{row['humidity_pct']:.0f} %")

            main = str(row["weather_main"] or "")
            desc = str(row["weather_description"] or main).capitalize()
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
        "PIR sensor auto-starts recording on any page · enable the mic in the sidebar once",
    )

    qa_device = st.text_input("Device ID", value=device_id, key="qa_device_id")

    _section_label("📡 PIR Live Status")
    components.html(_pir_auto_widget(qa_device), height=110)

    st.divider()

    _section_label("⌨️ Ask by text")
    typed_q = st.text_input(
        "Your question",
        placeholder="e.g. What is the forecast for tomorrow?",
        key="text_question",
        label_visibility="collapsed",
    )
    if st.button("Ask ›", key="ask_text") and typed_q.strip():
        _run_qa_flow(typed_q.strip(), qa_device, push_to_device=True)

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
            _run_qa_flow(q, qa_device, push_to_device=True)
