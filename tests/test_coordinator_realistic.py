"""Realistic coordinator tests using Home Assistant's testing utilities."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.servicewelt import DOMAIN
from custom_components.servicewelt.api import (
    ServiceweltApiClient,
    ServiceweltApiClientError,
    ServiceweltApiClientCommunicationError,
)
from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator


@pytest.fixture
async def realistic_hass():
    """Create a minimal but realistic Home Assistant instance."""
    hass = HomeAssistant("/tmp")
    hass.config.time_zone = dt_util.get_default_time_zone()
    await hass.async_start()
    yield hass
    await hass.async_stop()


@pytest.fixture
def realistic_config_entry():
    """Create a realistic config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Servicewelt Heat Pump",
        data={
            CONF_USERNAME: "realistic_user",
            CONF_PASSWORD: "realistic_password",
        },
        source="user",
        unique_id="realistic_unique_id",
        entry_id="realistic_entry_id",
    )


@pytest.fixture
def realistic_api_client():
    """Create a realistic API client mock."""
    client = AsyncMock(spec=ServiceweltApiClient)
    client._username = "realistic_user"
    client._password = "realistic_password"
    client._session = MagicMock()
    return client


@pytest.fixture
def realistic_sample_data():
    """Realistic sample data that mimics actual servicewelt responses."""
    return {
        "system": {
            "HEATING": {
                "OUTSIDE TEMPERATURE": {"value": 15.2, "unit": "°C"},
                "ACTUAL TEMPERATURE HK 1": {"value": 20.5, "unit": "°C"},
                "SET TEMPERATURE HK 1": {"value": 21.0, "unit": "°C"},
                "ACTUAL BUFFER TEMPERATURE": {"value": 35.8, "unit": "°C"},
                "SET BUFFER TEMPERATURE": {"value": 38.0, "unit": "°C"},
            },
            "DHW": {
                "ACTUAL TEMPERATURE": {"value": 48.3, "unit": "°C"},
                "SET TEMPERATURE": {"value": 50.0, "unit": "°C"},
            },
        },
        "heat_pump": {
            "PROCESS DATA": {
                "RETURN TEMPERATURE": {"value": 32.1, "unit": "°C"},
                "FLOW TEMPERATURE": {"value": 38.7, "unit": "°C"},
                "OUTSIDE TEMPERATURE": {"value": 15.1, "unit": "°C"},
                "HOT GAS TEMPERATURE": {"value": 68.4, "unit": "°C"},
                "LOW PRESSURE": {"value": 8.92, "unit": "bar"},
                "HIGH PRESSURE": {"value": 18.45, "unit": "bar"},
                "INVERTER POWER": {"value": 1.8, "unit": "kW"},
                "ACTUAL COMPRESSOR SPEED": {"value": 35, "unit": "Hz"},
            },
            "AMOUNT OF HEAT": {
                "VD HEATING DAY": {"value": 12.5, "unit": "KWh"},
                "VD HEATING TOTAL": {"value": 2547.8, "unit": "KWh"},
                "VD DHW DAY": {"value": 3.2, "unit": "KWh"},
                "VD DHW TOTAL": {"value": 891.4, "unit": "KWh"},
            },
        },
        "system_status": {
            "OPERATING MODE": {
                "HEATING CIRCUIT 1 PUMP": "on",
                "DHW HEATING": "off",
                "COMPRESSOR": "on",
                "SUMMER MODE": "off",
            },
        },
    }


@pytest.mark.asyncio
async def test_realistic_coordinator_full_lifecycle(
    realistic_hass, realistic_config_entry, realistic_api_client, realistic_sample_data
):
    """Test coordinator through a complete realistic lifecycle."""
    
    # Create coordinator with realistic Home Assistant instance
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=realistic_hass,
        logger=realistic_hass.helpers.logger,  # Use HA's logger
        name=DOMAIN,
        update_interval=timedelta(seconds=10),
    )
    
    # Set up realistic config entry relationship
    coordinator.config_entry = realistic_config_entry
    
    # Mock the runtime data with realistic API client
    realistic_config_entry.runtime_data = MagicMock()
    realistic_config_entry.runtime_data.client = realistic_api_client
    
    # Configure successful API response
    realistic_api_client.async_get_data.return_value = realistic_sample_data
    
    # Test initial data fetch (first refresh)
    await coordinator.async_config_entry_first_refresh()
    
    # Verify initial state
    assert coordinator.data == realistic_sample_data
    assert coordinator.last_update_success is True
    assert coordinator.last_exception is None
    assert realistic_api_client.async_get_data.call_count == 1
    
    # Test subsequent data updates
    updated_data = realistic_sample_data.copy()
    updated_data["system"]["HEATING"]["OUTSIDE TEMPERATURE"]["value"] = 12.8
    realistic_api_client.async_get_data.return_value = updated_data
    
    await coordinator.async_refresh()
    
    # Verify update
    assert coordinator.data == updated_data
    assert coordinator.last_update_success is True
    assert realistic_api_client.async_get_data.call_count == 2
    
    # Test coordinator integrates properly with Home Assistant's event loop
    await realistic_hass.async_block_till_done()
    assert coordinator.hass is realistic_hass


@pytest.mark.asyncio
async def test_realistic_coordinator_error_scenarios(
    realistic_hass, realistic_config_entry, realistic_api_client, realistic_sample_data
):
    """Test coordinator handling of realistic error scenarios."""
    
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=realistic_hass,
        logger=realistic_hass.helpers.logger,
        name=DOMAIN,
        update_interval=timedelta(seconds=10),
    )
    coordinator.config_entry = realistic_config_entry
    realistic_config_entry.runtime_data = MagicMock()
    realistic_config_entry.runtime_data.client = realistic_api_client
    
    # Test network timeout error
    realistic_api_client.async_get_data.side_effect = ServiceweltApiClientCommunicationError(
        "Connection timeout after 30 seconds"
    )
    
    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator.async_config_entry_first_refresh()
    
    assert "Connection timeout after 30 seconds" in str(exc_info.value)
    assert coordinator.last_update_success is False
    
    # Test authentication error
    realistic_api_client.async_get_data.side_effect = ServiceweltApiClientError(
        "Authentication failed: Invalid credentials"
    )
    
    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator.async_refresh()
    
    assert "Authentication failed: Invalid credentials" in str(exc_info.value)
    
    # Test recovery after error
    realistic_api_client.async_get_data.side_effect = None
    realistic_api_client.async_get_data.return_value = realistic_sample_data
    
    await coordinator.async_refresh()
    
    # Verify recovery
    assert coordinator.data == realistic_sample_data
    assert coordinator.last_update_success is True


@pytest.mark.asyncio
async def test_realistic_coordinator_data_consistency(
    realistic_hass, realistic_config_entry, realistic_api_client
):
    """Test coordinator maintains data consistency across updates."""
    
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=realistic_hass,
        logger=realistic_hass.helpers.logger,
        name=DOMAIN,
        update_interval=timedelta(seconds=10),
    )
    coordinator.config_entry = realistic_config_entry
    realistic_config_entry.runtime_data = MagicMock()
    realistic_config_entry.runtime_data.client = realistic_api_client
    
    # Test with progressively changing data to simulate real-world updates
    temperature_readings = [18.5, 18.7, 19.2, 19.8, 20.1]
    
    for i, temp in enumerate(temperature_readings):
        data = {
            "system": {
                "HEATING": {
                    "OUTSIDE TEMPERATURE": {"value": temp, "unit": "°C"},
                }
            },
            "timestamp": f"2024-01-01T10:{i:02d}:00Z",  # Realistic timestamp
        }
        
        realistic_api_client.async_get_data.return_value = data
        
        if i == 0:
            await coordinator.async_config_entry_first_refresh()
        else:
            await coordinator.async_refresh()
        
        # Verify data consistency
        assert coordinator.data == data
        assert coordinator.data["system"]["HEATING"]["OUTSIDE TEMPERATURE"]["value"] == temp
        
        # Ensure Home Assistant event loop processes the update
        await realistic_hass.async_block_till_done()
    
    # Verify all updates were processed
    assert realistic_api_client.async_get_data.call_count == len(temperature_readings)


@pytest.mark.asyncio
async def test_realistic_coordinator_update_listeners(
    realistic_hass, realistic_config_entry, realistic_api_client, realistic_sample_data
):
    """Test coordinator update listeners work realistically with Home Assistant."""
    
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=realistic_hass,
        logger=realistic_hass.helpers.logger,
        name=DOMAIN,
        update_interval=timedelta(seconds=10),
    )
    coordinator.config_entry = realistic_config_entry
    realistic_config_entry.runtime_data = MagicMock()
    realistic_config_entry.runtime_data.client = realistic_api_client
    
    # Track listener updates
    listener_updates = []
    
    def update_listener():
        listener_updates.append({
            "data": coordinator.data,
            "success": coordinator.last_update_success,
            "timestamp": dt_util.utcnow().isoformat(),
        })
    
    # Add listener before first refresh
    unsub = coordinator.async_add_listener(update_listener)
    
    # Configure API responses
    realistic_api_client.async_get_data.return_value = realistic_sample_data
    
    # Initial refresh
    await coordinator.async_config_entry_first_refresh()
    await realistic_hass.async_block_till_done()
    
    # Verify listener was called
    assert len(listener_updates) == 1
    assert listener_updates[0]["data"] == realistic_sample_data
    assert listener_updates[0]["success"] is True
    
    # Update data and refresh
    updated_data = realistic_sample_data.copy()
    updated_data["system"]["HEATING"]["OUTSIDE TEMPERATURE"]["value"] = 25.0
    realistic_api_client.async_get_data.return_value = updated_data
    
    await coordinator.async_refresh()
    await realistic_hass.async_block_till_done()
    
    # Verify listener was called again
    assert len(listener_updates) == 2
    assert listener_updates[1]["data"] == updated_data
    
    # Remove listener and verify it stops being called
    unsub()
    
    realistic_api_client.async_get_data.return_value = {"different": "data"}
    await coordinator.async_refresh()
    await realistic_hass.async_block_till_done()
    
    # Listener should not have been called after removal
    assert len(listener_updates) == 2


@pytest.mark.asyncio 
async def test_realistic_coordinator_performance(
    realistic_hass, realistic_config_entry, realistic_api_client, realistic_sample_data
):
    """Test coordinator performance characteristics in realistic conditions."""
    
    coordinator = ServiceweltDataUpdateCoordinator(
        hass=realistic_hass,
        logger=realistic_hass.helpers.logger,
        name=DOMAIN,
        update_interval=timedelta(seconds=10),
    )
    coordinator.config_entry = realistic_config_entry
    realistic_config_entry.runtime_data = MagicMock()
    realistic_config_entry.runtime_data.client = realistic_api_client
    
    # Simulate realistic API response time
    async def simulated_api_call():
        # Simulate 200ms API response time (realistic for local network)
        await realistic_hass.async_add_executor_job(lambda: None)
        return realistic_sample_data
    
    realistic_api_client.async_get_data.side_effect = simulated_api_call
    
    # Measure update performance
    import time
    start_time = time.time()
    
    await coordinator.async_config_entry_first_refresh()
    
    end_time = time.time()
    update_duration = end_time - start_time
    
    # Verify reasonable performance (should complete quickly in test environment)
    assert update_duration < 1.0  # Should complete within 1 second
    assert coordinator.data == realistic_sample_data
    
    # Test concurrent update handling
    realistic_api_client.async_get_data.reset_mock()
    realistic_api_client.async_get_data.side_effect = simulated_api_call
    
    # Trigger multiple rapid updates
    import asyncio
    await asyncio.gather(
        coordinator.async_request_refresh(),
        coordinator.async_request_refresh(),
        coordinator.async_request_refresh(),
    )
    
    # Verify coordinator efficiently handled concurrent requests
    # Should not make excessive API calls
    assert realistic_api_client.async_get_data.call_count <= 2