# Copilot instructions — greencell_ups

This file gives targeted guidance to AI coding agents working on the `greencell_ups` Home Assistant custom integration.

High-level architecture
- Integration is a custom Home Assistant integration under `custom_components/greencell_ups`.
- `__init__.py` creates a `GreencellCoordinator` and stores it at `hass.data[DOMAIN][entry.entry_id]`.
- `GreencellCoordinator` (in `coordinator.py`) subclasses `DataUpdateCoordinator` and delegates HTTP calls to `GreencellApi`.
- Platforms: `sensor` and `binary_sensor` (see `const.py` and `PLATFORMS`). Entities are CoordinatorEntity wrappers referencing `coordinator.data`.

Key files to reference
- `custom_components/greencell_ups/api.py` — HTTP client using `aiohttp`, `async_timeout`. Token is held in `GreencellApi._token`; `login()` posts to `/api/login`, `fetch_status()` GETs `/api/current_parameters`.
- `custom_components/greencell_ups/coordinator.py` — polling interval comes from `UPDATE_INTERVAL` in `const.py` (30s). Errors are wrapped as `UpdateFailed`.
- `custom_components/greencell_ups/sensor.py` and `binary_sensor.py` — show entity naming, unique_id (`greencell_{key}`), and how values are read from `coordinator.data`.
- `custom_components/greencell_ups/config_flow.py` — validates host/password by calling `GreencellApi.login()` before creating a config entry.
- `custom_components/greencell_ups/diagnostics.py` — diagnostics provider; sensitive keys are redacted (`password`, `access_token`, `refresh_token`).
- `manifest.json` — lists `config_flow: true`, `iot_class: local_polling`, and `version`.

Patterns and conventions (concrete)
- Entities use `CoordinatorEntity` + platform entity class order: `class GreencellSensor(CoordinatorEntity, SensorEntity)`.
- Unique IDs are `greencell_{key}` where `key` is from the SENSORS/BINARY_SENSORS dicts (e.g. `batteryLevel`, `inputVoltage`).
- Sensors expose `native_value` using `self.coordinator.data.get(self._key)`; binary sensors expose `is_on` as `bool(self.coordinator.data.get(self._key))`.
- Network: requests use 10s timeout (`async_timeout.timeout(10)`) and re-authenticate on 401 by clearing `_token` and calling `login()`.
- Coordinator polling frequency: controlled by `const.UPDATE_INTERVAL` (change here to alter global polling behavior).

Developer workflows / quick commands (discoverable from repo)
- Install for local HA testing: copy `custom_components/greencell_ups` into `<HA config>/custom_components` or install via HACS (see root README).
- To validate config flow changes: run Home Assistant dev instance and add integration via Settings → Devices & Services → Add Integration → Greencell UPS.
- For debugging at runtime: check Home Assistant logs and look for `Logger` messages from the `greencell_ups` domain and traceback from `UpdateFailed` when coordinator updates fail.

What to change and where (examples)
- Add a new sensor: update `SENSORS` in `sensor.py` with key/name/unit, then the entity will be created automatically by `async_setup_entry`.
- Change polling: modify `UPDATE_INTERVAL` in `const.py` and coordinator will pick it up on next reload.
- Extend API calls: add methods to `GreencellApi` and call them from `coordinator` or platforms; follow existing login/token handling pattern.

What not to assume
- There are no automated tests in the repo; do not add references to tests that do not exist.
- The host/password are stored in the config entry; diagnostics redacts them — do not log secrets.

If you modify this file
- Preserve the concrete examples (file paths, keys) above. If you add new platform files or change unique_id formats, update this document.

Questions for the maintainer
- Do you want a recommended local dev command (docker / hass core) documented here?
- Are there any additional sensor keys or naming conventions to include?

---
Please review and tell me any missing examples or developer commands to add.
