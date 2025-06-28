"""Simple test for the Servicewelt API client parsing functionality."""

from __future__ import annotations

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add the custom_components directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

# Import after adding to path
from servicewelt.api import ServiceweltApiClient


class TestServiceweltApiClientParsing:
    """Test the ServiceweltApiClient HTML parsing functionality."""

    @pytest.fixture
    def api_client(self):
        """Fixture for ServiceweltApiClient."""
        session = MagicMock()
        return ServiceweltApiClient(
            username="test_user",
            password="test_pass",
            session=session,
        )

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
        </table>
        <table class="info">
            <tr><th colspan="2" class="round-top">DHW</th></tr>
            <tr class="even">
                <td class="key">ACTUAL TEMPERATURE</td>
                <td class="value">46,2°C</td>
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
        </table>
        </body>
        </html>
        """

    def test_api_client_initialization(self, api_client):
        """Test API client initialization."""
        assert api_client._username == "test_user"
        assert api_client._password == "test_pass"
        assert api_client._base_url == "https://servicewelt.stiebel-eltron.com"

    def test_parse_html_data_with_temperatures(self, api_client, sample_system_html):
        """Test parsing HTML data with temperature values."""
        parsed_data = api_client._parse_html_data(sample_system_html)
        
        # Check that heating data is parsed
        assert "HEATING" in parsed_data
        heating_data = parsed_data["HEATING"]
        
        # Check specific temperature values
        assert "OUTSIDE TEMPERATURE" in heating_data
        outside_temp = heating_data["OUTSIDE TEMPERATURE"]
        assert isinstance(outside_temp, dict)
        assert outside_temp["value"] == 26.3
        assert outside_temp["unit"] == "°C"
        
        # Check DHW data
        assert "DHW" in parsed_data
        dhw_data = parsed_data["DHW"]
        assert "ACTUAL TEMPERATURE" in dhw_data
        assert dhw_data["ACTUAL TEMPERATURE"]["value"] == 46.2

    def test_parse_html_data_with_binary_states(self, api_client, sample_status_html):
        """Test parsing HTML data with binary states from images."""
        parsed_data = api_client._parse_html_data(sample_status_html)
        
        # Check operating mode data
        assert "OPERATING MODE" in parsed_data
        operating_mode = parsed_data["OPERATING MODE"]
        
        # Check binary states are parsed as 'on'
        assert "HEATING CIRCUIT 1 PUMP" in operating_mode
        assert operating_mode["HEATING CIRCUIT 1 PUMP"] == "on"
        
        assert "COMPRESSOR" in operating_mode
        assert operating_mode["COMPRESSOR"] == "on"

    def test_parse_value_temperature(self, api_client):
        """Test parsing temperature values."""
        result = api_client._parse_value("26,3°C")
        assert result == {"value": 26.3, "unit": "°C"}

    def test_parse_value_pressure(self, api_client):
        """Test parsing pressure values."""
        result = api_client._parse_value("12,43bar")
        assert result == {"value": 12.43, "unit": "bar"}

    def test_parse_value_percentage(self, api_client):
        """Test parsing percentage values."""
        result = api_client._parse_value("40%")
        assert result == {"value": 40.0, "unit": "%"}

    def test_parse_value_plain_number(self, api_client):
        """Test parsing plain numeric values."""
        result = api_client._parse_value("123")
        assert result == 123.0

    def test_parse_value_string(self, api_client):
        """Test parsing non-numeric string values."""
        result = api_client._parse_value("Off")
        assert result == "Off"

    def test_parse_value_empty(self, api_client):
        """Test parsing empty values."""
        result = api_client._parse_value("")
        assert result is None

    def test_parse_value_none(self, api_client):
        """Test parsing None values."""
        result = api_client._parse_value(None)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])