"""Sensor platform for Greencell UPS"""
import logging
import requests
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

SENSOR_FIELDS = {
    "inputVoltage": ("Input Voltage", "V"),
    "inputVoltageFault": ("Input Voltage Fault", "V"),
    "outputVoltage": ("Output Voltage", "V"),
    "load": ("Load", "A"),
    "inputFrequency": ("Input Frequency", "Hz"),
    "batteryVoltage": ("Battery Voltage", "V"),
    "temperature": ("Temperature", "°C"),
    "utilityFail": ("Utility Fail", None),
    "batteryLow": ("Battery Low", None),
    "bypassBoost": ("Bypass Boost", None),
    "failed": ("Failed", None),
    "offline": ("Offline", None),
    "testInProgress": ("Test In Progress", None),
    "shutdownActive": ("Shutdown Active", None),
    "beeperOn": ("Beeper On", None),
    "batteryLevel": ("Battery Level", "%"),
    "active": ("Active", None),
    "connected": ("Connected", None),
    "status": ("Status", None),
    "errno": ("Errno", None),
    "inputVoltageNominal": ("Input Voltage Nominal", "V"),
    "inputFrequencyNominal": ("Input Frequency Nominal", "Hz"),
    "batteryVoltageNominal": ("Battery Voltage Nominal", "V"),
    "inputCurrentNominal": ("Input Current Nominal", "A"),
    "batteryNumberNominal": ("Battery Number Nominal", None),
    "batteryVoltageHighNominal": ("Battery Voltage High Nominal", "V"),
    "batteryVoltageLowNominal": ("Battery Voltage Low Nominal", "V"),
    "reg": ("Register", None)
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    host = config.get(CONF_HOST)
    password = config.get(CONF_PASSWORD)

    api = GreencellAPI(host, password)

    sensors = [GreencellSensor(api, key, *SENSOR_FIELDS[key]) for key in SENSOR_FIELDS]
    add_entities(sensors, True)


class GreencellSensor(SensorEntity):
    def __init__(self, api, key, name, unit):
        self._api = api
        self._key = key
        self._name = name
        self._unit = unit
        self._state = None

    @property
    def name(self):
        return f"{DEFAULT_NAME} {self._name}"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    def update(self):
        data = self._api.get_data()
        if data:
            self._state = data.get(self._key)


class GreencellAPI:
    def __init__(self, host, password):
        self.host = host
        self.password = password
        self.access_token = None
        self.expiration = datetime.min.replace(tzinfo=timezone.utc)

    def get_token(self):
        url = f"{self.host}/api/login"
        r = requests.post(url, json={"password": self.password}, timeout=10)
        if r.status_code != 200:
            return False
        resp = r.json()
        self.access_token = resp.get("access_token")
        exp_str = resp.get("expiration_date")
        self.expiration = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
        return True

    def get_data(self):
        # refresh token if expired
        if not self.access_token or datetime.now(timezone.utc) >= self.expiration:
            if not self.get_token():
                return None

        url = f"{self.host}/api/current_parameters"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            if not self.get_token():
                return None
            headers = {"Authorization": f"Bearer {self.access_token}"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return None

        return r.json()
