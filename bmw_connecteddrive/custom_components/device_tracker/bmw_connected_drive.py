"""Device tracker for BMW Connected Drive vehicles.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.bmw_connected_drive/
"""
import json
import logging
import requests

from custom_components.bmw_connected_drive import DOMAIN as BMW_DOMAIN
from homeassistant.util import slugify

DEPENDENCIES = ['bmw_connected_drive']

_LOGGER = logging.getLogger(__name__)


def setup_scanner(hass, config, see, discovery_info=None):
    """Set up the BMW tracker."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.debug('Found BMW accounts: %s',
                  ', '.join([a.name for a in accounts]))
    for account in accounts:
        for vehicle in account.account.vehicles:
            tracker = BMWDeviceTracker(see, vehicle)
            account.add_update_listener(tracker.update)
            tracker.update()

    return True


class BMWDeviceTracker(object):
    """BMW Connected Drive device tracker."""

    def __init__(self, see, vehicle):
        """Initialize the Tracker."""
        self._see = see
        self.vehicle = vehicle
        self.dev_id = slugify(self.vehicle.name)

    def update(self) -> None:
        """Update the device info.
        
        Only update the state in home assistant if tracking in
        the car is enabled.
        """
        if not self.vehicle.state.is_vehicle_tracking_enabled:
            _LOGGER.debug('Tracking is disabled for vehicle %s',
                          self.vehicle.modelName)
            return
        _LOGGER.debug('Updating %s', self.vehicle.modelName)
        lat, lon = self.vehicle.state.gps_position
        address = self.get_place(lat, lon)
        heading = self.vehicle.state._attributes['position']['heading']
        heading_rounded = 0
        if heading:
            heading_rounded = min(range(0, 361, 30),
                                key=lambda x:abs(x-heading))
            if heading_rounded == 360:
                heading_rounded = 0
        attrs = {
            'address': address,
            'id': self.dev_id,
            'heading': heading,
            'heading_rounded': heading_rounded,
            'last_update': self.vehicle.state.timestamp.replace(tzinfo=None),
            'name': self.vehicle.name,
            'vin': self.vehicle.vin
        }
        self._see(
            dev_id=self.dev_id, host_name=self.vehicle.name,
            gps=self.vehicle.state.gps_position, attributes=attrs,
            icon='mdi:car'
        )
    
    def get_place(self, lat, lon):
        """Get address info from Openstreetmap based on lat and lon."""
        url = "https://nominatim.openstreetmap.org/reverse?format=json&"
        url += "lat={}&lon={}".format(lat, lon)
        response = requests.get(url)
        data = response.json()
        address = 'unknown'
        if 'display_name' in data:
            address = data['display_name']
        return address
