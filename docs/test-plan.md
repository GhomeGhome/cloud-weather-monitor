# Validation and Robustness Test Plan

## Mandatory scenarios
1. Internet outage
   - Disconnect network during device runtime.
   - Expected: device keeps local display alive, ingestion logs errors, no crash.
   - Restore network.
   - Expected: ingestion resumes automatically.

2. Device reboot
   - Stop device process and restart.
   - Expected: boot sync endpoint returns latest snapshot and UI immediately displays last known data.

3. Wi-Fi update
   - Change SSID/password in the device Wi-Fi config workflow.
   - Expected: updated config is persisted and used at next boot.

4. Alert thresholds
   - Force humidity below 40.
   - Expected: API returns low-humidity alert, event written in BigQuery.
   - Force TVOC > 500 or eCO2 > 1000.
   - Expected: poor-air alert + event row.

5. Voice cooldown
   - Trigger one alert and announcement.
   - Trigger same alert again within one hour.
   - Expected: no second announcement.

## Dashboard checks
- Realtime page shows latest indoor and outdoor values.
- History page draws temperature, humidity, TVOC, eCO2 trends.
- Events page displays alert/event rows.

## Cloud Run checks
- `/live` returns `status: ok`.
- Dashboard URL is reachable publicly.
- Service env vars are set (project, dataset, table names, secret, weather key).
