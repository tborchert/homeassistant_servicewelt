"""Test the Servicewelt binary sensor platform."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.servicewelt.binary_sensor import (
    ServiceweltBinarySensor,
    BINARY_SENSOR_DESCRIPTIONS,
    async_setup_entry,
)


class TestServiceweltBinarySensor:
    """Test the ServiceweltBinarySensor class."""

    @pytest.fixture
    def mock_coordinator(self, parsed_sample_data):
        """Fixture for mocked coordinator."""
        coordinator = MagicMock()
        coordinator.data = parsed_sample_data
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator):
        """Fixture for mocked config entry."""
        entry = MagicMock()
        entry.runtime_data.coordinator = mock_coordinator
        return entry

    async def test_binary_sensor_descriptions_exist(self):
        """Test that binary sensor descriptions are properly defined."""
        assert len(BINARY_SENSOR_DESCRIPTIONS) > 0
        
        # Check that key binary sensors are defined
        assert "heating_circuit_pump" in BINARY_SENSOR_DESCRIPTIONS
        assert "dhw_heating" in BINARY_SENSOR_DESCRIPTIONS
        assert "compressor" in BINARY_SENSOR_DESCRIPTIONS
        assert "summer_mode" in BINARY_SENSOR_DESCRIPTIONS

    async def test_binary_sensor_descriptions_have_required_fields(self):
        """Test that all binary sensor descriptions have required fields."""
        for key, description in BINARY_SENSOR_DESCRIPTIONS.items():
            assert hasattr(description, "key")
            assert hasattr(description, "name")
            assert description.key == key
            assert description.name is not None

    async def test_pump_sensors_have_correct_device_class(self):
        """Test that pump sensors have the correct device class."""
        pump_sensors = [
            "heating_circuit_pump",
            "buffer_charging_pump",
            "dhw_charging_pump",
        ]
        
        for sensor_key in pump_sensors:
            if sensor_key in BINARY_SENSOR_DESCRIPTIONS:
                description = BINARY_SENSOR_DESCRIPTIONS[sensor_key]
                assert description.device_class == BinarySensorDeviceClass.RUNNING

    async def test_compressor_sensors_have_correct_device_class(self):
        """Test that compressor sensors have the correct device class."""
        compressor_sensors = ["compressor", "compressor_output"]
        
        for sensor_key in compressor_sensors:
            if sensor_key in BINARY_SENSOR_DESCRIPTIONS:
                description = BINARY_SENSOR_DESCRIPTIONS[sensor_key]
                assert description.device_class == BinarySensorDeviceClass.RUNNING

    async def test_binary_sensor_initialization(self, mock_coordinator):
        """Test binary sensor initialization."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        assert sensor._sensor_key == "heating_circuit_pump"
        assert sensor.entity_description == description

    async def test_heating_circuit_pump_sensor_on(self, mock_coordinator):
        """Test heating circuit pump sensor when on."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # The mock data has this pump as "on"
        assert sensor.is_on is True

    async def test_dhw_heating_sensor_on(self, mock_coordinator):
        """Test DHW heating sensor when on."""
        description = BINARY_SENSOR_DESCRIPTIONS["dhw_heating"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="dhw_heating",
        )
        
        # The mock data has DHW heating as "on"
        assert sensor.is_on is True

    async def test_compressor_sensor_on(self, mock_coordinator):
        """Test compressor sensor when on."""
        description = BINARY_SENSOR_DESCRIPTIONS["compressor"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="compressor",
        )
        
        # The mock data has compressor as "on"
        assert sensor.is_on is True

    async def test_summer_mode_sensor_on(self, mock_coordinator):
        """Test summer mode sensor when on."""
        description = BINARY_SENSOR_DESCRIPTIONS["summer_mode"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="summer_mode",
        )
        
        # The mock data has summer mode as "on"
        assert sensor.is_on is True

    async def test_buffer_charging_pump_sensor_on(self, mock_coordinator):
        """Test buffer charging pump sensor when on."""
        description = BINARY_SENSOR_DESCRIPTIONS["buffer_charging_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="buffer_charging_pump",
        )
        
        # The mock data has buffer charging pump as "on"
        assert sensor.is_on is True

    async def test_binary_sensor_with_off_state(self, mock_coordinator):
        """Test binary sensor when state is off."""
        # Modify the coordinator data to have an "off" state
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = "off"
        
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        assert sensor.is_on is False

    async def test_binary_sensor_with_no_data(self, mock_coordinator):
        """Test binary sensor when coordinator has no data."""
        mock_coordinator.data = None
        
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        assert sensor.is_on is False

    async def test_binary_sensor_with_missing_key(self, mock_coordinator):
        """Test binary sensor when data key is missing."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="nonexistent_sensor",
        )
        
        assert sensor.is_on is False

    async def test_extract_sensor_value_mappings(self, mock_coordinator):
        """Test that all binary sensor key mappings work correctly."""
        test_cases = [
            ("heating_circuit_pump", ("system_status", "OPERATING MODE", "HEATING CIRCUIT 1 PUMP"), "on"),
            ("dhw_heating", ("system_status", "OPERATING MODE", "DHW HEATING"), "on"),
            ("compressor", ("system_status", "OPERATING MODE", "COMPRESSOR"), "on"),
            ("summer_mode", ("system_status", "OPERATING MODE", "SUMMER MODE"), "on"),
            ("buffer_charging_pump", ("system_status", "SYSTEM STATUS", "BUFFER CHARGING PUMP 1"), "on"),
            ("dhw_charging_pump", ("system_status", "SYSTEM STATUS", "DHW CHARGING PUMP"), "on"),
            ("compressor_output", ("heat_pump_status", "HEAT PUMP STATUS", "OUTPUT COMPRESSOR ON"), "on"),
        ]
        
        for sensor_key, data_path, expected_value in test_cases:
            if sensor_key in BINARY_SENSOR_DESCRIPTIONS:
                description = BINARY_SENSOR_DESCRIPTIONS[sensor_key]
                sensor = ServiceweltBinarySensor(
                    coordinator=mock_coordinator,
                    entity_description=description,
                    sensor_key=sensor_key,
                )
                
                # Verify the mapping returns the expected value
                extracted_value = sensor._extract_sensor_value()
                assert extracted_value == expected_value

    async def test_string_to_boolean_conversion(self, mock_coordinator):
        """Test conversion of string values to boolean."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # Test "on" string converts to True
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = "on"
        assert sensor.is_on is True
        
        # Test "off" string converts to False
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = "off"
        assert sensor.is_on is False
        
        # Test "ON" (uppercase) string converts to True
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = "ON"
        assert sensor.is_on is True
        
        # Test "Off" (mixed case) string converts to False
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = "Off"
        assert sensor.is_on is False

    async def test_boolean_value_handling(self, mock_coordinator):
        """Test handling of actual boolean values."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # Test actual boolean True
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = True
        assert sensor.is_on is True
        
        # Test actual boolean False
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = False
        assert sensor.is_on is False

    async def test_none_value_handling(self, mock_coordinator):
        """Test handling of None values."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # Test None value converts to False
        mock_coordinator.data["system_status"]["OPERATING MODE"]["HEATING CIRCUIT 1 PUMP"] = None
        assert sensor.is_on is False

    async def test_async_setup_entry(self, mock_config_entry):
        """Test async setup entry creates all binary sensors."""
        hass = MagicMock(spec=HomeAssistant)
        entities = []
        
        async def mock_add_entities(entity_list):
            entities.extend(entity_list)
        
        add_entities_callback = AsyncMock(side_effect=mock_add_entities)
        
        await async_setup_entry(hass, mock_config_entry, add_entities_callback)
        
        # Check that entities were created for all binary sensor descriptions
        assert len(entities) == len(BINARY_SENSOR_DESCRIPTIONS)
        
        # Check that all entities are ServiceweltBinarySensor instances
        for entity in entities:
            assert isinstance(entity, ServiceweltBinarySensor)

    async def test_sensor_availability_with_coordinator_data(self, mock_coordinator):
        """Test sensor availability when coordinator has data."""
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # Should have a valid state when data is available
        assert isinstance(sensor.is_on, bool)

    async def test_sensor_unavailability_with_empty_coordinator_data(self, mock_coordinator):
        """Test sensor availability when coordinator has empty data."""
        mock_coordinator.data = {}
        
        description = BINARY_SENSOR_DESCRIPTIONS["heating_circuit_pump"]
        sensor = ServiceweltBinarySensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_circuit_pump",
        )
        
        # Should return False when data is empty
        assert sensor.is_on is False

    async def test_heat_pump_status_sensors(self, mock_coordinator):
        """Test heat pump status sensors from the heat_pump_status page."""
        if "compressor_output" in BINARY_SENSOR_DESCRIPTIONS:
            description = BINARY_SENSOR_DESCRIPTIONS["compressor_output"]
            sensor = ServiceweltBinarySensor(
                coordinator=mock_coordinator,
                entity_description=description,
                sensor_key="compressor_output",
            )
            
            # The mock data has compressor output as "on"
            assert sensor.is_on is True

    async def test_all_binary_sensors_have_valid_mappings(self, mock_coordinator):
        """Test that all binary sensor keys have valid data path mappings."""
        for sensor_key in BINARY_SENSOR_DESCRIPTIONS.keys():
            description = BINARY_SENSOR_DESCRIPTIONS[sensor_key]
            sensor = ServiceweltBinarySensor(
                coordinator=mock_coordinator,
                entity_description=description,
                sensor_key=sensor_key,
            )
            
            # Each sensor should either return a valid value or None
            # (None is acceptable for sensors whose data paths don't exist in mock data)
            extracted_value = sensor._extract_sensor_value()
            assert extracted_value is None or isinstance(extracted_value, (str, bool))
            
            # The is_on property should always return a boolean
            assert isinstance(sensor.is_on, bool)