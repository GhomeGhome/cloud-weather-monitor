import os, sys, io
import M5
from M5 import *
import m5ui
import lvgl as lv
from unit import ENVUnit
from hardware import Pin
from hardware import I2C
from unit import PIRUnit
from unit import TVOCUnit



Home = None
Forecast = None
WiFi = None
lbl_home_title = None
lbl_forecast_title = None
lbl_wifi_title = None
lbl_home_outdoor = None
lbl_forecast_subtitle = None
lbl_wifi_current_ap = None
lbl_home_clock = None
lbl_forecast_1 = None
lbl_wifi_ip = None
lbl_home_indoor_temp = None
lbl_forecast_2 = None
lbl_home_tvoc = None
lbl_forecast_3 = None
lbl_wifi_status = None
lbl_home_alert = None
lbl_forecast_updated = None
btn_wifi_refresh = None
lbl_home_icon = None
btn_forecast_refresh = None
btn_wifi_ssid_1 = None
lbl_home_motion = None
btn_forecast_wifi = None
btn_wifi_ssid_2 = None
btn_forecast_home = None
btn_wifi_forecast = None
btn_home_forecast = None
btn_wifi_home = None
btn_home_wifi = None
lbl_home_indoor_hum = None
lbl_home_eco2 = None
lbl_home_date = None
i2c0 = None
env3_0 = None
pir_1 = None
tvoc_0 = None


C_WIFI_1_SSID = None
C_WIFI_1_PASS = None
C_WIFI_2_SSID = None
C_WIFI_2_PASS = None

# Describe this function...
def refresh_wifi_info():
  global C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS, Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0
  global wlan_sta

  try:
      if wlan_sta.isconnected():
          lbl_wifi_current_ap.set_text("Connected AP: {}".format(wlan_sta.config('ssid')))
          lbl_wifi_ip.set_text("IP: {}".format(wlan_sta.ifconfig()[0]))
          lbl_wifi_status.set_text("Status: Connected")
      else:
          lbl_wifi_current_ap.set_text("Connected AP: --")
          lbl_wifi_ip.set_text("IP: --")
          lbl_wifi_status.set_text("Status: Disconnected")
  except Exception:
      lbl_wifi_current_ap.set_text("Connected AP: --")
      lbl_wifi_ip.set_text("IP: --")
      lbl_wifi_status.set_text("Status: Disconnected")

# Describe this function...
def refresh_outdoor():
  global C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS, Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0
  try:
      import json
      try:
          import urequests as requests
      except Exception:
          import requests

      # Endpoint qui a les données outdoor fraîches
      url = "https://weather-ingestion-api-972242315876.europe-west6.run.app/v1/weather/current"
      r = requests.get(url, timeout=8)

      if r.status_code != 200:
          lbl_home_outdoor.set_text("Outdoor: HTTP{}".format(r.status_code))
          try:
              r.close()
          except Exception:
              pass
      else:
          data = json.loads(r.text)

          # Format attendu:
          # { "status":"success", "weather": { "temperature_c": ... } }
          temp = None
          if isinstance(data, dict):
              weather = data.get("weather", {})
              if isinstance(weather, dict):
                  temp = weather.get("temperature_c", None)

          if temp is None:
              lbl_home_outdoor.set_text("Outdoor: no data")
          else:
              lbl_home_outdoor.set_text("Outdoor: {:.1f} C".format(float(temp)))

          try:
              r.close()
          except Exception:
              pass

  except Exception:
      lbl_home_outdoor.set_text("Outdoor: ERR")

# Describe this function...
def fetch_forecast():
  global C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS, Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0
  try:
      import json
      import time
      try:
          import urequests as requests
      except Exception:
          import requests

      url = "https://weather-ingestion-api-972242315876.europe-west6.run.app/v1/weather/forecast"
      r = requests.get(url, timeout=10)

      if r.status_code != 200:
          lbl_forecast_1.set_text("Day 1: HTTP{}".format(r.status_code))
          lbl_forecast_2.set_text("Day 2: --")
          lbl_forecast_3.set_text("Day 3: --")
          lbl_forecast_updated.set_text("Last update: HTTP error")
          try:
              r.close()
          except Exception:
              pass
      else:
          data = json.loads(r.text)
          fc = data.get("forecast", {}) if isinstance(data, dict) else {}
          daily = fc.get("daily", []) if isinstance(fc, dict) else []

          def line_for(i):
              if i >= len(daily):
                  return "Day {}: --".format(i + 1)

              row = daily[i]
              d = str(row.get("date", "--"))
              tmin = row.get("temp_min_c", None)
              tmax = row.get("temp_max_c", None)
              main = str(row.get("weather_main", "--"))

              # YYYY-MM-DD -> "22 May"
              date_txt = d
              try:
                  parts = d.split("-")
                  m = int(parts[1])
                  day = int(parts[2])
                  months = [
                      "January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"
                  ]
                  if 1 <= m <= 12:
                      date_txt = "{} {}".format(day, months[m - 1])
              except Exception:
                  pass

              if tmin is None or tmax is None:
                  return "{} : {} --/-- C".format(date_txt, main)

              return "{} : {} {:.0f}/{:.0f} C".format(date_txt, main, float(tmin), float(tmax))

          lbl_forecast_1.set_text(line_for(0))
          lbl_forecast_2.set_text(line_for(1))
          lbl_forecast_3.set_text(line_for(2))

          # Last update based on NTP-synced device clock + timezone offset
          try:
              offset = int(TZ_OFFSET_HOURS) * 3600
          except Exception:
              offset = 0

          tt = time.localtime(time.time() + offset)
          lbl_forecast_updated.set_text("Last update: {:02d}:{:02d}".format(tt[3], tt[4]))

          try:
              r.close()
          except Exception:
              pass

  except Exception:
      lbl_forecast_1.set_text("Day 1: ERR")
      lbl_forecast_2.set_text("Day 2: --")
      lbl_forecast_3.set_text("Day 3: --")
      lbl_forecast_updated.set_text("Last update: ERR")

# Describe this function...
def refresh_home_metrics():
  global C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS, Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0
  lbl_home_indoor_temp.set_text(str(env3_0.read_temperature()))
  lbl_home_indoor_hum.set_text(str(env3_0.read_humidity()))
  lbl_home_tvoc.set_text(str(tvoc_0.tvoc()))
  lbl_home_eco2.set_text(str(tvoc_0.co2eq()))
  lbl_home_motion.set_text(str(pir_1.get_status()))
  import time
  try:
      offset = int(TZ_OFFSET_HOURS) * 3600
  except Exception:
      offset = 0

  try:
      tt = time.localtime(time.time() + offset)
      lbl_home_clock.set_text("{:02d}:{:02d}:{:02d}".format(tt[3], tt[4], tt[5]))

      months = [
          "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"
      ]
      mname = months[tt[1] - 1] if 1 <= tt[1] <= 12 else "--"
      lbl_home_date.set_text("{} {}".format(tt[2], mname))  # e.g. 22 May
  except Exception:
      lbl_home_clock.set_text("--:--:--")
      lbl_home_date.set_text("--")

  # Alertes
  try:
      h = float(env3_0.read_humidity())
  except Exception:
      h = None

  try:
      tv = int(tvoc_0.tvoc())
  except Exception:
      tv = None

  try:
      eco2 = int(tvoc_0.co2eq())
  except Exception:
      eco2 = None

  alert = False
  if h is not None and h < 40:
      alert = True
  if tv is not None and tv > 500:
      alert = True
  if eco2 is not None and eco2 > 1200:
      alert = True

  lbl_home_alert.set_text("ALERT" if alert else "no alert")


def btn_wifi_ssid_1_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  import time
  ok = False

  if C_WIFI_1_SSID and C_WIFI_1_PASS:
      try:
          wlan_sta.disconnect()
      except Exception:
          pass

      time.sleep_ms(200)
      wlan_sta.connect(C_WIFI_1_SSID, C_WIFI_1_PASS)

      t0 = time.ticks_ms()
      while time.ticks_diff(time.ticks_ms(), t0) < 8000:
          if wlan_sta.isconnected():
              ok = True
              break
          time.sleep_ms(200)

  if ok:
      lbl_wifi_status.set_text("Connection done")
      try:
          lbl_wifi_current_ap.set_text("Connected AP: {}".format(wlan_sta.config('ssid')))
          lbl_wifi_ip.set_text("IP: {}".format(wlan_sta.ifconfig()[0]))
      except Exception:
          pass

      # NTP sync after successful WiFi connection
      try:
          sync_ntp()
      except Exception:
          pass
  else:
      lbl_wifi_status.set_text("Unable to connect")
  refresh_wifi_info()


def btn_wifi_ssid_2_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  import time
  ok = False

  if C_WIFI_2_SSID and C_WIFI_2_PASS:
      try:
          wlan_sta.disconnect()
      except Exception:
          pass

      time.sleep_ms(200)
      wlan_sta.connect(C_WIFI_2_SSID, C_WIFI_2_PASS)

      t0 = time.ticks_ms()
      while time.ticks_diff(time.ticks_ms(), t0) < 8000:
          if wlan_sta.isconnected():
              ok = True
              break
          time.sleep_ms(200)

  if ok:
      lbl_wifi_status.set_text("Connection done")
      try:
          lbl_wifi_current_ap.set_text("Connected AP: {}".format(wlan_sta.config('ssid')))
          lbl_wifi_ip.set_text("IP: {}".format(wlan_sta.ifconfig()[0]))
      except Exception:
          pass

      # NTP sync after successful WiFi connection
      try:
          sync_ntp()
      except Exception:
          pass
  else:
      lbl_wifi_status.set_text("Unable to connect")
  refresh_wifi_info()


def btn_home_forecast_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  fetch_forecast()
  Forecast.screen_load()


def btn_home_wifi_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  WiFi.screen_load()


def btn_forecast_refresh_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  fetch_forecast()


def btn_forecast_home_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  Home.screen_load()


def btn_forecast_wifi_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  WiFi.screen_load()


def btn_wifi_refresh_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  refresh_wifi_info()


def btn_wifi_home_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  Home.screen_load()


def btn_wifi_forecast_clicked_event(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  fetch_forecast()
  Forecast.screen_load()


def btn_wifi_ssid_1_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_wifi_ssid_1_clicked_event(event_struct)
  return

def btn_wifi_ssid_2_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_wifi_ssid_2_clicked_event(event_struct)
  return

def btn_home_forecast_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_home_forecast_clicked_event(event_struct)
  return

def btn_home_wifi_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_home_wifi_clicked_event(event_struct)
  return

def btn_forecast_refresh_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_forecast_refresh_clicked_event(event_struct)
  return

def btn_forecast_home_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_forecast_home_clicked_event(event_struct)
  return

def btn_forecast_wifi_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_forecast_wifi_clicked_event(event_struct)
  return

def btn_wifi_refresh_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_wifi_refresh_clicked_event(event_struct)
  return

def btn_wifi_home_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_wifi_home_clicked_event(event_struct)
  return

def btn_wifi_forecast_event_handler(event_struct):
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  event = event_struct.code
  if event == lv.EVENT.CLICKED and True:
    btn_wifi_forecast_clicked_event(event_struct)
  return

def setup():
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS

  M5.begin()
  Widgets.setRotation(1)
  m5ui.init()
  Home = m5ui.M5Page(bg_c=0xffffff)
  Forecast = m5ui.M5Page(bg_c=0xffffff)
  WiFi = m5ui.M5Page(bg_c=0xffffff)
  lbl_home_title = m5ui.M5Label("HOME", x=9, y=8, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_16, parent=Home)
  lbl_forecast_title = m5ui.M5Label("Forecast", x=10, y=8, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_18, parent=Forecast)
  lbl_wifi_title = m5ui.M5Label("WiFi", x=10, y=8, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_18, parent=WiFi)
  lbl_home_outdoor = m5ui.M5Label("Outdoor: -- C", x=9, y=40, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_forecast_subtitle = m5ui.M5Label("Next 3 days", x=10, y=34, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Forecast)
  lbl_wifi_current_ap = m5ui.M5Label("Connected AP: --", x=10, y=40, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=WiFi)
  lbl_home_clock = m5ui.M5Label("--:--:--", x=229, y=8, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_forecast_1 = m5ui.M5Label("Day 1: --", x=10, y=64, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Forecast)
  lbl_wifi_ip = m5ui.M5Label("IP: --", x=10, y=62, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=WiFi)
  lbl_home_indoor_temp = m5ui.M5Label("Indoor: --.- C", x=10, y=66, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_forecast_2 = m5ui.M5Label("Day 2: --", x=10, y=90, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Forecast)
  lbl_home_tvoc = m5ui.M5Label("TVOC: --", x=10, y=92, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_forecast_3 = m5ui.M5Label("Day 3: --", x=10, y=116, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Forecast)
  lbl_wifi_status = m5ui.M5Label("Status: --", x=10, y=170, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=WiFi)
  lbl_home_alert = m5ui.M5Label("Status: --", x=10, y=118, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_forecast_updated = m5ui.M5Label("Last update: --:--", x=10, y=146, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Forecast)
  btn_wifi_refresh = m5ui.M5Button(text="refresh", x=10, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=WiFi)
  lbl_home_icon = m5ui.M5Label("(sun)", x=10, y=146, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  btn_forecast_refresh = m5ui.M5Button(text="Refresh", x=10, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=Forecast)
  btn_wifi_ssid_1 = m5ui.M5Button(text="SSID_1", x=10, y=84, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=WiFi)
  lbl_home_motion = m5ui.M5Label("Motion: 0", x=110, y=148, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  btn_forecast_wifi = m5ui.M5Button(text="WiFi", x=225, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=Forecast)
  btn_wifi_ssid_2 = m5ui.M5Button(text="SSID_2", x=10, y=130, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=WiFi)
  btn_forecast_home = m5ui.M5Button(text="Home", x=123, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=Forecast)
  btn_wifi_forecast = m5ui.M5Button(text="Forecast", x=113, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=WiFi)
  btn_home_forecast = m5ui.M5Button(text="Forecast", x=57, y=195, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=Home)
  btn_wifi_home = m5ui.M5Button(text="Home", x=227, y=200, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=WiFi)
  btn_home_wifi = m5ui.M5Button(text="WiFi", x=222, y=195, bg_c=0x2196f3, text_c=0xffffff, font=lv.font_montserrat_14, parent=Home)
  lbl_home_indoor_hum = m5ui.M5Label("RH --%", x=129, y=66, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_home_eco2 = m5ui.M5Label("ECO2: --", x=129, y=92, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)
  lbl_home_date = m5ui.M5Label("Date", x=139, y=10, text_c=0x000000, bg_c=0xffffff, bg_opa=0, font=lv.font_montserrat_14, parent=Home)

  btn_wifi_ssid_1.add_event_cb(btn_wifi_ssid_1_event_handler, lv.EVENT.ALL, None)
  btn_wifi_ssid_2.add_event_cb(btn_wifi_ssid_2_event_handler, lv.EVENT.ALL, None)
  btn_home_forecast.add_event_cb(btn_home_forecast_event_handler, lv.EVENT.ALL, None)
  btn_home_wifi.add_event_cb(btn_home_wifi_event_handler, lv.EVENT.ALL, None)
  btn_forecast_refresh.add_event_cb(btn_forecast_refresh_event_handler, lv.EVENT.ALL, None)
  btn_forecast_home.add_event_cb(btn_forecast_home_event_handler, lv.EVENT.ALL, None)
  btn_forecast_wifi.add_event_cb(btn_forecast_wifi_event_handler, lv.EVENT.ALL, None)
  btn_wifi_refresh.add_event_cb(btn_wifi_refresh_event_handler, lv.EVENT.ALL, None)
  btn_wifi_home.add_event_cb(btn_wifi_home_event_handler, lv.EVENT.ALL, None)
  btn_wifi_forecast.add_event_cb(btn_wifi_forecast_event_handler, lv.EVENT.ALL, None)

  i2c0 = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
  pir_1 = PIRUnit((36, 26))
  env3_0 = ENVUnit(i2c=i2c0, type=3)
  tvoc_0 = TVOCUnit(i2c0)
  C_WIFI_1_SSID = 'your-ssid'
  C_WIFI_1_PASS = 'your-password'
  C_WIFI_2_SSID = 'false_wifi'
  C_WIFI_2_PASS = 'fake'
  import network
  global wlan_sta
  wlan_sta = network.WLAN(network.STA_IF)
  wlan_sta.active(True)

  try:
      btn_wifi_ssid_1.get_child(0).set_text(C_WIFI_1_SSID if C_WIFI_1_SSID else "SSID_1")
      btn_wifi_ssid_2.get_child(0).set_text(C_WIFI_2_SSID if C_WIFI_2_SSID else "SSID_2")
  except Exception:
      lbl_wifi_status.set_text("Status: button text fixed in UI")

  lbl_wifi_status.set_text("W1:{} | W2:{}".format(C_WIFI_1_SSID, C_WIFI_2_SSID))
  lbl_wifi_status.set_text("Status: --")
  import network

  global wlan_sta
  wlan_sta = network.WLAN(network.STA_IF)
  wlan_sta.active(True)

  # Timezone offset from UTC (summer in CH = 2, winter = 1)
  global TZ_OFFSET_HOURS
  TZ_OFFSET_HOURS = 2

  def sync_ntp():
      try:
          import ntptime
          ntptime.host = "pool.ntp.org"
          ntptime.settime()  # sets device clock in UTC
          return True
      except Exception:
          return False

  # If already connected at boot, sync now
  try:
      if wlan_sta.isconnected():
          sync_ntp()
  except Exception:
      pass
  import time
  global last_sensor_ms, last_wifi_ms, last_outdoor_ms
  last_sensor_ms = 0
  last_wifi_ms = 0
  last_outdoor_ms = 0
  refresh_wifi_info()
  refresh_outdoor()
  Home.screen_load()


def loop():
  global Home, Forecast, WiFi, lbl_home_title, lbl_forecast_title, lbl_wifi_title, lbl_home_outdoor, lbl_forecast_subtitle, lbl_wifi_current_ap, lbl_home_clock, lbl_forecast_1, lbl_wifi_ip, lbl_home_indoor_temp, lbl_forecast_2, lbl_home_tvoc, lbl_forecast_3, lbl_wifi_status, lbl_home_alert, lbl_forecast_updated, btn_wifi_refresh, lbl_home_icon, btn_forecast_refresh, btn_wifi_ssid_1, lbl_home_motion, btn_forecast_wifi, btn_wifi_ssid_2, btn_forecast_home, btn_wifi_forecast, btn_home_forecast, btn_wifi_home, btn_home_wifi, lbl_home_indoor_hum, lbl_home_eco2, lbl_home_date, i2c0, env3_0, pir_1, tvoc_0, C_WIFI_1_SSID, C_WIFI_1_PASS, C_WIFI_2_SSID, C_WIFI_2_PASS
  M5.update()
  import time
  global last_sensor_ms, last_wifi_ms, last_outdoor_ms

  now = time.ticks_ms()

  # Indoor toutes les 1s
  if time.ticks_diff(now, last_sensor_ms) >= 1000:
      last_sensor_ms = now
      try:
          refresh_home_metrics()
      except Exception:
          pass

  # WiFi toutes les 10s
  if time.ticks_diff(now, last_wifi_ms) >= 10000:
      last_wifi_ms = now
      try:
          refresh_wifi_info()
      except Exception:
          pass

  # Outdoor toutes les 10 min
  if time.ticks_diff(now, last_outdoor_ms) >= 600000:
      last_outdoor_ms = now
      try:
          refresh_outdoor()
      except Exception:
          pass


if __name__ == '__main__':
  try:
    setup()
    while True:
      loop()
  except (Exception, KeyboardInterrupt) as e:
    try:
      m5ui.deinit()
      from utility import print_error_msg
      print_error_msg(e)
    except ImportError:
      print("please update to latest firmware")
