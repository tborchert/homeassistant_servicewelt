"""Test the Servicewelt integration setup."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from custom_components.servicewelt import (
    PLATFORMS,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.servicewelt.api import ServiceweltApiClient
from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator


class TestServiceweltIntegration:
    """Test the Servicewelt integration setup and teardown."""

    @pytest.fixture
    def mock_config_entry(self):
        """Fixture for mocked config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }
        entry.domain = "servicewelt"
        entry.runtime_data = None
        entry.add_update_listener = MagicMock()
        entry.async_on_unload = MagicMock()
        return entry

    @pytest.fixture
    def mock_hass(self):
        """Fixture for mocked Home Assistant."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        return hass

    async def test_platforms_defined(self):
        """Test that all required platforms are defined."""
        expected_platforms = [
            Platform.SENSOR,
            Platform.BINARY_SENSOR,
            Platform.SWITCH,
        ]

        assert PLATFORMS == expected_platforms

    @patch("custom_components.servicewelt.async_get_clientsession")
    @patch("custom_components.servicewelt.async_get_loaded_integration")
    async def test_async_setup_entry_success(
        self,
        mock_get_integration,
        mock_get_session,
        mock_hass,
        mock_config_entry,
    ):
        """Test successful setup of config entry."""
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

            # Verify runtime data was set
            assert mock_config_entry.runtime_data is not None
            assert hasattr(mock_config_entry.runtime_data, "client")
            assert hasattr(mock_config_entry.runtime_data, "coordinator")
            assert hasattr(mock_config_entry.runtime_data, "integration")

            # Verify API client was created with correct parameters
            assert isinstance(
                mock_config_entry.runtime_data.client, ServiceweltApiClient
            )

            # Verify coordinator was created
            assert isinstance(
                mock_config_entry.runtime_data.coordinator,
                ServiceweltDataUpdateCoordinator,
            )

            # Verify first refresh was called
            mock_refresh.assert_called_once()

            # Verify platforms were set up
            mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
                mock_config_entry, PLATFORMS
            )

            # Verify update listener was added
            mock_config_entry.async_on_unload.assert_called_once()

    async def test_coordinator_configuration(self, mock_hass, mock_config_entry):
        """Test that coordinator is configured correctly."""
        with patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session:
            with patch(
                "custom_components.servicewelt.async_get_loaded_integration"
            ) as mock_get_integration:
                with patch.object(
                    ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
                ):
                    mock_get_session.return_value = MagicMock()
                    mock_get_integration.return_value = MagicMock()

                    await async_setup_entry(mock_hass, mock_config_entry)

                    coordinator = mock_config_entry.runtime_data.coordinator

                    # Check coordinator configuration
                    assert coordinator.name == "servicewelt"
                    assert coordinator.update_interval == timedelta(seconds=10)

    async def test_api_client_configuration(self, mock_hass, mock_config_entry):
        """Test that API client is configured correctly."""
        mock_session = MagicMock()

        with patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session:
            with patch(
                "custom_components.servicewelt.async_get_loaded_integration"
            ) as mock_get_integration:
                with patch.object(
                    ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
                ):
                    mock_get_session.return_value = mock_session
                    mock_get_integration.return_value = MagicMock()

                    await async_setup_entry(mock_hass, mock_config_entry)

                    client = mock_config_entry.runtime_data.client

                    # Check API client configuration
                    assert client._username == "test_user"
                    assert client._password == "test_password"
                    assert client._session == mock_session

    @patch("custom_components.servicewelt.async_get_clientsession")
    @patch("custom_components.servicewelt.async_get_loaded_integration")
    async def test_async_setup_entry_coordinator_refresh_failure(
        self,
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

    async def test_async_unload_entry(self, mock_hass, mock_config_entry):
        """Test unloading of config entry."""
        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )

    async def test_async_unload_entry_failure(self, mock_hass, mock_config_entry):
        """Test unloading failure."""
        mock_hass.config_entries.async_unload_platforms.return_value = False

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is False

    async def test_async_reload_entry(self, mock_hass, mock_config_entry):
        """Test reloading of config entry."""
        with patch("custom_components.servicewelt.async_unload_entry") as mock_unload:
            with patch("custom_components.servicewelt.async_setup_entry") as mock_setup:
                mock_unload.return_value = True
                mock_setup.return_value = True

                await async_reload_entry(mock_hass, mock_config_entry)

                mock_unload.assert_called_once_with(mock_hass, mock_config_entry)
                mock_setup.assert_called_once_with(mock_hass, mock_config_entry)

    async def test_runtime_data_structure(self, mock_hass, mock_config_entry):
        """Test that runtime data has the expected structure."""
        with patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session:
            with patch(
                "custom_components.servicewelt.async_get_loaded_integration"
            ) as mock_get_integration:
                with patch.object(
                    ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
                ):
                    mock_get_session.return_value = MagicMock()
                    mock_integration = MagicMock()
                    mock_get_integration.return_value = mock_integration

                    await async_setup_entry(mock_hass, mock_config_entry)

                    runtime_data = mock_config_entry.runtime_data

                    # Check that runtime data has all required attributes
                    assert hasattr(runtime_data, "client")
                    assert hasattr(runtime_data, "coordinator")
                    assert hasattr(runtime_data, "integration")

                    # Check that they are the correct types
                    assert isinstance(runtime_data.client, ServiceweltApiClient)
                    assert isinstance(
                        runtime_data.coordinator, ServiceweltDataUpdateCoordinator
                    )
                    assert runtime_data.integration == mock_integration

    async def test_coordinator_config_entry_reference(
        self, mock_hass, mock_config_entry
    ):
        """Test that coordinator has reference to config entry."""
        with patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session:
            with patch(
                "custom_components.servicewelt.async_get_loaded_integration"
            ) as mock_get_integration:
                with patch.object(
                    ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
                ):
                    mock_get_session.return_value = MagicMock()
                    mock_get_integration.return_value = MagicMock()

                    await async_setup_entry(mock_hass, mock_config_entry)

                    coordinator = mock_config_entry.runtime_data.coordinator

                    # Check that coordinator has reference to config entry
                    assert coordinator.config_entry == mock_config_entry

    async def test_update_listener_callback(self, mock_hass, mock_config_entry):
        """Test that update listener callback is properly set."""
        with patch(
            "custom_components.servicewelt.async_get_clientsession"
        ) as mock_get_session:
            with patch(
                "custom_components.servicewelt.async_get_loaded_integration"
            ) as mock_get_integration:
                with patch.object(
                    ServiceweltDataUpdateCoordinator, "async_config_entry_first_refresh"
                ):
                    mock_get_session.return_value = MagicMock()
                    mock_get_integration.return_value = MagicMock()

                    await async_setup_entry(mock_hass, mock_config_entry)

                    # Verify that add_update_listener was called with async_reload_entry
                    mock_config_entry.add_update_listener.assert_called_once()

                    # Get the callback that was passed to add_update_listener
                    callback = mock_config_entry.add_update_listener.call_args[0][0]

                    # Verify it's the async_reload_entry function
                    from custom_components.servicewelt import async_reload_entry

                    assert callback == async_reload_entry
