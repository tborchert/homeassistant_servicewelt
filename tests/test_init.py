"""Test the Servicewelt integration setup and coordinator integration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.servicewelt import async_setup_entry
from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator


@pytest.fixture
def mock_config_entry():
    """Fixture for mocked config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {}
    entry.domain = "servicewelt"
    entry.runtime_data = None
    entry.add_update_listener = MagicMock()
    entry.async_on_unload = MagicMock()
    return entry


@pytest.fixture
def mock_hass():
    """Fixture for mocked Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    return hass


@pytest.mark.asyncio
@patch("custom_components.servicewelt.async_get_clientsession")
@patch("custom_components.servicewelt.async_get_loaded_integration")
async def test_async_setup_entry_success(
    mock_get_integration,
    mock_get_session,
    mock_hass,
    mock_config_entry,
):
    """Test successful setup of config entry with coordinator creation."""
    # Mock dependencies
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    mock_integration = MagicMock()
    mock_get_integration.return_value = mock_integration

    # Mock coordinator first refresh
    with patch.object(
        ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
    ) as mock_refresh:
        mock_refresh.return_value = None

        # Call setup
        result = await async_setup_entry(mock_hass, mock_config_entry)

        # Verify success
        assert result is True

        # Verify coordinator was created
        assert isinstance(
            mock_config_entry.runtime_data.coordinator,
            ServiceweltDataUpdateCoordinator,
        )

        # Verify first refresh was called
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_configuration(mock_hass, mock_config_entry):
    """Test that coordinator is configured correctly."""
    with (
        patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session,
        patch(
            "custom_components.servicewelt.async_get_loaded_integration"
        ) as mock_get_integration,
        patch.object(
            ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
        ),
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_integration.return_value = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data.coordinator

        # Check coordinator configuration
        assert coordinator.name == "servicewelt"
        assert coordinator.update_interval == timedelta(seconds=10)


@pytest.mark.asyncio
@patch("custom_components.servicewelt.async_get_clientsession")
@patch("custom_components.servicewelt.async_get_loaded_integration")
async def test_async_setup_entry_coordinator_refresh_failure(
    mock_get_integration,
    mock_get_session,
    mock_hass,
    mock_config_entry,
):
    """Test setup when coordinator first refresh fails."""
    mock_get_session.return_value = MagicMock()
    mock_get_integration.return_value = MagicMock()

    # Mock coordinator first refresh to raise an exception
    with patch.object(
        ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
    ) as mock_refresh:
        mock_refresh.side_effect = Exception("Connection failed")

        # Setup should raise the exception
        with pytest.raises(Exception, match="Connection failed"):
            await async_setup_entry(mock_hass, mock_config_entry)


@pytest.mark.asyncio
async def test_runtime_data_coordinator_structure(mock_hass, mock_config_entry):
    """Test that runtime data contains properly configured coordinator."""
    with (
        patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session,
        patch(
            "custom_components.servicewelt.async_get_loaded_integration"
        ) as mock_get_integration,
        patch.object(
            ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
        ),
    ):
        mock_get_session.return_value = MagicMock()
        mock_integration = MagicMock()
        mock_get_integration.return_value = mock_integration

        await async_setup_entry(mock_hass, mock_config_entry)

        runtime_data = mock_config_entry.runtime_data

        # Check that runtime data has coordinator
        assert hasattr(runtime_data, "coordinator")

        # Check that coordinator is the correct type
        assert isinstance(runtime_data.coordinator, ServiceweltDataUpdateCoordinator)


@pytest.mark.asyncio
async def test_coordinator_config_entry_reference(mock_hass, mock_config_entry):
    """Test that coordinator has reference to config entry."""
    with (
        patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session,
        patch(
            "custom_components.servicewelt.async_get_loaded_integration"
        ) as mock_get_integration,
        patch.object(
            ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
        ),
    ):
        mock_get_session.return_value = MagicMock()
        mock_get_integration.return_value = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry)

        coordinator = mock_config_entry.runtime_data.coordinator

        # Check that coordinator has reference to config entry
        assert coordinator.config_entry == mock_config_entry
