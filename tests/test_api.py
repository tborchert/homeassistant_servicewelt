"""Test the Servicewelt API client."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
import aiohttp

from custom_components.servicewelt.api import (
    ServiceweltApiClient,
    ServiceweltApiClientError,
    ServiceweltApiClientCommunicationError,
)


class TestServiceweltApiClient:
    """Test the ServiceweltApiClient."""

    @pytest.fixture
    def mock_session(self):
        """Fixture for mocked aiohttp session."""
        session = MagicMock(spec=aiohttp.ClientSession)
        return session

    @pytest.fixture 
    def api_client(self, mock_session):
        """Fixture for ServiceweltApiClient."""
        return ServiceweltApiClient(
            username="test_user",
            password="test_pass",
            session=mock_session,
        )

    async def test_init(self, api_client):
        """Test API client initialization."""
        assert api_client._username == "test_user"
        assert api_client._password == "test_pass"
        assert api_client._base_url == "https://servicewelt.stiebel-eltron.com"

    async def test_parse_html_data_system_page(self, api_client, sample_html_files):
        """Test parsing of system page HTML data."""
        if "system" not in sample_html_files:
            pytest.skip("System HTML sample not available")
            
        html = sample_html_files["system"]
        parsed_data = api_client._parse_html_data(html)
        
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

    async def test_parse_html_data_heat_pump_page(self, api_client, sample_html_files):
        """Test parsing of heat pump page HTML data."""
        if "heat_pump" not in sample_html_files:
            pytest.skip("Heat pump HTML sample not available")
            
        html = sample_html_files["heat_pump"]
        parsed_data = api_client._parse_html_data(html)
        
        # Check process data
        assert "PROCESS DATA" in parsed_data
        process_data = parsed_data["PROCESS DATA"]
        
        # Check temperature values
        assert "RETURN TEMPERATURE" in process_data
        assert process_data["RETURN TEMPERATURE"]["value"] == 47.4
        
        # Check pressure values
        assert "LOW PRESSURE" in process_data
        assert process_data["LOW PRESSURE"]["value"] == 12.43
        assert process_data["LOW PRESSURE"]["unit"] == "bar"
        
        # Check electrical values
        assert "INVERTER POWER" in process_data
        assert process_data["INVERTER POWER"]["value"] == 2.4
        assert process_data["INVERTER POWER"]["unit"] == "kW"

    async def test_parse_html_data_system_status_page(self, api_client, sample_html_files):
        """Test parsing of system status page HTML data."""
        if "system_status" not in sample_html_files:
            pytest.skip("System status HTML sample not available")
            
        html = sample_html_files["system_status"]
        parsed_data = api_client._parse_html_data(html)
        
        # Check operating mode data (should be binary states)
        assert "OPERATING MODE" in parsed_data
        operating_mode = parsed_data["OPERATING MODE"]
        
        # Check binary states are parsed as 'on'
        assert "HEATING CIRCUIT 1 PUMP" in operating_mode
        assert operating_mode["HEATING CIRCUIT 1 PUMP"] == "on"
        
        assert "COMPRESSOR" in operating_mode
        assert operating_mode["COMPRESSOR"] == "on"

    async def test_parse_value_temperature(self, api_client):
        """Test parsing temperature values."""
        result = api_client._parse_value("26,3°C")
        assert result == {"value": 26.3, "unit": "°C"}

    async def test_parse_value_pressure(self, api_client):
        """Test parsing pressure values."""
        result = api_client._parse_value("12,43bar")
        assert result == {"value": 12.43, "unit": "bar"}

    async def test_parse_value_percentage(self, api_client):
        """Test parsing percentage values.""" 
        result = api_client._parse_value("40%")
        assert result == {"value": 40.0, "unit": "%"}

    async def test_parse_value_plain_number(self, api_client):
        """Test parsing plain numeric values."""
        result = api_client._parse_value("123")
        assert result == 123.0

    async def test_parse_value_string(self, api_client):
        """Test parsing non-numeric string values."""
        result = api_client._parse_value("Off")
        assert result == "Off"

    async def test_parse_value_empty(self, api_client):
        """Test parsing empty values."""
        result = api_client._parse_value("")
        assert result is None

    async def test_async_get_data_success(self, api_client, mock_session, sample_html_files):
        """Test successful data retrieval."""
        # Mock the session request to return HTML content
        mock_response = AsyncMock()
        mock_response.text = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        
        # Set up responses for different pages
        responses = [
            sample_html_files.get("system", "<html></html>"),
            sample_html_files.get("heat_pump", "<html></html>"),
            sample_html_files.get("energy_footprint", "<html></html>"),
            sample_html_files.get("system_status", "<html></html>"),
            sample_html_files.get("heat_pump_status", "<html></html>"),
        ]
        
        mock_response.text.side_effect = responses
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await api_client.async_get_data()
        
        # Check that all pages are requested
        assert mock_session.request.call_count == 5
        
        # Check that result contains all expected page data
        assert "system" in result
        assert "heat_pump" in result
        assert "energy_footprint" in result
        assert "system_status" in result
        assert "heat_pump_status" in result

    async def test_async_get_data_communication_error(self, api_client, mock_session):
        """Test handling of communication errors."""
        mock_session.request = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        
        result = await api_client.async_get_data()
        
        # Check that errors are handled gracefully
        for page_data in result.values():
            assert "error" in page_data

    async def test_async_get_data_timeout_error(self, api_client, mock_session):
        """Test handling of timeout errors."""
        mock_session.request = AsyncMock(side_effect=TimeoutError("Request timed out"))
        
        result = await api_client.async_get_data()
        
        # Check that errors are handled gracefully
        for page_data in result.values():
            assert "error" in page_data

    async def test_fetch_page_success(self, api_client, mock_session):
        """Test successful page fetching."""
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="<html>test</html>")
        mock_response.raise_for_status = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await api_client._fetch_page("?s=1,0")
        
        assert result == "<html>test</html>"
        mock_session.request.assert_called_once_with(
            method="get",
            url="https://servicewelt.stiebel-eltron.com/?s=1,0",
            headers=None,
            json=None,
        )

    async def test_api_wrapper_http_error(self, api_client, mock_session):
        """Test API wrapper handling of HTTP errors."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            None, None, status=404, message="Not Found"
        ))
        mock_session.request = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ServiceweltApiClientCommunicationError):
            await api_client._api_wrapper("get", "https://example.com")

    async def test_api_wrapper_timeout_error(self, api_client, mock_session):
        """Test API wrapper handling of timeout errors."""
        mock_session.request = AsyncMock(side_effect=TimeoutError("Request timed out"))
        
        with pytest.raises(ServiceweltApiClientCommunicationError):
            await api_client._api_wrapper("get", "https://example.com")

    async def test_api_wrapper_generic_error(self, api_client, mock_session):
        """Test API wrapper handling of generic errors."""
        mock_session.request = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with pytest.raises(ServiceweltApiClientError):
            await api_client._api_wrapper("get", "https://example.com")