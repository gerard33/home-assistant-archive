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
