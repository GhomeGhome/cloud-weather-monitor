# ============================================================
# test_mic.py — Core2 microphone I2S test
# Flash this instead of core2_main.py to diagnose mic support.
# Results shown line by line on screen.
# ============================================================

from m5stack import *
from m5stack_ui import *
from uiflow import *
import time

screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0x000000)

C_OK  = 0x00FF7F
C_ERR = 0xFF4444
C_INF = 0xFFFF00

# 10 fixed label rows
_rows = []
for i in range(11):
    _rows.append(M5Label('', x=5, y=4 + i * 20, color=C_INF, font=FONT_MONT_10, parent=None))

_row_idx = 0

def log(msg, color=C_INF):
    global _row_idx
    if _row_idx < len(_rows):
        _rows[_row_idx].set_text(str(msg)[:42])
        _rows[_row_idx].set_text_color(color)
        _row_idx += 1

# ---- TEST 1 : import machine.I2S ----
try:
    from machine import I2S, Pin
    log('1) I2S: importable OK', C_OK)
except Exception as e:
    log('1) I2S import FAIL:', C_ERR)
    log('   ' + str(e)[:38], C_ERR)
    log('=> machine.I2S not in firmware', C_ERR)
    log('Flash stopped.', C_ERR)
    raise SystemExit

# ---- TEST 2 : I2S constants ----
try:
    log('2) I2S.RX  = ' + str(I2S.RX),   C_INF)
    log('   I2S.MONO= ' + str(getattr(I2S, 'MONO', 'N/A')), C_INF)
except Exception as e:
    log('2) constants: ' + str(e)[:28], C_ERR)

# ---- TEST 3 : init I2S (Core2 mic pins: SCK=12, WS=0, SD=34) ----
i2s = None
try:
    fmt = getattr(I2S, 'MONO', getattr(I2S, 'LEFT', 0))
    i2s = I2S(
        0,
        sck=Pin(12),
        ws=Pin(0),
        sd=Pin(34),
        mode=I2S.RX,
        bits=16,
        format=fmt,
        rate=16000,
        ibuf=8000,
    )
    log('3) I2S init: OK', C_OK)
except Exception as e:
    log('3) I2S init FAIL:', C_ERR)
    log('   ' + str(e)[:38], C_ERR)
    raise SystemExit

# ---- TEST 4 : record ~0.5s (16kHz 16-bit mono = 16000 samples/s) ----
try:
    buf = bytearray(16000)   # 0.5 s worth of samples
    log('4) Recording 0.5s...', C_INF)
    n = i2s.readinto(buf)
    i2s.deinit()
    nonzero = sum(1 for b in buf[:200] if b != 0)
    log('   {} bytes read'.format(n), C_OK)
    log('   non-zero bytes (of 200): {}'.format(nonzero),
        C_OK if nonzero > 10 else 0xFFA500)
    if nonzero > 10:
        log('=> MIC WORKS! Audio data OK', C_OK)
    else:
        log('=> Got zeros - check pins?', 0xFFA500)
except Exception as e:
    log('4) Record FAIL:', C_ERR)
    log('   ' + str(e)[:38], C_ERR)
