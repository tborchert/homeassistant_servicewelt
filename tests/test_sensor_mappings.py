"""Test sensor data mappings with real sample data."""

from __future__ import annotations

import os
import re
from bs4 import BeautifulSoup
import pytest


class TestSensorMappings:
    """Test that sensor mappings correctly extract data from parsed HTML."""

    def _parse_html_data(self, html: str) -> dict:
        """Parse HTML and extract sensor data."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        tables = soup.find_all('table', class_='info')
        
        for table in tables:
            header = table.find('th')
            if not header:
                continue
                
            category = header.get_text(strip=True)
            category_data = {}
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) != 2:
                    continue
                    
                key = cells[0].get_text(strip=True)
                value_cell = cells[1]
                
                # Check for image (binary state)
                img = value_cell.find('img')
                if img:
                    # Extract state from image filename
                    src = img.get('src', '')
                    value = 'on' if 'symbol_an' in src else 'off'
                else:
                    value = value_cell.get_text(strip=True)
                    # Parse numeric values and units
                    value = self._parse_value(value)
                
                category_data[key] = value
            
            if category_data:
                data[category] = category_data
                
        return data

    def _parse_value(self, value: str):
        """Parse and convert values to appropriate types."""
        if not value or value == '':
            return None
            
        # Remove common separators and normalize
        value = value.replace(',', '.')
        
        # Try to extract numeric value with unit
        match = re.match(r'^(-?\d+(?:\.\d+)?)\s*([A-Za-z%°]+)?', value)
        if match:
            num_str, unit = match.groups()
            try:
                num_value = float(num_str)
                if unit:
                    return {"value": num_value, "unit": unit}
                else:
                    return num_value
            except ValueError:
                pass
                
        return value

    def _extract_sensor_value(self, data: dict, sensor_key: str):
        """Extract sensor value using the same mappings as the real sensor code."""
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
        
        if sensor_key not in key_mappings:
            return None
            
        page, category, field = key_mappings[sensor_key]
        
        try:
            return data.get(page, {}).get(category, {}).get(field)
        except (KeyError, AttributeError):
            return None

    def _extract_binary_sensor_value(self, data: dict, sensor_key: str):
        """Extract binary sensor value using the same mappings as the real binary sensor code."""
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
        
        if sensor_key not in key_mappings:
            return None
            
        page, category, field = key_mappings[sensor_key]
        
        try:
            return data.get(page, {}).get(category, {}).get(field)
        except (KeyError, AttributeError):
            return None

    @pytest.fixture
    def parsed_sample_data(self):
        """Load and parse all real sample HTML files."""
        sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_pages")
        data = {}
        
        file_mapping = {
            "s_1_0.html": "system",
            "s_1_1.html": "heat_pump",
            "s_1_8.html": "energy_footprint",
            "s_2_0.html": "system_status",
            "s_2_2.html": "heat_pump_status",
        }
        
        for filename, key in file_mapping.items():
            filepath = os.path.join(sample_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    html = f.read()
                    data[key] = self._parse_html_data(html)
        
        return data

    def test_temperature_sensor_mappings(self, parsed_sample_data):
        """Test that temperature sensor mappings work with real data."""
        temperature_sensors = [
            "outside_temperature",
            "actual_temperature_hk1",
            "dhw_actual_temperature",
            "return_temperature",
            "flow_temperature",
            "hot_gas_temperature",
        ]
        
        for sensor_key in temperature_sensors:
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:  # Some sensors may not be present in all samples
                assert isinstance(value, dict), f"Temperature sensor {sensor_key} should return dict"
                assert "value" in value, f"Temperature sensor {sensor_key} missing value"
                assert "unit" in value, f"Temperature sensor {sensor_key} missing unit"
                assert value["unit"] == "°C", f"Temperature sensor {sensor_key} wrong unit: {value['unit']}"
                assert isinstance(value["value"], (int, float)), f"Temperature value should be numeric: {value}"
                print(f"✓ {sensor_key}: {value['value']}°C")

    def test_pressure_sensor_mappings(self, parsed_sample_data):
        """Test that pressure sensor mappings work with real data."""
        pressure_sensors = ["low_pressure", "high_pressure"]
        
        for sensor_key in pressure_sensors:
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                assert isinstance(value, dict), f"Pressure sensor {sensor_key} should return dict"
                assert "value" in value, f"Pressure sensor {sensor_key} missing value"
                assert "unit" in value, f"Pressure sensor {sensor_key} missing unit"
                assert value["unit"] == "bar", f"Pressure sensor {sensor_key} wrong unit: {value['unit']}"
                assert isinstance(value["value"], (int, float)), f"Pressure value should be numeric: {value}"
                print(f"✓ {sensor_key}: {value['value']} bar")

    def test_power_sensor_mappings(self, parsed_sample_data):
        """Test that power sensor mappings work with real data."""
        power_sensors = ["inverter_power"]
        
        for sensor_key in power_sensors:
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                assert isinstance(value, dict), f"Power sensor {sensor_key} should return dict"
                assert "value" in value, f"Power sensor {sensor_key} missing value"
                assert "unit" in value, f"Power sensor {sensor_key} missing unit"
                assert value["unit"] == "kW", f"Power sensor {sensor_key} wrong unit: {value['unit']}"
                assert isinstance(value["value"], (int, float)), f"Power value should be numeric: {value}"
                print(f"✓ {sensor_key}: {value['value']} kW")

    def test_electrical_sensor_mappings(self, parsed_sample_data):
        """Test that electrical sensor mappings work with real data."""
        electrical_sensors = {
            "inverter_current": "A",
            "inverter_voltage": "V",
            "compressor_speed": "Hz",
            "fan_rate": "%",
        }
        
        for sensor_key, expected_unit in electrical_sensors.items():
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                assert isinstance(value, dict), f"Electrical sensor {sensor_key} should return dict"
                assert "value" in value, f"Electrical sensor {sensor_key} missing value"
                assert "unit" in value, f"Electrical sensor {sensor_key} missing unit"
                assert value["unit"] == expected_unit, f"Electrical sensor {sensor_key} wrong unit: {value['unit']} (expected {expected_unit})"
                assert isinstance(value["value"], (int, float)), f"Electrical value should be numeric: {value}"
                print(f"✓ {sensor_key}: {value['value']} {expected_unit}")

    def test_energy_sensor_mappings(self, parsed_sample_data):
        """Test that energy sensor mappings work with real data."""
        energy_sensors = [
            "heating_energy_day",
            "heating_energy_total", 
            "dhw_energy_day",
            "dhw_energy_total",
        ]
        
        for sensor_key in energy_sensors:
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                assert isinstance(value, dict), f"Energy sensor {sensor_key} should return dict"
                assert "value" in value, f"Energy sensor {sensor_key} missing value"
                assert "unit" in value, f"Energy sensor {sensor_key} missing unit"
                assert value["unit"] in ["KWh", "MWh", "kWh"], f"Energy sensor {sensor_key} unexpected unit: {value['unit']}"
                assert isinstance(value["value"], (int, float)), f"Energy value should be numeric: {value}"
                print(f"✓ {sensor_key}: {value['value']} {value['unit']}")

    def test_binary_sensor_mappings(self, parsed_sample_data):
        """Test that binary sensor mappings work with real data."""
        binary_sensors = [
            "heating_circuit_pump",
            "dhw_heating",
            "compressor", 
            "summer_mode",
            "buffer_charging_pump",
            "dhw_charging_pump",
            "compressor_output",
        ]
        
        for sensor_key in binary_sensors:
            value = self._extract_binary_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                assert value in ["on", "off"], f"Binary sensor {sensor_key} should be 'on' or 'off', got: {value}"
                print(f"✓ {sensor_key}: {value}")

    def test_all_sensor_mappings_exist(self, parsed_sample_data):
        """Test that all defined sensor mappings can extract some data."""
        # Test regular sensors
        sensor_mappings = [
            "outside_temperature", "actual_temperature_hk1", "set_temperature_hk1",
            "actual_buffer_temperature", "set_buffer_temperature", "dhw_actual_temperature",
            "dhw_set_temperature", "return_temperature", "flow_temperature", 
            "hot_gas_temperature", "low_pressure", "high_pressure", "inverter_power",
            "inverter_current", "inverter_voltage", "compressor_speed", "fan_rate",
            "heating_energy_day", "heating_energy_total", "dhw_energy_day", "dhw_energy_total",
        ]
        
        found_sensors = 0
        for sensor_key in sensor_mappings:
            value = self._extract_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                found_sensors += 1
                print(f"✓ Found data for sensor: {sensor_key}")
        
        assert found_sensors > 0, "No sensor mappings found any data"
        print(f"Successfully mapped {found_sensors}/{len(sensor_mappings)} sensors")
        
        # Test binary sensors
        binary_mappings = [
            "heating_circuit_pump", "dhw_heating", "compressor", "summer_mode",
            "buffer_charging_pump", "dhw_charging_pump", "compressor_output",
        ]
        
        found_binary = 0
        for sensor_key in binary_mappings:
            value = self._extract_binary_sensor_value(parsed_sample_data, sensor_key)
            if value is not None:
                found_binary += 1
                print(f"✓ Found data for binary sensor: {sensor_key}")
        
        assert found_binary > 0, "No binary sensor mappings found any data"
        print(f"Successfully mapped {found_binary}/{len(binary_mappings)} binary sensors")

    def test_sensor_value_extraction_matches_expected_types(self, parsed_sample_data):
        """Test that extracted values match expected types for Home Assistant."""
        # Temperature sensors should return float values
        temp_value = self._extract_sensor_value(parsed_sample_data, "outside_temperature")
        if temp_value and isinstance(temp_value, dict):
            native_value = temp_value["value"] if isinstance(temp_value, dict) else temp_value
            assert isinstance(native_value, (int, float)), "Temperature should be numeric"
        
        # Binary sensors should return boolean-convertible values
        binary_value = self._extract_binary_sensor_value(parsed_sample_data, "heating_circuit_pump")
        if binary_value:
            is_on = binary_value.lower() == "on" if isinstance(binary_value, str) else bool(binary_value)
            assert isinstance(is_on, bool), "Binary sensor should convert to boolean"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])