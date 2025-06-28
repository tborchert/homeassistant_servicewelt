from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator
from custom_components.servicewelt.api import ServiceweltApiClientError


@pytest.fixture
def mock_hass():
    """Fixture for mocked Home Assistant."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Fixture for mocked logger."""
    return MagicMock()


@pytest.fixture
def mock_client():
    """Fixture for mocked API client."""
    client = MagicMock()
    client.async_get_data = AsyncMock()
    return client


@pytest.fixture
def mock_config_entry(mock_client):
    """Fixture for mocked config entry."""
    entry = MagicMock()
    entry.runtime_data.client = mock_client
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_logger, mock_config_entry):
    """Fixture for ServiceweltDataUpdateCoordinator."""
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=mock_hass,
        logger=mock_logger,
        name="servicewelt",
        update_interval=None,
    )
    coordinator.config_entry = mock_config_entry
    return coordinator


@pytest.mark.asyncio
async def test_successful_data_update(coordinator, mock_client, parsed_sample_data):
    """Test successful data update."""
    mock_client.async_get_data.return_value = parsed_sample_data

    result = await coordinator._async_update_data()

    assert result == parsed_sample_data
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_data_update_with_api_error(coordinator, mock_client):
    """Test data update when API raises an error."""
    error_message = "API connection failed"
    mock_client.async_get_data.side_effect = ServiceweltApiClientError(error_message)

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert str(exc_info.value) == error_message
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_data_update_with_communication_error(coordinator, mock_client):
    """Test data update when API raises a communication error."""
    from custom_components.servicewelt.api import ServiceweltApiClientCommunicationError

    error_message = "Network timeout"
    mock_client.async_get_data.side_effect = ServiceweltApiClientCommunicationError(
        error_message
    )

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert str(exc_info.value) == error_message
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_data_update_with_unexpected_error(coordinator, mock_client):
    """Test data update when API raises an unexpected error."""
    error_message = "Unexpected error"
    mock_client.async_get_data.side_effect = Exception(error_message)

    # Should not catch unexpected exceptions, let them bubble up
    with pytest.raises(Exception) as exc_info:
        await coordinator._async_update_data()

    assert str(exc_info.value) == error_message
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_has_config_entry_reference(coordinator, mock_config_entry):
    """Test that coordinator has reference to config entry."""
    assert coordinator.config_entry == mock_config_entry


@pytest.mark.asyncio
async def test_coordinator_uses_client_from_runtime_data(
    coordinator, mock_config_entry, mock_client
):
    """Test that coordinator uses client from config entry runtime data."""
    await coordinator._async_update_data()

    # Should use the client from config_entry.runtime_data
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_data_update_returns_structured_data(coordinator, mock_client):
    """Test that data update returns properly structured data."""
    sample_data = {
        "system": {"HEATING": {"OUTSIDE TEMPERATURE": {"value": 25.0, "unit": "°C"}}},
        "heat_pump": {
            "PROCESS DATA": {"RETURN TEMPERATURE": {"value": 45.0, "unit": "°C"}}
        },
    }

    mock_client.async_get_data.return_value = sample_data

    result = await coordinator._async_update_data()

    assert isinstance(result, dict)
    assert "system" in result
    assert "heat_pump" in result
    assert result["system"]["HEATING"]["OUTSIDE TEMPERATURE"]["value"] == 25.0


@pytest.mark.asyncio
async def test_data_update_handles_empty_response(coordinator, mock_client):
    """Test that data update handles empty response from API."""
    mock_client.async_get_data.return_value = {}

    result = await coordinator._async_update_data()

    assert result == {}
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_data_update_handles_none_response(coordinator, mock_client):
    """Test that data update handles None response from API."""
    mock_client.async_get_data.return_value = None

    result = await coordinator._async_update_data()

    assert result is None
    mock_client.async_get_data.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_consecutive_updates(
    coordinator, mock_client, parsed_sample_data
):
    """Test multiple consecutive data updates."""
    mock_client.async_get_data.return_value = parsed_sample_data

    # First update
    result1 = await coordinator._async_update_data()
    assert result1 == parsed_sample_data

    # Second update
    result2 = await coordinator._async_update_data()
    assert result2 == parsed_sample_data

    # Verify client was called twice
    assert mock_client.async_get_data.call_count == 2


@pytest.mark.asyncio
async def test_update_failure_preserves_previous_data(
    coordinator, mock_client, parsed_sample_data
):
    """Test that update failure doesn't affect coordinator state."""
    # First successful update
    mock_client.async_get_data.return_value = parsed_sample_data
    await coordinator._async_update_data()

    # Second update fails
    mock_client.async_get_data.side_effect = ServiceweltApiClientError(
        "Connection failed"
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Coordinator should still function for next update
    mock_client.async_get_data.side_effect = None
    mock_client.async_get_data.return_value = parsed_sample_data

    result = await coordinator._async_update_data()
    assert result == parsed_sample_data
