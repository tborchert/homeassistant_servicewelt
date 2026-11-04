# Stiebel Eltron Servicewelt Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

**This integration will set up the following platforms:**

Platform | Description
-- | --
`sensor` | Temperature, pressure, energy, and electrical sensors from your heat pump
`binary_sensor` | Status sensors for pumps, compressor, and operating modes

This Home Assistant custom integration connects to the Stiebel Eltron Servicewelt portal to monitor your heat pump system. It extracts real-time data including temperatures, pressures, energy consumption, and operational status.

## Features

- **Temperature Monitoring**: Outside temperature, heating circuit temperatures, DHW temperatures, heat pump process temperatures
- **Energy Tracking**: Daily and total energy consumption and generation for heating and DHW
- **System Status**: Real-time status of pumps, compressor, and operating modes
- **Process Data**: Heat pump pressures, electrical measurements, and performance metrics
- **Automatic Updates**: Configurable update intervals (default: 10 seconds)

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz) installed
2. Open HACS, click the three-dot menu in the top right and choose "Custom repositories"
3. Enter the repository URL `https://github.com/tborchert/homeassistant_servicewelt`, select "Integration" as the type and click "Add"
4. Search HACS for "Stiebel Eltron Servicewelt", open it and click "Download"
5. Restart Home Assistant
6. Add the integration under Settings > Devices & services (see [Configuration](#configuration))

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`)
2. If you do not have a `custom_components` directory (folder) there, you need to create it
3. In the `custom_components` directory (folder) create a new folder called `servicewelt`
4. Download _all_ the files from the `custom_components/servicewelt/` directory (folder) in this repository
5. Place the files you downloaded in the new directory (folder) you created
6. Restart Home Assistant

## Configuration

### Using the UI

1. In Home Assistant, go to "Configuration" > "Integrations"
2. Click the "+" button to add a new integration
3. Search for "Stiebel Eltron Servicewelt"
4. Enter your Servicewelt portal details:
   - **Portal URL**: Address of the Servicewelt web interface (default `http://servicewelt`)
   - **Username**: Your Servicewelt account username
   - **Password**: Your Servicewelt account password
5. Click "Submit"

The integration will automatically discover and create sensors for all available data points from your heat pump system.

## Supported Data Points

### Temperature Sensors
- Outside Temperature
- Heating Circuit 1 (Actual & Set Temperature)
- Buffer Temperature (Actual & Set)
- DHW Temperature (Actual & Set)
- Heat pump process temperatures (Return, Flow, Hot Gas, etc.)

### Energy Sensors
- Daily and total heating energy
- Daily and total DHW energy
- Power consumption metrics

### Electrical Sensors
- Inverter power, current, and voltage
- Compressor speed and fan rate

### Pressure Sensors
- Low and high pressure readings

### Binary Status Sensors
- Heating circuit pump status
- DHW heating status
- Compressor status
- Summer mode status
- Buffer and DHW charging pump status

## Troubleshooting

### Common Issues

**Integration fails to load:**
- Verify your Servicewelt credentials are correct
- Check that your heat pump system is accessible via the Servicewelt portal
- Ensure your Home Assistant instance can reach the internet

**Sensors showing "Unknown" or "Unavailable":**
- Check the Home Assistant logs for specific error messages
- Verify your heat pump is online and reporting data
- Try restarting the integration

**Update frequency issues:**
- The default update interval is 10 seconds
- You can modify this in the integration's coordinator configuration
- Be mindful of not overwhelming the Servicewelt servers

## Contributing

If you want to contribute to this integration development, please read the [Contribution Guidelines](CONTRIBUTING.md).

## Credits

This integration was built using the [Home Assistant Integration Blueprint](https://github.com/ludeeus/integration_blueprint) as a foundation.

---

[servicewelt]: https://github.com/tborchert/homeassistant_servicewelt
[commits-shield]: https://img.shields.io/github/commit-activity/y/tborchert/homeassistant_servicewelt.svg?style=for-the-badge
[commits]: https://github.com/tborchert/homeassistant_servicewelt/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/tborchert/homeassistant_servicewelt.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40tborchert-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/tborchert/homeassistant_servicewelt.svg?style=for-the-badge
[releases]: https://github.com/tborchert/homeassistant_servicewelt/releases
[user_profile]: https://github.com/tborchert