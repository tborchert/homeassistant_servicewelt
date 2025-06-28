"""Standalone test for HTML parsing functionality."""

from __future__ import annotations

import re
from bs4 import BeautifulSoup
import pytest


class TestHTMLParsing:
    """Test the HTML parsing logic used by the Servicewelt integration."""

    def _parse_html_data(self, html: str) -> dict:
        """Parse HTML and extract sensor data (standalone version)."""
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
        """Parse and convert values to appropriate types (standalone version)."""
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

    @pytest.fixture
    def sample_system_html(self):
        """Sample HTML from the system page."""
        return """
        <html>
        <body>
        <table class="info">
            <tr><th colspan="2" class="round-top">HEATING</th></tr>
            <tr class="even">
                <td class="key">OUTSIDE TEMPERATURE</td>
                <td class="value">26,3°C</td>
            </tr>
            <tr class="odd">
                <td class="key">ACTUAL TEMPERATURE HK 1</td>
                <td class="value">24,5°C</td>
            </tr>
            <tr class="even">
                <td class="key">SET TEMPERATURE HK 1</td>
                <td class="value">5,0°C</td>
            </tr>
        </table>
        <table class="info">
            <tr><th colspan="2" class="round-top">DHW</th></tr>
            <tr class="even">
                <td class="key">ACTUAL TEMPERATURE</td>
                <td class="value">46,2°C</td>
            </tr>
            <tr class="odd">
                <td class="key">SET TEMPERATURE</td>
                <td class="value">52,0°C</td>
            </tr>
        </table>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_heat_pump_html(self):
        """Sample HTML from the heat pump page."""
        return """
        <html>
        <body>
        <table class="info">
            <tr><th colspan="2" class="round-top">PROCESS DATA</th></tr>
            <tr class="even">
                <td class="key">RETURN TEMPERATURE</td>
                <td class="value">47,4°C</td>
            </tr>
            <tr class="odd">
                <td class="key">LOW PRESSURE</td>
                <td class="value">12,43bar</td>
            </tr>
            <tr class="even">
                <td class="key">INVERTER POWER</td>
                <td class="value">2,4kW</td>
            </tr>
            <tr class="odd">
                <td class="key">REL FAN RATE</td>
                <td class="value">40%</td>
            </tr>
        </table>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_status_html(self):
        """Sample HTML from the status page with binary states."""
        return """
        <html>
        <body>
        <table class="info">
            <tr><th colspan="2" class="round-top">OPERATING MODE</th></tr>
            <tr class="even">
                <td class="key">HEATING CIRCUIT 1 PUMP</td>
                <td class="value"><img height="15" src="./pics/ste-symbol_an-97b765.png" /></td>
            </tr>
            <tr class="odd">
                <td class="key">COMPRESSOR</td>
                <td class="value"><img height="15" src="./pics/ste-symbol_an-97b765.png" /></td>
            </tr>
            <tr class="even">
                <td class="key">SUMMER MODE</td>
                <td class="value"><img height="15" src="./pics/ste-symbol_off.png" /></td>
            </tr>
        </table>
        </body>
        </html>
        """

    def test_parse_system_page_temperatures(self, sample_system_html):
        """Test parsing of system page temperature values."""
        parsed_data = self._parse_html_data(sample_system_html)
        
        # Check that heating data is parsed
        assert "HEATING" in parsed_data
        heating_data = parsed_data["HEATING"]
        
        # Check specific temperature values
        assert "OUTSIDE TEMPERATURE" in heating_data
        outside_temp = heating_data["OUTSIDE TEMPERATURE"]
        assert isinstance(outside_temp, dict)
        assert outside_temp["value"] == 26.3
        assert outside_temp["unit"] == "°C"
        
        # Check actual temperature HK1
        assert "ACTUAL TEMPERATURE HK 1" in heating_data
        actual_temp = heating_data["ACTUAL TEMPERATURE HK 1"]
        assert actual_temp["value"] == 24.5
        assert actual_temp["unit"] == "°C"
        
        # Check DHW data
        assert "DHW" in parsed_data
        dhw_data = parsed_data["DHW"]
        assert "ACTUAL TEMPERATURE" in dhw_data
        assert dhw_data["ACTUAL TEMPERATURE"]["value"] == 46.2
        assert "SET TEMPERATURE" in dhw_data
        assert dhw_data["SET TEMPERATURE"]["value"] == 52.0

    def test_parse_heat_pump_process_data(self, sample_heat_pump_html):
        """Test parsing of heat pump process data."""
        parsed_data = self._parse_html_data(sample_heat_pump_html)
        
        # Check process data
        assert "PROCESS DATA" in parsed_data
        process_data = parsed_data["PROCESS DATA"]
        
        # Check temperature
        assert "RETURN TEMPERATURE" in process_data
        assert process_data["RETURN TEMPERATURE"]["value"] == 47.4
        assert process_data["RETURN TEMPERATURE"]["unit"] == "°C"
        
        # Check pressure
        assert "LOW PRESSURE" in process_data
        assert process_data["LOW PRESSURE"]["value"] == 12.43
        assert process_data["LOW PRESSURE"]["unit"] == "bar"
        
        # Check power
        assert "INVERTER POWER" in process_data
        assert process_data["INVERTER POWER"]["value"] == 2.4
        assert process_data["INVERTER POWER"]["unit"] == "kW"
        
        # Check percentage
        assert "REL FAN RATE" in process_data
        assert process_data["REL FAN RATE"]["value"] == 40.0
        assert process_data["REL FAN RATE"]["unit"] == "%"

    def test_parse_binary_states(self, sample_status_html):
        """Test parsing of binary states from images."""
        parsed_data = self._parse_html_data(sample_status_html)
        
        # Check operating mode data
        assert "OPERATING MODE" in parsed_data
        operating_mode = parsed_data["OPERATING MODE"]
        
        # Check 'on' states (symbol_an in image)
        assert "HEATING CIRCUIT 1 PUMP" in operating_mode
        assert operating_mode["HEATING CIRCUIT 1 PUMP"] == "on"
        
        assert "COMPRESSOR" in operating_mode
        assert operating_mode["COMPRESSOR"] == "on"
        
        # Check 'off' state (no symbol_an in image)
        assert "SUMMER MODE" in operating_mode
        assert operating_mode["SUMMER MODE"] == "off"

    def test_parse_value_temperature(self):
        """Test parsing temperature values."""
        result = self._parse_value("26,3°C")
        assert result == {"value": 26.3, "unit": "°C"}

    def test_parse_value_pressure(self):
        """Test parsing pressure values."""
        result = self._parse_value("12,43bar")
        assert result == {"value": 12.43, "unit": "bar"}

    def test_parse_value_percentage(self):
        """Test parsing percentage values."""
        result = self._parse_value("40%")
        assert result == {"value": 40.0, "unit": "%"}

    def test_parse_value_power(self):
        """Test parsing power values."""
        result = self._parse_value("2,4kW")
        assert result == {"value": 2.4, "unit": "kW"}

    def test_parse_value_plain_number(self):
        """Test parsing plain numeric values."""
        result = self._parse_value("123")
        assert result == 123.0

    def test_parse_value_negative_number(self):
        """Test parsing negative values."""
        result = self._parse_value("-4,0°C")
        assert result == {"value": -4.0, "unit": "°C"}

    def test_parse_value_string(self):
        """Test parsing non-numeric string values."""
        result = self._parse_value("Off")
        assert result == "Off"

    def test_parse_value_empty(self):
        """Test parsing empty values."""
        result = self._parse_value("")
        assert result is None

    def test_parse_value_none(self):
        """Test parsing None values."""
        result = self._parse_value(None)
        assert result is None

    def test_parse_complex_units(self):
        """Test parsing complex units."""
        # Test energy units
        result = self._parse_value("10,281MWh")
        assert result == {"value": 10.281, "unit": "MWh"}
        
        # Test current units
        result = self._parse_value("14,4A")
        assert result == {"value": 14.4, "unit": "A"}
        
        # Test voltage units
        result = self._parse_value("238,0V")
        assert result == {"value": 238.0, "unit": "V"}
        
        # Test frequency units
        result = self._parse_value("50Hz")
        assert result == {"value": 50.0, "unit": "Hz"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])