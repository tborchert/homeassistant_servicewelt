"""Binary sensor platform for servicewelt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import ServiceweltEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ServiceweltDataUpdateCoordinator
    from .data import ServiceweltConfigEntry

# Define binary sensor entities based on scraped data
BINARY_SENSOR_DESCRIPTIONS = {
    # Operating mode sensors (from system_status page)
    "heating_circuit_pump": BinarySensorEntityDescription(
        key="heating_circuit_pump",
        name="Heating Circuit 1 Pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
    ),
    "dhw_heating": BinarySensorEntityDescription(
        key="dhw_heating",
        name="DHW Heating",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:water-boiler",
    ),
    "compressor": BinarySensorEntityDescription(
        key="compressor",
        name="Compressor",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:air-conditioner",
    ),
    "summer_mode": BinarySensorEntityDescription(
        key="summer_mode",
        name="Summer Mode",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:weather-sunny",
    ),
    "buffer_charging_pump": BinarySensorEntityDescription(
        key="buffer_charging_pump",
        name="Buffer Charging Pump 1",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
    ),
    "dhw_charging_pump": BinarySensorEntityDescription(
        key="dhw_charging_pump",
        name="DHW Charging Pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
    ),
    # Heat pump status sensors
    "compressor_output": BinarySensorEntityDescription(
        key="compressor_output",
        name="Compressor Output",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:air-conditioner",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ServiceweltConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    # Create entities for all available binary sensors
    entities = []
    for sensor_key, entity_description in BINARY_SENSOR_DESCRIPTIONS.items():
        entities.append(
            ServiceweltBinarySensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=entity_description,
                sensor_key=sensor_key,
            )
        )
    
    async_add_entities(entities)


class ServiceweltBinarySensor(ServiceweltEntity, BinarySensorEntity):
    """Servicewelt binary sensor class."""

    def __init__(
        self,
        coordinator: ServiceweltDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
        sensor_key: str,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._sensor_key = sensor_key

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return False

        value = self._extract_sensor_value()
        
        # Handle 'on'/'off' string values from HTML parsing
        if isinstance(value, str):
            return value.lower() == "on"
        
        # Handle boolean values
        return bool(value)

    def _extract_sensor_value(self) -> str | bool | None:
        """Extract binary sensor value from coordinator data."""
        data = self.coordinator.data
        
        # Map sensor keys to actual data paths from HTML scraping
        key_mappings = {
            # Operating mode sensors (from system_status page)
            "heating_circuit_pump": ("system_status", "OPERATING MODE", "HEATING CIRCUIT 1 PUMP"),
            "dhw_heating": ("system_status", "OPERATING MODE", "DHW HEATING"),
            "compressor": ("system_status", "OPERATING MODE", "COMPRESSOR"),
            "summer_mode": ("system_status", "OPERATING MODE", "SUMMER MODE"),
            "buffer_charging_pump": ("system_status", "SYSTEM STATUS", "BUFFER CHARGING PUMP 1"),
            "dhw_charging_pump": ("system_status", "SYSTEM STATUS", "DHW CHARGING PUMP"),
            
            # Heat pump status sensors (from heat_pump_status page)
            "compressor_output": ("heat_pump_status", "HEAT PUMP STATUS", "OUTPUT COMPRESSOR ON"),
        }
        
        if self._sensor_key not in key_mappings:
            return None
            
        page, category, field = key_mappings[self._sensor_key]
        
        try:
            return data.get(page, {}).get(category, {}).get(field)
        except (KeyError, AttributeError):
            return None
