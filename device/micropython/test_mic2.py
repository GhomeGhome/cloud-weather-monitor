# ============================================================
# test_mic2.py — MicrophonePDM record + speaker playback test
# Flash this instead of core2_main.py.
# Press Button A to start recording (4s), then it tries playback.
# ============================================================

from m5stack import *
from m5stack_ui import *
from uiflow import *
import utime
import MicrophonePDM as MIC

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

def file_size(path):
    try:
        import uos
        return uos.stat(path)[6]
    except:
        return -1

log('Press BTN A to record 4s', C_CYN)
log('(then auto-plays back)', C_CYN)

while True:
    if btnA.wasPressed():
        # clear screen
        for r in _rows:
            r.set_text('')
        _ri[0] = 0

        # ---- STEP 1: init mic ----
        try:
            MIC.begin(
                pin_ws=0,
                pin_data=34,
                sample_rate_hz=16000,
                buffer_length_ms=1000,
                block_length_ms=100,
            )
            log('1) MIC.begin: OK', C_OK)
        except Exception as e:
            log('1) MIC.begin FAIL:', C_ERR)
            log('   ' + str(e)[:38], C_ERR)
            break

        # ---- STEP 2: record 4s to /flash/ ----
        try:
            log('2) Recording 4s...', C_INF)
            f = open('/flash/question.wav', 'wb')
            MIC.recordStart(f, 4000)
            MIC.waitDone(6000)
            f.close()
            sz = file_size('/flash/question.wav')
            log('   file size: {} bytes'.format(sz),
                C_OK if sz > 1000 else C_ERR)
            if sz < 1000:
                log('   WARNING: file too small', C_ERR)
        except Exception as e:
            log('2) Record FAIL:', C_ERR)
            log('   ' + str(e)[:38], C_ERR)
            break

        # ---- STEP 3: deinit mic ----
        try:
            MIC.deinit(3000)
            log('3) MIC.deinit: OK', C_OK)
        except Exception as e:
            log('3) MIC.deinit: ' + str(e)[:28], C_ERR)

        # ---- STEP 4: play back without reboot ----
        try:
            utime.sleep_ms(300)
            speaker.setVolume(8)
            speaker.playWAV('/flash/question.wav')
            log('4) Playback: OK (no reboot!)', C_OK)
        except Exception as e:
            log('4) Playback FAIL:', C_ERR)
            log('   ' + str(e)[:38], C_ERR)
            log('   => reboot needed', C_INF)

        log('Done. Press A to retry.', C_CYN)
        _ri[0] = min(_ri[0], len(_rows) - 1)

    utime.sleep_ms(100)
