"""
Support for interface with a Sony Bravia TV.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.braviatv/

Updated by G3rard - October 2017
    Changes:
    * use Pre-shared key (PSK) instead of connecting with a pin and the use of a cookie
    * option for amplifier: don't show volume slider when amp is attached as slider only works for TV speakers
    * option for Android: turn on with other method as WOL will not work
    * show program info on second line of state card (only available if built-in TV tuner is used)
    * added progress bar (WIP, not visible possibly due to missing Play/Pause button)
    * filter source list with list from configuration file to avoid a long list of channels and radio stations
    * pause/play tv when using built-in TV tuner
    * channel up/down with next and previous buttons when using built-in TV tuner
"""
import logging
import os
import json
import re

import voluptuous as vol

from homeassistant.components.media_player import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK, SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP, SUPPORT_PLAY,
    SUPPORT_VOLUME_SET, SUPPORT_SELECT_SOURCE, MediaPlayerDevice,
    PLATFORM_SCHEMA, MEDIA_TYPE_MUSIC, SUPPORT_STOP)
from homeassistant.const import (CONF_HOST, CONF_NAME, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow

REQUIREMENTS = [
    'https://github.com/gerard33/braviarc/archive/0.4.2.zip'
    '#braviarc==0.4.2']

_LOGGER = logging.getLogger(__name__)

SUPPORT_BRAVIA = SUPPORT_PAUSE | SUPPORT_VOLUME_STEP | \
    SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
    SUPPORT_SELECT_SOURCE | SUPPORT_PLAY | SUPPORT_STOP

CLIENTID_PREFIX = 'HomeAssistant'
NICKNAME = 'Home Assistant'
DEFAULT_NAME = 'Sony Bravia TV'
STATE_STARTING = 'TV started' ### TO DO --> not working yet

CONF_PSK = 'psk'
CONF_MAC = 'mac'
CONF_AMP = 'amp'
CONF_ANDROID = 'android'
CONF_SOURCE_FILTER = 'sourcefilter'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PSK): cv.string,
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_AMP, default=False): cv.boolean,
    vol.Optional(CONF_ANDROID, default=False): cv.boolean,
    vol.Optional(CONF_SOURCE_FILTER, default=[]): vol.All(cv.ensure_list, [cv.string])
})

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Sony Bravia TV platform."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    mac = config.get(CONF_MAC)
    psk = config.get(CONF_PSK)
    amp = config.get(CONF_AMP)
    android = config.get(CONF_ANDROID)
    source_filter = config.get(CONF_SOURCE_FILTER)

    if host is None:
        _LOGGER.error("No TV IP address found in configuration file")
        return

    add_devices([BraviaTVDevice(host, psk, mac, name, amp, android, source_filter)])

class BraviaTVDevice(MediaPlayerDevice):
    """Representation of a Sony Bravia TV."""

    def __init__(self, host, psk, mac, name, amp, android, source_filter):
        """Initialize the Sony Bravia device."""
        _LOGGER.info("Setting up Sony Bravia TV")
        from braviarc import braviarc_psk

        self._braviarc = braviarc_psk.BraviaRC(host, psk, mac)
        self._name = name
        self._amp = amp
        self._android = android
        self._source_filter = source_filter
        self._state = STATE_OFF
        self._muted = False
        self._program_name = None
        self._channel_name = None
        self._channel_number = None
        self._source = None
        self._source_list = []
        self._original_content_list = []
        self._content_mapping = {}
        self._duration = None
        self._content_uri = None
        self._id = None
        self._playing = False
        self._start_date_time = None
        self._program_media_type = None
        self._min_volume = None
        self._max_volume = None
        self._volume = None
        ###Times
        self._start_time = None
        self._end_time = None
        self._media_position = None
        self._media_position_updated_at = None
        self._media_position_perc = None
        self._last_update = None

        _LOGGER.debug("Set up Sony Bravia TV with IP: " + host + " - PSK: " + psk + " - MAC: " + mac)

        self.update()

    def update(self):
        """Update TV info."""
        try:
            ### TV is starting
            ### TO DO --> show this while TV is starting but not yet showing information
            if self._state == STATE_STARTING:
                self._state = STATE_ON
                self._channel_name = 'TV started'

            power_status = self._braviarc.get_power_status()
            if power_status == 'active':
                self._state = STATE_ON
                self._refresh_volume()
                self._refresh_channels()
                playing_info = self._braviarc.get_playing_info()
                self._reset_playing_info()
                if playing_info is None or not playing_info:
                    self._channel_name = 'TV on'
                    self._program_name = 'No info: TV resumed after pause or App opened'
                else:
                    self._program_name = playing_info.get('programTitle')
                    self._channel_name = playing_info.get('title')
                    self._program_media_type = playing_info.get('programMediaType')
                    self._channel_number = playing_info.get('dispNum')
                    self._source = playing_info.get('source')
                    self._content_uri = playing_info.get('uri')
                    self._duration = playing_info.get('durationSec')
                    self._start_date_time = playing_info.get('startDateTime')
                    # Get time info from TV program
                    if self._start_date_time is not None and self._duration is not None:
                        time_info = self._braviarc.playing_time(self._start_date_time, self._duration)
                        self._start_time = time_info.get('start_time')
                        self._end_time = time_info.get('end_time')
                        self._media_position = time_info.get('media_position')
                        self._media_position_perc = time_info.get('media_position_perc')
                        self._last_update = utcnow()
            else:
                self._state = STATE_OFF

        except Exception as exception_instance:  # pylint: disable=broad-except
            _LOGGER.error("No data received from TV, probably it has just been turned off. Error message is: ")
            _LOGGER.error(exception_instance)
            self._state = STATE_OFF

    def _reset_playing_info(self):
        self._program_name = None
        self._channel_name = None
        self._program_media_type = None
        self._channel_number = None
        self._source = None
        self._content_uri = None
        self._duration = None
        self._start_date_time = None
        self._start_time = None
        self._end_time = None
        self._media_position = None
        self._media_position_updated_at = None
        self._media_position_perc = None

    def _refresh_volume(self):
        """Refresh volume information."""
        volume_info = self._braviarc.get_volume_info()
        if volume_info is not None:
            self._volume = volume_info.get('volume')
            self._min_volume = volume_info.get('minVolume')
            self._max_volume = volume_info.get('maxVolume')
            self._muted = volume_info.get('mute')

    def _refresh_channels(self):
        if not self._source_list:
            self._content_mapping = self._braviarc. \
                load_source_list()
            self._source_list = []
            if not self._source_filter: # list is empty
                for key in self._content_mapping:
                    self._source_list.append(key)
            else:
                filtered_dict = {title:uri for (title, uri) in self._content_mapping.items() if any(filter_title in title for filter_title in self._source_filter)}
                for key in filtered_dict:
                    self._source_list.append(key)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is not None:
            return self._volume / 100
        return None

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        supported = SUPPORT_BRAVIA
        #Remove volume slider if amplifier is attached to TV
        if self._amp:
            supported = supported ^ SUPPORT_VOLUME_SET
        return supported

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        # Loaded so media_artist is shown, used for program information below the channel in the state card
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        if self._duration is not None:
            return int(self._duration)

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        if self._media_position is not None:
            return int(self._media_position)

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.
        Returns value from homeassistant.util.dt.utcnow().
        """
        return self._last_update

    ###@property
    #def media_image_url(self):
    #    """Image url of current playing media."""
    #    return "http://url/image.png"
    
    @property
    def media_artist(self):
        """Artist of current playing media, music track only.
        Used to show TV program info.
        """
        return_value = None
        if self._program_name is not None:
            if self._start_time is not None and self._end_time is not None:
                return_value = self._program_name + ' [' + self._start_time + ' - ' + self._end_time + ']'
            else:
                return_value = self._program_name
        return return_value

    @property
    def media_title(self):
        """Title of current playing media.
        Used to show TV channel info.
        """
        return_value = None
        if self._channel_name is not None:
            if self._channel_number is not None:
                return_value = str(int(self._channel_number)) + ': ' + self._channel_name
            else:
                return_value = self._channel_name
        return return_value

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._channel_name

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._braviarc.set_volume_level(volume)

    def turn_on(self):
        """Turn the media player on. Use a different command for Android as WOL is not working"""
        self._state = STATE_STARTING
        if self._android:
            self._braviarc.turn_on_command()
        else:
            self._braviarc.turn_on()

    def turn_off(self):
        """Turn off media player."""
        self._state = STATE_OFF
        self._braviarc.turn_off()

    def volume_up(self):
        """Volume up the media player."""
        self._braviarc.volume_up()

    def volume_down(self):
        """Volume down media player."""
        self._braviarc.volume_down()

    def mute_volume(self, mute):
        """Send mute command."""
        self._braviarc.mute_volume()

    def select_source(self, source):
        """Set the input source."""
        if source in self._content_mapping:
            uri = self._content_mapping[source]
            self._braviarc.play_content(uri)

    def media_play_pause(self):
        """Simulate play pause media player."""
        if self._playing:
            self.media_pause()
        else:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self._playing = True
        self._braviarc.media_play()

    def media_pause(self):
        """Send media pause command to media player."""
        self._playing = False
        if self._program_name is not None:
            # Pause TV when TV tuner is playing
            self._braviarc.media_tvpause()
        else:
            self._braviarc.media_pause()

    def media_stop(self):
        """Send media stop command to media player."""
        ### TO DO --> not used currently
        self._playing = False
        self._braviarc.media_pause()

    def media_next_track(self):
        """Send next track command or next channel when TV tuner is on."""
        ###TO DO --> if self._source == "tv:dvbc" or "tv:dvbt":
        ###TO DO --> if self._program_media_type == "tv":
        if self._program_name is not None:
            self._braviarc.send_command('ChannelUp')
        else:
            self._braviarc.media_next_track()

    def media_previous_track(self):
        """Send the previous track command or previous channel when TV tuner is on."""
        if self._program_name is not None:
            self._braviarc.send_command('ChannelDown')
        else:
            self._braviarc.media_previous_track()
