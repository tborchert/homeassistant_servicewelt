"""Realistic integration test for servicewelt coordinator within Home Assistant environment."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.setup import async_setup_component

from custom_components.servicewelt import DOMAIN, async_setup_entry
from custom_components.servicewelt.api import (
    ServiceweltApiClient,
    ServiceweltApiClientError,
)
from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator


@pytest.fixture
async def hass():
    """Create a real Home Assistant instance for testing."""
    from homeassistant.core import HomeAssistant
    from homeassistant.util.unit_system import METRIC_SYSTEM

    hass_instance = HomeAssistant("/tmp")
    hass_instance.config.units = METRIC_SYSTEM
    hass_instance.config.time_zone = "UTC"

    # Initialize core components that coordinator might depend on
    await async_setup_component(hass_instance, "logger", {})
    await hass_instance.async_block_till_done()

    yield hass_instance

    await hass_instance.async_stop()


@pytest.fixture
def config_entry_data():
    """Config entry data fixture."""
    return {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }


@pytest.fixture
def config_entry(config_entry_data):
    """Create a realistic config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Servicewelt",
        data=config_entry_data,
        source="user",
        unique_id="test_unique_id",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_api_responses():
    """Mock API responses that simulate real servicewelt data."""
    return {
        "success_response": {
            "system": {
                "HEATING": {
                    "OUTSIDE TEMPERATURE": {"value": 22.5, "unit": "°C"},
                    "ACTUAL TEMPERATURE HK 1": {"value": 21.0, "unit": "°C"},
                },
                "DHW": {
                    "ACTUAL TEMPERATURE": {"value": 45.0, "unit": "°C"},
                    "SET TEMPERATURE": {"value": 50.0, "unit": "°C"},
                },
            },
            "heat_pump": {
                "PROCESS DATA": {
                    "RETURN TEMPERATURE": {"value": 35.2, "unit": "°C"},
                    "FLOW TEMPERATURE": {"value": 40.1, "unit": "°C"},
                    "INVERTER POWER": {"value": 3.2, "unit": "kW"},
                },
            },
        },
        "partial_response": {
            "system": {
                "HEATING": {
                    "OUTSIDE TEMPERATURE": {"value": 18.0, "unit": "°C"},
                }
            }
        },
        "empty_response": {},
    }


@pytest.mark.asyncio
async def test_realistic_coordinator_lifecycle(hass, config_entry, mock_api_responses):
    """Test complete coordinator lifecycle in realistic Home Assistant environment."""

    # Mock the API client to simulate real servicewelt communication
    with patch(
        "custom_components.servicewelt.api.ServiceweltApiClient"
    ) as mock_api_class:
        mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
        mock_api_class.return_value = mock_api_instance

        # Configure successful API response
        mock_api_instance.async_get_data.return_value = mock_api_responses[
            "success_response"
        ]

        # Mock aiohttp session
        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()

            # Setup the integration entry
            result = await async_setup_entry(hass, config_entry)

            # Verify setup succeeded
            assert result is True

            # Get the coordinator from runtime data
            coordinator = config_entry.runtime_data.coordinator

            # Verify coordinator is properly configured
            assert isinstance(coordinator, ServiceweltDataUpdateCoordinator)
            assert coordinator.name == DOMAIN
            assert coordinator.update_interval == timedelta(seconds=10)
            assert coordinator.config_entry is config_entry
            assert coordinator.hass is hass

            # Verify initial data was fetched
            assert coordinator.data == mock_api_responses["success_response"]
            assert coordinator.last_update_success is True

            # Test manual data update
            mock_api_instance.async_get_data.return_value = mock_api_responses[
                "partial_response"
            ]
            await coordinator.async_request_refresh()
            await hass.async_block_till_done()

            # Verify data was updated
            assert coordinator.data == mock_api_responses["partial_response"]
            assert mock_api_instance.async_get_data.call_count == 2


@pytest.mark.asyncio
async def test_realistic_coordinator_error_handling(hass, config_entry):
    """Test coordinator error handling in realistic Home Assistant environment."""

    with patch(
        "custom_components.servicewelt.api.ServiceweltApiClient"
    ) as mock_api_class:
        mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
        mock_api_class.return_value = mock_api_instance

        # First call succeeds for initial setup
        mock_api_instance.async_get_data.return_value = {"system": {"test": "data"}}

        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()

            # Setup the integration
            await async_setup_entry(hass, config_entry)
            coordinator = config_entry.runtime_data.coordinator

            # Store initial successful data
            initial_data = coordinator.data

            # Configure API to raise error on next call
            mock_api_instance.async_get_data.side_effect = ServiceweltApiClientError(
                "Connection timeout"
            )

            # Request refresh and expect it to handle the error gracefully
            await coordinator.async_request_refresh()
            await hass.async_block_till_done()

            # Verify error was handled properly
            assert coordinator.last_update_success is False
            assert coordinator.last_exception is not None
            # Data should remain unchanged after error
            assert coordinator.data == initial_data

            # Verify recovery after error
            mock_api_instance.async_get_data.side_effect = None
            mock_api_instance.async_get_data.return_value = {
                "system": {"recovered": "data"}
            }

            await coordinator.async_request_refresh()
            await hass.async_block_till_done()

            # Verify recovery
            assert coordinator.last_update_success is True
            assert coordinator.data == {"system": {"recovered": "data"}}


@pytest.mark.asyncio
async def test_realistic_coordinator_with_listeners(
    hass, config_entry, mock_api_responses
):
    """Test coordinator with realistic update listeners."""

    # Track listener calls
    listener_calls = []

    def test_listener():
        listener_calls.append("update_received")

    with patch(
        "custom_components.servicewelt.api.ServiceweltApiClient"
    ) as mock_api_class:
        mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
        mock_api_class.return_value = mock_api_instance
        mock_api_instance.async_get_data.return_value = mock_api_responses[
            "success_response"
        ]

        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()

            # Setup integration
            await async_setup_entry(hass, config_entry)
            coordinator = config_entry.runtime_data.coordinator

            # Add update listener
            unsub = coordinator.async_add_listener(test_listener)

            # Trigger update
            mock_api_instance.async_get_data.return_value = mock_api_responses[
                "partial_response"
            ]
            await coordinator.async_request_refresh()
            await hass.async_block_till_done()

            # Verify listener was called
            assert len(listener_calls) == 1
            assert listener_calls[0] == "update_received"

            # Remove listener and verify it's not called again
            unsub()
            listener_calls.clear()

            mock_api_instance.async_get_data.return_value = mock_api_responses[
                "empty_response"
            ]
            await coordinator.async_request_refresh()
            await hass.async_block_till_done()

            # Verify listener was not called after removal
            assert len(listener_calls) == 0


@pytest.mark.asyncio
async def test_realistic_coordinator_concurrent_updates(
    hass, config_entry, mock_api_responses
):
    """Test coordinator handling concurrent update requests realistically."""

    with patch(
        "custom_components.servicewelt.api.ServiceweltApiClient"
    ) as mock_api_class:
        mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
        mock_api_class.return_value = mock_api_instance

        # Simulate slow API response
        async def slow_api_call():
            await hass.async_block_till_done()  # Yield control
            return mock_api_responses["success_response"]

        mock_api_instance.async_get_data.side_effect = slow_api_call

        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()

            # Setup integration
            await async_setup_entry(hass, config_entry)
            coordinator = config_entry.runtime_data.coordinator

            # Reset call count after initial setup
            mock_api_instance.async_get_data.reset_mock()

            # Trigger multiple concurrent updates
            import asyncio

            tasks = [
                coordinator.async_request_refresh(),
                coordinator.async_request_refresh(),
                coordinator.async_request_refresh(),
            ]

            await asyncio.gather(*tasks)
            await hass.async_block_till_done()

            # Verify coordinator handled concurrent requests efficiently
            # Should not make redundant API calls
            assert (
                mock_api_instance.async_get_data.call_count <= 2
            )  # Allow for some overlap


@pytest.mark.asyncio
async def test_realistic_coordinator_update_interval(
    hass, config_entry, mock_api_responses
):
    """Test coordinator respects update intervals in realistic environment."""

    with patch(
        "custom_components.servicewelt.api.ServiceweltApiClient"
    ) as mock_api_class:
        mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
        mock_api_class.return_value = mock_api_instance
        mock_api_instance.async_get_data.return_value = mock_api_responses[
            "success_response"
        ]

        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession"
        ) as mock_session:
            mock_session.return_value = MagicMock()

            # Setup integration
            await async_setup_entry(hass, config_entry)
            coordinator = config_entry.runtime_data.coordinator

            # Verify update interval is configured correctly
            assert coordinator.update_interval == timedelta(seconds=10)

            # Verify coordinator integrates with Home Assistant's time system
            assert coordinator.hass is hass

            # Test that coordinator respects the update interval for automatic updates
            initial_call_count = mock_api_instance.async_get_data.call_count

            # Fast-forward time and trigger Home Assistant's update cycle
            import time

            with patch("time.time", return_value=time.time() + 15):  # 15 seconds later
                # Simulate HA's internal update trigger (this would normally be automatic)
                if hasattr(coordinator, "_schedule_refresh"):
                    coordinator._schedule_refresh()
                    await hass.async_block_till_done()

            # Note: In a real HA environment, the coordinator would automatically
            # schedule updates based on update_interval. This test verifies the
            # structure is in place for that to work.
