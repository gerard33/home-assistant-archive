BMW ConnectedDrive as custom component

See this topic for more info
https://community.home-assistant.io/t/wip-bmw-connected-drive-custom-component/39569/103

```yaml
 # Example configuration.yaml entry
 bmw_connected_drive:
   mycar:
     username: USERNAME_BMW_CONNECTED_DRIVE
     password: PASSWORD_BMW_CONNECTED_DRIVE
     region: one of "north_america", "china", "rest_of_world"
 ```
For the region of your Connected Drive account please use one of these values: `north_america`, `china`, `rest_of_world`

**Device tracker**

If your new devices aren't automatically tracked, you have to edit the known_devices.yaml and enable tracking for the BMW device tracker to make sure it get's visible in Home Assistant.

**Switches**

This version uses the newly added [services](https://github.com/home-assistant/home-assistant/pull/13497) instead of the switches, you can configure this by using the following script.
```yaml
bmw_airco:
  sequence:
    - service: bmw_connected_drive.activate_air_conditioning
      data:
        vin: '<your_17_char_vin>'
bmw_horn:
  sequence:
    - service: bmw_connected_drive.sound_horn
      data:
        vin: '<your_17_char_vin>'
bmw_light:
  sequence:
    - service: bmw_connected_drive.light_flash
      data:
        vin: '<your_17_char_vin>'
bmw_refresh:
  sequence:
    - service: bmw_connected_drive.update_state
```
