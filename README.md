# GreenCell UPS integration for Home Assistant

Custom Home Assistant integration for GreenCell UPS devices and sensors via the local HTTP API.

## Features
- Sensors for voltages, load, battery level, temperature, and status/error codes (nominal/fault values appear under Diagnostics).
- Binary sensors for connectivity, failures, tests, shutdown, beeper state, and more.
- Device buttons for control: toggle beeper, shutdown/wake, short/long test, cancel test (on the device page).
- Configurable scan interval and SSL verification via Options flow.
- Attempts to auto-detect MAC for device linking in HA; you can also set it manually via Options if discovery fails.

## UI reference
![GreenCell UPS dashboard](docs/ui.png)

## API endpoints used (reverse engineered)
| Endpoint | Method | Purpose | Auth/Notes |
| --- | --- | --- | --- |
| `/api/login` | POST | Obtain bearer token | No (201 on success) |
| `/api/current_parameters` | GET | Live status/metrics payload | Bearer token |
| `/api/specification` | GET | Device specification (model/codes, etc.) | Bearer token |
| `/api/device/specification` | GET | Device specification (alternate path) | Bearer token |
| `/api/commands` | POST | Control actions via `{"action": "...", "args": {}}` (returns int/HTML) | Bearer token |
| `/api/statistics/tests` | GET | History of UPS tests (short/long) with voltage thresholds and timestamps | Bearer token |
| `/api/statistics/tests/{id}/measurements` | GET | Measurements for a test run (timestamp, load, battery_voltage/level, utility_fail, etc.) | Bearer token |
| `/api/statistics/events` | GET | Event history (supports `limit` query) | Bearer token |
| `/api/scheduler/schedules` | GET | Schedules (supports `visible` query) | Bearer token |
| `/api/scheduler/schedules` | POST | Create schedule with `event`/`action` payload (e.g., battery-low → audio-alert) | Bearer token |
| `/api/scheduler/schedules/{id}` | DELETE | Delete schedule | Bearer token |
| `/api/settings/smtp` | GET/PUT | SMTP settings payload (host/port/user/pass/from/default_recipient) | Bearer token |
| `/api/settings/smtp/verify` | POST | Verify SMTP settings | Bearer token |

Sample responses for the above endpoints (tests, schedules, SMTP, measurements) are captured in this repo for reference. An OpenAPI export of the observed endpoints is available at [`docs/openapi.json`](docs/openapi.json). Endpoints are reverse engineered and may change with firmware updates.

### Command actions
Actions sent to `/api/commands`:
- `beeperToggleOrder`
- `shutdownOrder`
- `wakeUpOrder`
- `shortTestOrder` (short test, ~10s)
- `longTestOrder` (battery discharge test)
- `cancelTestOrder` (cancels running tests)

Sample payloads matching these endpoints live in `tests/samples/` for test coverage.

### Notes
- Control is exposed as device buttons/switches.
- Tests use the sample payloads in `tests/samples/` (run with `pytest`).
- Some diagnostic sensors (e.g., input voltage fault, nominal voltages, register, battery number nominal) are disabled by default in HA but can be enabled manually.

## Install
### HACS
The easiest way to install this component is by clicking the badge below, which adds this repo as a custom repo in your HASS instance.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nobless&repository=greencell_upds_ha&category=Integration)

You can also add the integration manually by copying `custom_components/greencell_ups` into `<HASS config directory>/custom_components`.

### Configuration

- Browse to your Home Assistant instance.
- Go to Settings > Devices & Services.
- In the bottom right corner, select the Add Integration button.
- From the list, select GreenCell UPS.
- Enter host/password (SSL verify optional). Use Options to adjust scan interval and SSL verify.
- Device page exposes control buttons (beeper toggle, shutdown/wake, short/long test, cancel test).
