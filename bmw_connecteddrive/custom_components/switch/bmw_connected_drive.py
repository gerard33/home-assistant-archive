"""
Support for BMW cars with BMW ConnectedDrive.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.bmw_connected_drive/
"""
import asyncio
import logging

from custom_components.bmw_connected_drive import DOMAIN as BMW_DOMAIN
from homeassistant.components.switch import SwitchDevice
from homeassistant.const import STATE_OFF, STATE_ON

DEPENDENCIES = ['bmw_connected_drive']

_LOGGER = logging.getLogger(__name__)

SWITCHES = {
    'climate': ['Climate', 'mdi:air-conditioner'],
    'light': ['Light', 'mdi:alarm-light'],
    'horn': ['Horn', 'mdi:bullhorn']
}

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the BMW Connected Drive switches."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.debug('Found BMW accounts: %s',
                  ', '.join([a.name for a in accounts]))
    devices = []
    for account in accounts:
        for vehicle in account.account.vehicles:
            for key, value in sorted(SWITCHES.items()):
                device = BMWSwitch(account, vehicle, key, value[0], value[1])
                devices.append(device)
    add_devices(devices, True)

class BMWSwitch(SwitchDevice):
    """Representation of a BMW vehicle switch."""

    def __init__(self, account, vehicle, attribute: str, sensor_name, icon):
        """Initialize the switch."""
        self._account = account
        self._vehicle = vehicle
        self._attribute = attribute
        self._name = '{} {}'.format(self._vehicle.name, self._attribute)
        self._unique_id = '{}-{}'.format(self._vehicle.vin, self._attribute)
        self._sensor_name = sensor_name
        self._icon = icon
        self._state = None

    @property
    def unique_id(self):
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self._state == STATE_ON

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'last_update': self._vehicle.state.timestamp.replace(tzinfo=None),
            'car': self._vehicle.name,
            'friendly_name': self._sensor_name
        }

    def turn_on(self, **kwargs):
        """Send the on command."""
        _LOGGER.debug("%s: switching on %s", self._vehicle.name,
                        self._name)
        if self._attribute == 'climate':
            self._vehicle.remote_services.trigger_remote_air_conditioning()
        elif self._attribute == 'light':
            self._vehicle.remote_services.trigger_remote_light_flash()
        elif self._attribute == 'horn':
            self._vehicle.remote_services.trigger_remote_horn()

    def turn_off(self, **kwargs):
        """Send the off command."""
        _LOGGER.debug("%s: switching off %s", self._vehicle.name,
                        self._name)
        ### CAN CLIMATE BE PUT OFF?

    def update(self):
        """Update state of the switch."""
        _LOGGER.info("%s: updating data for %s", self._vehicle.name,
                     self._attribute)

        ### IS CLIMATE STATUS AVAILABLE?
        self._state = STATE_OFF

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Add callback after being added to hass.

        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
        self._account.async_add_to_group(self._vehicle, self.entity_id)
