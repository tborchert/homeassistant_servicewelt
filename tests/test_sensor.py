"""Test the Servicewelt sensor platform."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature, UnitOfPressure, UnitOfEnergy, UnitOfPower

from custom_components.servicewelt.sensor import (
    ServiceweltSensor,
    SENSOR_DESCRIPTIONS,
    async_setup_entry,
)


class TestServiceweltSensor:
    """Test the ServiceweltSensor class."""

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

    async def test_sensor_descriptions_exist(self):
        """Test that sensor descriptions are properly defined."""
        assert len(SENSOR_DESCRIPTIONS) > 0
        
        # Check that key sensors are defined
        assert "outside_temperature" in SENSOR_DESCRIPTIONS
        assert "dhw_actual_temperature" in SENSOR_DESCRIPTIONS
        assert "inverter_power" in SENSOR_DESCRIPTIONS
        assert "low_pressure" in SENSOR_DESCRIPTIONS

    async def test_sensor_descriptions_have_required_fields(self):
        """Test that all sensor descriptions have required fields."""
        for key, description in SENSOR_DESCRIPTIONS.items():
            assert hasattr(description, "key")
            assert hasattr(description, "name")
            assert description.key == key
            assert description.name is not None

    async def test_temperature_sensor_units(self):
        """Test that temperature sensors have correct units."""
        temp_sensors = [
            "outside_temperature",
            "actual_temperature_hk1", 
            "dhw_actual_temperature",
            "return_temperature",
            "flow_temperature",
            "hot_gas_temperature",
        ]
        
        for sensor_key in temp_sensors:
            if sensor_key in SENSOR_DESCRIPTIONS:
                description = SENSOR_DESCRIPTIONS[sensor_key]
                assert description.native_unit_of_measurement == UnitOfTemperature.CELSIUS
                assert description.device_class == "temperature"

    async def test_pressure_sensor_units(self):
        """Test that pressure sensors have correct units."""
        pressure_sensors = ["low_pressure", "high_pressure"]
        
        for sensor_key in pressure_sensors:
            if sensor_key in SENSOR_DESCRIPTIONS:
                description = SENSOR_DESCRIPTIONS[sensor_key]
                assert description.native_unit_of_measurement == UnitOfPressure.BAR
                assert description.device_class == "pressure"

    async def test_energy_sensor_units(self):
        """Test that energy sensors have correct units.""" 
        energy_sensors = ["heating_energy_day", "dhw_energy_day"]
        
        for sensor_key in energy_sensors:
            if sensor_key in SENSOR_DESCRIPTIONS:
                description = SENSOR_DESCRIPTIONS[sensor_key]
                assert description.device_class == "energy"

    async def test_power_sensor_units(self):
        """Test that power sensors have correct units."""
        if "inverter_power" in SENSOR_DESCRIPTIONS:
            description = SENSOR_DESCRIPTIONS["inverter_power"]
            assert description.native_unit_of_measurement == UnitOfPower.KILO_WATT
            assert description.device_class == "power"

    async def test_sensor_initialization(self, mock_coordinator):
        """Test sensor initialization."""
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        assert sensor._sensor_key == "outside_temperature"
        assert sensor.entity_description == description

    async def test_outside_temperature_sensor_value(self, mock_coordinator):
        """Test outside temperature sensor value extraction."""
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        value = sensor.native_value
        assert value == 26.3

    async def test_dhw_temperature_sensor_value(self, mock_coordinator):
        """Test DHW temperature sensor value extraction."""
        description = SENSOR_DESCRIPTIONS["dhw_actual_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="dhw_actual_temperature",
        )
        
        value = sensor.native_value
        assert value == 46.2

    async def test_pressure_sensor_value(self, mock_coordinator):
        """Test pressure sensor value extraction."""
        description = SENSOR_DESCRIPTIONS["low_pressure"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="low_pressure",
        )
        
        value = sensor.native_value
        assert value == 12.43

    async def test_power_sensor_value(self, mock_coordinator):
        """Test power sensor value extraction."""
        description = SENSOR_DESCRIPTIONS["inverter_power"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="inverter_power",
        )
        
        value = sensor.native_value
        assert value == 2.4

    async def test_energy_sensor_value(self, mock_coordinator):
        """Test energy sensor value extraction."""
        description = SENSOR_DESCRIPTIONS["heating_energy_day"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="heating_energy_day",
        )
        
        value = sensor.native_value
        assert value == 0.045

    async def test_sensor_value_no_data(self, mock_coordinator):
        """Test sensor value when coordinator has no data."""
        mock_coordinator.data = None
        
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        value = sensor.native_value
        assert value is None

    async def test_sensor_value_missing_key(self, mock_coordinator):
        """Test sensor value when data key is missing."""
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="nonexistent_sensor",
        )
        
        value = sensor.native_value
        assert value is None

    async def test_extract_sensor_value_mappings(self, mock_coordinator):
        """Test that all sensor key mappings work correctly."""
        # Test a few key mappings to ensure they extract the right data
        test_cases = [
            ("outside_temperature", ("system", "HEATING", "OUTSIDE TEMPERATURE"), 26.3),
            ("dhw_actual_temperature", ("system", "DHW", "ACTUAL TEMPERATURE"), 46.2),
            ("return_temperature", ("heat_pump", "PROCESS DATA", "RETURN TEMPERATURE"), 47.4),
            ("heating_energy_day", ("heat_pump", "AMOUNT OF HEAT", "VD HEATING DAY"), 0.045),
        ]
        
        for sensor_key, data_path, expected_value in test_cases:
            if sensor_key in SENSOR_DESCRIPTIONS:
                description = SENSOR_DESCRIPTIONS[sensor_key]
                sensor = ServiceweltSensor(
                    coordinator=mock_coordinator,
                    entity_description=description,
                    sensor_key=sensor_key,
                )
                
                # Verify the mapping returns the expected value
                extracted_value = sensor._extract_sensor_value()
                if isinstance(extracted_value, dict) and "value" in extracted_value:
                    assert extracted_value["value"] == expected_value
                else:
                    assert extracted_value == expected_value

    async def test_async_setup_entry(self, mock_config_entry):
        """Test async setup entry creates all sensors."""
        hass = MagicMock(spec=HomeAssistant)
        entities = []
        
        async def mock_add_entities(entity_list):
            entities.extend(entity_list)
        
        add_entities_callback = AsyncMock(side_effect=mock_add_entities)
        
        await async_setup_entry(hass, mock_config_entry, add_entities_callback)
        
        # Check that entities were created for all sensor descriptions
        assert len(entities) == len(SENSOR_DESCRIPTIONS)
        
        # Check that all entities are ServiceweltSensor instances
        for entity in entities:
            assert isinstance(entity, ServiceweltSensor)

    async def test_structured_value_extraction(self, mock_coordinator):
        """Test extraction of structured values (dict with value/unit)."""
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        # The mock data has structured values with "value" and "unit" keys
        raw_value = sensor._extract_sensor_value()
        assert isinstance(raw_value, dict)
        assert "value" in raw_value
        assert "unit" in raw_value
        
        # The native_value property should extract just the numeric value
        assert sensor.native_value == raw_value["value"]

    async def test_sensor_availability_with_coordinator_data(self, mock_coordinator):
        """Test sensor availability when coordinator has data."""
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        # Should have a valid value when data is available
        assert sensor.native_value is not None
        assert isinstance(sensor.native_value, (int, float))

    async def test_sensor_unavailability_with_empty_coordinator_data(self, mock_coordinator):
        """Test sensor availability when coordinator has empty data."""
        mock_coordinator.data = {}
        
        description = SENSOR_DESCRIPTIONS["outside_temperature"]
        sensor = ServiceweltSensor(
            coordinator=mock_coordinator,
            entity_description=description,
            sensor_key="outside_temperature",
        )
        
        # Should return None when data is empty
        assert sensor.native_value is None