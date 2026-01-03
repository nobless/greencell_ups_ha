# GreenCell UPS integration for Home Assistant

Custom Home Assistant integration for GreenCell UPS devices and sensors through API.

## Features
- Sensors for voltages, load, battery level, temperature, and status/error codes (nominal/fault values appear under Diagnostics).
- Binary sensors for connectivity, failures, tests, shutdown, beeper state, and more.
- Device buttons for control: toggle beeper, shutdown/wake, short/long test, cancel test (on the device page).
- Configurable scan interval and SSL verification via Options flow.
- Attempts to auto-detect MAC for device linking in HA; falls back to network resolution if possible.

## Install
### HACS
The easiest way to install this component is by clicking the badge below, which adds this repo as a custom repo in your HASS instance.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nobless&repository=greencell_upds_ha&category=Integration)

You can also add the integration manually by copying `custom_components/greencell_ups` into `<HASS config directory>/custom_components`

### Configuration

- Browse to your Home Assistant instance.
- Go to  Settings > Devices & Services.
- In the bottom right corner, select the  Add Integration button.
- From the list, select GreenCell UPS.
- Enter host/password (SSL verify optional). Use Options to adjust scan interval and SSL verify.
- Device page exposes control buttons (beeper toggle, shutdown/wake, short/long test, cancel test).
