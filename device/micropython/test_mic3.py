# ============================================================
# test_mic3.py — Check if question.wav survived reboot + test speaker
# Flash AFTER test_mic2.py has already run and rebooted.
# ============================================================

from m5stack import *
from m5stack_ui import *
from uiflow import *
import utime
import uos

screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0x000000)

C_OK  = 0x00FF7F
C_ERR = 0xFF4444
C_INF = 0xFFFF00
C_CYN = 0x00FFFF

_rows = []
for i in range(12):
    _rows.append(M5Label('', x=5, y=4 + i * 19, color=C_INF,
                         font=FONT_MONT_10, parent=None))
_ri = [0]

def log(msg, color=C_INF):
    if _ri[0] < len(_rows):
        _rows[_ri[0]].set_text(str(msg)[:42])
        _rows[_ri[0]].set_text_color(color)
        _ri[0] += 1

# ---- Check what's in /flash/ ----
log('Files in /flash/:', C_CYN)
try:
    files = uos.listdir('/flash')
    wavs = [f for f in files if f.endswith('.wav')]
    if wavs:
        for w in wavs:
            sz = uos.stat('/flash/' + w)[6]
            log('  {} : {} bytes'.format(w, sz),
                C_OK if sz > 10000 else C_ERR)
    else:
        log('  No .wav files found', C_ERR)
        log('  (test_mic2 may not have', C_INF)
        log('   saved before reboot)', C_INF)
except Exception as e:
    log('listdir error: ' + str(e)[:30], C_ERR)

# ---- Test speaker ----
log('', C_INF)
log('Press BTN A: play question.wav', C_CYN)
log('Press BTN B: play test tone', C_CYN)

while True:
    if btnA.wasPressed():
        try:
            sz = uos.stat('/flash/question.wav')[6]
            log('Playing question.wav ({})...'.format(sz), C_INF)
            speaker.setVolume(8)
            speaker.playWAV('/flash/question.wav')
            log('Playback done!', C_OK)
        except Exception as e:
            log('Play FAIL: ' + str(e)[:32], C_ERR)

    if btnB.wasPressed():
        try:
            log('Playing test tone...', C_INF)
            speaker.setVolume(8)
            speaker.tone(440, 500)
            log('Tone OK', C_OK)
        except Exception as e:
            log('Tone FAIL: ' + str(e)[:32], C_ERR)

    utime.sleep_ms(100)
