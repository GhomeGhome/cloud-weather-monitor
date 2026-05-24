# ============================================================
# test_speaker.py — Inspect speaker object + try all known APIs
# Flash this to find out what works on this Core2 firmware.
# ============================================================

from m5stack import *
from m5stack_ui import *
from uiflow import *
import utime

screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0x000000)

C_OK  = 0x00FF7F
C_ERR = 0xFF4444
C_INF = 0xFFFF00
C_CYN = 0x00FFFF

_rows = []
for i in range(13):
    _rows.append(M5Label('', x=5, y=2 + i * 18, color=C_INF,
                         font=FONT_MONT_10, parent=None))
_ri = [0]

def log(msg, color=C_INF):
    if _ri[0] < len(_rows):
        _rows[_ri[0]].set_text(str(msg)[:42])
        _rows[_ri[0]].set_text_color(color)
        _ri[0] += 1

# ---- Show type ----
log('type: ' + str(type(speaker)), C_CYN)

# ---- Show all attributes ----
attrs = [a for a in dir(speaker) if not a.startswith('_')]
log('attrs (' + str(len(attrs)) + '):', C_CYN)
line = ''
for a in attrs:
    if len(line) + len(a) + 1 > 40:
        log('  ' + line, C_INF)
        line = a
    else:
        line = line + ' ' + a if line else a
if line:
    log('  ' + line, C_INF)

log('', C_INF)
log('BTN A: try tone/beep methods', C_CYN)
log('BTN B: try play methods', C_CYN)
log('BTN C: try setVolume', C_CYN)

while True:
    if btnA.wasPressed():
        for name in ['tone', 'beep', 'playTone', 'buzz', 'sing']:
            try:
                fn = getattr(speaker, name)
                fn(440, 300)
                log(name + ': OK!', C_OK)
            except AttributeError:
                log(name + ': no attr', C_ERR)
            except Exception as e:
                log(name + ': ' + str(e)[:28], C_ERR)
            utime.sleep_ms(400)

    if btnB.wasPressed():
        for name in ['playWAV', 'playWave', 'playMP3', 'play', 'playMusic',
                     'playRaw', 'playBytes']:
            try:
                fn = getattr(speaker, name)
                log(name + ': exists', C_OK)
            except AttributeError:
                log(name + ': no attr', C_ERR)

    if btnC.wasPressed():
        try:
            speaker.setVolume(6)
            log('setVolume: OK', C_OK)
        except Exception as e:
            log('setVolume: ' + str(e)[:28], C_ERR)
        try:
            speaker.volume = 6
            log('volume=: OK', C_OK)
        except Exception as e:
            log('volume=: ' + str(e)[:28], C_ERR)

    utime.sleep_ms(100)
