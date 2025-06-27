"""Sensor platform for servicewelt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfTemperature, UnitOfPressure, UnitOfEnergy, UnitOfPower, UnitOfTime, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfFrequency, PERCENTAGE

from .entity import ServiceweltEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ServiceweltDataUpdateCoordinator
    from .data import ServiceweltConfigEntry

# Define sensor entities based on the scraped data structure
SENSOR_DESCRIPTIONS = {
    # System sensors (s_1_0)
    "outside_temperature": SensorEntityDescription(
        key="outside_temperature",
        name="Outside Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "actual_temperature_hk1": SensorEntityDescription(
        key="actual_temperature_hk1", 
        name="Actual Temperature HK1",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "set_temperature_hk1": SensorEntityDescription(
        key="set_temperature_hk1",
        name="Set Temperature HK1", 
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer-plus",
    ),
    "actual_buffer_temperature": SensorEntityDescription(
        key="actual_buffer_temperature",
        name="Actual Buffer Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "set_buffer_temperature": SensorEntityDescription(
        key="set_buffer_temperature",
        name="Set Buffer Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer-plus",
    ),
    "dhw_actual_temperature": SensorEntityDescription(
        key="dhw_actual_temperature",
        name="DHW Actual Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "dhw_set_temperature": SensorEntityDescription(
        key="dhw_set_temperature",
        name="DHW Set Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer-plus",
    ),
    # Heat pump process data (s_1_1)
    "return_temperature": SensorEntityDescription(
        key="return_temperature",
        name="Return Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "flow_temperature": SensorEntityDescription(
        key="flow_temperature",
        name="Flow Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "hot_gas_temperature": SensorEntityDescription(
        key="hot_gas_temperature",
        name="Hot Gas Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        icon="mdi:thermometer",
    ),
    "low_pressure": SensorEntityDescription(
        key="low_pressure",
        name="Low Pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class="pressure",
        icon="mdi:gauge",
    ),
    "high_pressure": SensorEntityDescription(
        key="high_pressure",
        name="High Pressure", 
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class="pressure",
        icon="mdi:gauge",
    ),
    "inverter_power": SensorEntityDescription(
        key="inverter_power",
        name="Inverter Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class="power",
        icon="mdi:lightning-bolt",
    ),
    "inverter_current": SensorEntityDescription(
        key="inverter_current",
        name="Inverter Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class="current",
        icon="mdi:current-ac",
    ),
    "inverter_voltage": SensorEntityDescription(
        key="inverter_voltage",
        name="Inverter Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class="voltage",
        icon="mdi:flash",
    ),
    "compressor_speed": SensorEntityDescription(
        key="compressor_speed",
        name="Compressor Speed",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:fan",
    ),
    "fan_rate": SensorEntityDescription(
        key="fan_rate",
        name="Fan Rate",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:fan",
    ),
    # Energy data
    "heating_energy_day": SensorEntityDescription(
        key="heating_energy_day",
        name="Heating Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class="energy",
        icon="mdi:lightning-bolt",
    ),
    "heating_energy_total": SensorEntityDescription(
        key="heating_energy_total",
        name="Heating Energy Total", 
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class="energy",
        icon="mdi:lightning-bolt",
    ),
    "dhw_energy_day": SensorEntityDescription(
        key="dhw_energy_day",
        name="DHW Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class="energy",
        icon="mdi:lightning-bolt",
    ),
    "dhw_energy_total": SensorEntityDescription(
        key="dhw_energy_total", 
        name="DHW Energy Total",
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        device_class="energy",
        icon="mdi:lightning-bolt",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ServiceweltConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Create entities for all available sensors
    entities = []
    for sensor_key, entity_description in SENSOR_DESCRIPTIONS.items():
        entities.append(
            ServiceweltSensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=entity_description,
                sensor_key=sensor_key,
            )
        )
    
    async_add_entities(entities)


class ServiceweltSensor(ServiceweltEntity, SensorEntity):
    """Servicewelt Sensor class."""

    def __init__(
        self,
        coordinator: ServiceweltDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        sensor_key: str,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._sensor_key = sensor_key

    @property
    def native_value(self) -> float | str | None:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            return None

        # Map sensor keys to data paths in the scraped structure
        value = self._extract_sensor_value()
        
        # Handle structured values with units
        if isinstance(value, dict) and "value" in value:
            return value["value"]
        
        return value

    def _extract_sensor_value(self) -> float | str | None:
        """Extract sensor value from coordinator data."""
        data = self.coordinator.data
        
        # Map sensor keys to actual data paths from HTML scraping
        key_mappings = {
            # System data (from 'system' page)
            "outside_temperature": ("system", "HEATING", "OUTSIDE TEMPERATURE"),
            "actual_temperature_hk1": ("system", "HEATING", "ACTUAL TEMPERATURE HK 1"),
            "set_temperature_hk1": ("system", "HEATING", "SET TEMPERATURE HK 1"),
            "actual_buffer_temperature": ("system", "HEATING", "ACTUAL BUFFER TEMPERATURE"),
            "set_buffer_temperature": ("system", "HEATING", "SET BUFFER TEMPERATURE"),
            "dhw_actual_temperature": ("system", "DHW", "ACTUAL TEMPERATURE"),
            "dhw_set_temperature": ("system", "DHW", "SET TEMPERATURE"),
            
            # Heat pump process data (from 'heat_pump' page)
            "return_temperature": ("heat_pump", "PROCESS DATA", "RETURN TEMPERATURE"),
            "flow_temperature": ("heat_pump", "PROCESS DATA", "FLOW TEMPERATURE"),
            "hot_gas_temperature": ("heat_pump", "PROCESS DATA", "HOT GAS TEMPERATURE"),
            "low_pressure": ("heat_pump", "PROCESS DATA", "LOW PRESSURE"),
            "high_pressure": ("heat_pump", "PROCESS DATA", "HIGH PRESSURE"),
            "inverter_power": ("heat_pump", "PROCESS DATA", "INVERTER POWER"),
            "inverter_current": ("heat_pump", "PROCESS DATA", "INVERTER CURRENT"),
            "inverter_voltage": ("heat_pump", "PROCESS DATA", "INVERTER VOLTAGE"),
            "compressor_speed": ("heat_pump", "PROCESS DATA", "ACTUAL COMPRESSOR SPEED"),
            "fan_rate": ("heat_pump", "PROCESS DATA", "REL FAN RATE"),
            
            # Energy data
            "heating_energy_day": ("heat_pump", "AMOUNT OF HEAT", "VD HEATING DAY"),
            "heating_energy_total": ("heat_pump", "AMOUNT OF HEAT", "VD HEATING TOTAL"),
            "dhw_energy_day": ("heat_pump", "AMOUNT OF HEAT", "VD DHW DAY"),
            "dhw_energy_total": ("heat_pump", "AMOUNT OF HEAT", "VD DHW TOTAL"),
        }
        
        if self._sensor_key not in key_mappings:
            return None
            
        page, category, field = key_mappings[self._sensor_key]
        
        try:
            return data.get(page, {}).get(category, {}).get(field)
        except (KeyError, AttributeError):
            return None
