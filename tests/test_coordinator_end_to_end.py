"""End-to-end coordinator test simulating real-world usage patterns."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.servicewelt import DOMAIN, async_setup_entry
from custom_components.servicewelt.api import (
    ServiceweltApiClient,
    ServiceweltApiClientError,
)
from custom_components.servicewelt.coordinator import ServiceweltDataUpdateCoordinator


@pytest.fixture
def real_world_config_entry():
    """Config entry that simulates a real user setup."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Home Heat Pump",
        data={
            CONF_USERNAME: "homeowner@example.com",
            CONF_PASSWORD: "secure_password_123",
        },
        source="user",
        unique_id="heatpump_main_system",
        entry_id="abc123def456",
    )


@pytest.fixture
def daily_temperature_cycle():
    """Simulates a realistic daily temperature cycle for testing."""
    return [
        # Early morning (cold)
        {"outside_temp": 8.2, "flow_temp": 42.1, "return_temp": 35.8, "power": 3.5},
        # Mid morning (warming up)
        {"outside_temp": 12.5, "flow_temp": 38.7, "return_temp": 33.2, "power": 2.8},
        # Midday (warm)
        {"outside_temp": 18.3, "flow_temp": 32.4, "return_temp": 28.9, "power": 1.2},
        # Afternoon (peak warm)
        {"outside_temp": 22.1, "flow_temp": 28.1, "return_temp": 25.3, "power": 0.8},
        # Evening (cooling)
        {"outside_temp": 16.7, "flow_temp": 35.6, "return_temp": 30.1, "power": 2.1},
        # Night (cold again)
        {"outside_temp": 10.3, "flow_temp": 40.8, "return_temp": 34.7, "power": 3.2},
    ]


def create_realistic_data(temp_reading):
    """Create realistic servicewelt data based on temperature reading."""
    return {
        "system": {
            "HEATING": {
                "OUTSIDE TEMPERATURE": {"value": temp_reading["outside_temp"], "unit": "°C"},
                "ACTUAL TEMPERATURE HK 1": {"value": 21.0, "unit": "°C"},
                "SET TEMPERATURE HK 1": {"value": 21.5, "unit": "°C"},
            },
            "DHW": {
                "ACTUAL TEMPERATURE": {"value": 48.5, "unit": "°C"},
                "SET TEMPERATURE": {"value": 50.0, "unit": "°C"},
            },
        },
        "heat_pump": {
            "PROCESS DATA": {
                "RETURN TEMPERATURE": {"value": temp_reading["return_temp"], "unit": "°C"},
                "FLOW TEMPERATURE": {"value": temp_reading["flow_temp"], "unit": "°C"},
                "OUTSIDE TEMPERATURE": {"value": temp_reading["outside_temp"], "unit": "°C"},
                "INVERTER POWER": {"value": temp_reading["power"], "unit": "kW"},
                "LOW PRESSURE": {"value": 8.5 + (temp_reading["power"] * 2), "unit": "bar"},
                "HIGH PRESSURE": {"value": 15.2 + (temp_reading["power"] * 4), "unit": "bar"},
            },
            "AMOUNT OF HEAT": {
                "VD HEATING DAY": {"value": temp_reading["power"] * 2.5, "unit": "KWh"},
                "VD DHW DAY": {"value": 3.8, "unit": "KWh"},
            },
        },
        "system_status": {
            "OPERATING MODE": {
                "HEATING CIRCUIT 1 PUMP": "on" if temp_reading["power"] > 1.0 else "off",
                "DHW HEATING": "on",
                "COMPRESSOR": "on" if temp_reading["power"] > 0.5 else "off",
                "SUMMER MODE": "off" if temp_reading["outside_temp"] < 20 else "on",
            },
        },
    }


@pytest.mark.asyncio
async def test_end_to_end_coordinator_daily_cycle(
    real_world_config_entry, daily_temperature_cycle
):
    """Test coordinator through a complete daily temperature cycle."""
    
    # Create minimal Home Assistant instance
    hass = HomeAssistant("/tmp")
    hass.config.time_zone = dt_util.get_default_time_zone()
    await hass.async_start()
    
    try:
        # Track all coordinator state changes
        coordinator_states = []
        
        def state_tracker():
            if hasattr(coordinator, 'data') and coordinator.data:
                outside_temp = coordinator.data.get("heat_pump", {}).get("PROCESS DATA", {}).get("OUTSIDE TEMPERATURE", {}).get("value", 0)
                power = coordinator.data.get("heat_pump", {}).get("PROCESS DATA", {}).get("INVERTER POWER", {}).get("value", 0)
                coordinator_states.append({
                    "outside_temp": outside_temp,
                    "power": power,
                    "success": coordinator.last_update_success,
                    "timestamp": dt_util.utcnow().isoformat(),
                })
        
        # Mock the API client with realistic responses
        with patch("custom_components.servicewelt.api.ServiceweltApiClient") as mock_api_class:
            mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
            mock_api_class.return_value = mock_api_instance
            
            # Set up initial data
            temp_cycle_iter = iter(daily_temperature_cycle)
            current_temp = next(temp_cycle_iter)
            mock_api_instance.async_get_data.return_value = create_realistic_data(current_temp)
            
            with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
                mock_session.return_value = MagicMock()
                
                # Set up the integration
                result = await async_setup_entry(hass, real_world_config_entry)
                assert result is True
                
                coordinator = real_world_config_entry.runtime_data.coordinator
                
                # Add state tracking listener
                unsub = coordinator.async_add_listener(state_tracker)
                
                # Verify initial setup
                assert isinstance(coordinator, ServiceweltDataUpdateCoordinator)
                assert coordinator.config_entry is real_world_config_entry
                assert coordinator.hass is hass
                
                # Simulate updates throughout the day
                for temp_reading in daily_temperature_cycle:
                    # Update API response for this time period
                    mock_api_instance.async_get_data.return_value = create_realistic_data(temp_reading)
                    
                    # Trigger coordinator update
                    await coordinator.async_request_refresh()
                    await hass.async_block_till_done()
                    
                    # Verify data consistency
                    assert coordinator.last_update_success is True
                    current_data = coordinator.data
                    
                    # Verify realistic data relationships
                    outside_temp = current_data["heat_pump"]["PROCESS DATA"]["OUTSIDE TEMPERATURE"]["value"]
                    power = current_data["heat_pump"]["PROCESS DATA"]["INVERTER POWER"]["value"]
                    
                    assert outside_temp == temp_reading["outside_temp"]
                    assert power == temp_reading["power"]
                    
                    # Verify logical relationships (colder outside = more power needed)
                    if outside_temp < 15:
                        assert power > 2.0  # Should need more power when cold
                    elif outside_temp > 20:
                        assert power < 1.5  # Should need less power when warm
                
                # Verify we tracked all state changes
                assert len(coordinator_states) == len(daily_temperature_cycle)
                
                # Verify realistic temperature progression
                temps = [state["outside_temp"] for state in coordinator_states]
                assert min(temps) < 10  # Had cold periods
                assert max(temps) > 20  # Had warm periods
                
                # Clean up
                unsub()
                
    finally:
        await hass.async_stop()


@pytest.mark.asyncio
async def test_end_to_end_coordinator_error_recovery(real_world_config_entry):
    """Test coordinator error recovery in realistic scenarios."""
    
    hass = HomeAssistant("/tmp")
    await hass.async_start()
    
    try:
        with patch("custom_components.servicewelt.api.ServiceweltApiClient") as mock_api_class:
            mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
            mock_api_class.return_value = mock_api_instance
            
            # Start with successful data
            good_data = create_realistic_data({"outside_temp": 15.0, "flow_temp": 35.0, "return_temp": 30.0, "power": 2.0})
            mock_api_instance.async_get_data.return_value = good_data
            
            with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
                mock_session.return_value = MagicMock()
                
                # Set up integration
                await async_setup_entry(hass, real_world_config_entry)
                coordinator = real_world_config_entry.runtime_data.coordinator
                
                # Verify initial success
                assert coordinator.last_update_success is True
                assert coordinator.data == good_data
                
                # Simulate network error (realistic scenario)
                mock_api_instance.async_get_data.side_effect = ServiceweltApiClientError(
                    "Network unreachable: router offline"
                )
                
                # Attempt update during network error
                await coordinator.async_request_refresh()
                await hass.async_block_till_done()
                
                # Verify error handling
                assert coordinator.last_update_success is False
                assert "Network unreachable" in str(coordinator.last_exception)
                # Data should remain from last successful update
                assert coordinator.data == good_data
                
                # Simulate authentication error (user changed password)
                mock_api_instance.async_get_data.side_effect = ServiceweltApiClientError(
                    "Authentication failed: invalid password"
                )
                
                await coordinator.async_request_refresh()
                await hass.async_block_till_done()
                
                # Still in error state
                assert coordinator.last_update_success is False
                assert "Authentication failed" in str(coordinator.last_exception)
                
                # Simulate recovery (network/auth fixed)
                mock_api_instance.async_get_data.side_effect = None
                recovery_data = create_realistic_data({"outside_temp": 18.0, "flow_temp": 32.0, "return_temp": 28.0, "power": 1.5})
                mock_api_instance.async_get_data.return_value = recovery_data
                
                await coordinator.async_request_refresh()
                await hass.async_block_till_done()
                
                # Verify full recovery
                assert coordinator.last_update_success is True
                assert coordinator.last_exception is None
                assert coordinator.data == recovery_data
                
    finally:
        await hass.async_stop()


@pytest.mark.asyncio
async def test_end_to_end_coordinator_realistic_timing(real_world_config_entry):
    """Test coordinator with realistic timing and update intervals."""
    
    hass = HomeAssistant("/tmp")
    await hass.async_start()
    
    try:
        with patch("custom_components.servicewelt.api.ServiceweltApiClient") as mock_api_class:
            mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
            mock_api_class.return_value = mock_api_instance
            
            # Simulate realistic API response timing
            call_count = 0
            async def timed_api_response():
                nonlocal call_count
                call_count += 1
                # Simulate variable response times (realistic network conditions)
                if call_count % 3 == 0:
                    # Occasionally slower (realistic network variation)
                    await hass.async_add_executor_job(lambda: None)
                
                return create_realistic_data({
                    "outside_temp": 15.0 + call_count,
                    "flow_temp": 35.0,
                    "return_temp": 30.0,
                    "power": 2.0
                })
            
            mock_api_instance.async_get_data.side_effect = timed_api_response
            
            with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
                mock_session.return_value = MagicMock()
                
                # Set up integration
                await async_setup_entry(hass, real_world_config_entry)
                coordinator = real_world_config_entry.runtime_data.coordinator
                
                # Verify configured update interval
                assert coordinator.update_interval == timedelta(seconds=10)
                
                # Test rapid successive updates (user manually refreshing)
                import asyncio
                import time
                
                start_time = time.time()
                
                # Simulate user hitting refresh multiple times rapidly
                await asyncio.gather(
                    coordinator.async_request_refresh(),
                    coordinator.async_request_refresh(),
                    coordinator.async_request_refresh(),
                )
                
                end_time = time.time()
                
                # Should complete efficiently despite multiple requests
                assert (end_time - start_time) < 2.0
                assert coordinator.last_update_success is True
                
                # Verify coordinator didn't make excessive API calls
                # (should deduplicate concurrent requests)
                assert call_count <= 3  # Initial setup + efficient request handling
                
                # Test that coordinator properly spaces automatic updates
                initial_call_count = call_count
                
                # Multiple refresh requests in short succession
                for _ in range(5):
                    await coordinator.async_request_refresh()
                    await asyncio.sleep(0.1)  # Brief pause between requests
                
                await hass.async_block_till_done()
                
                # Should handle requests efficiently
                final_call_count = call_count
                assert (final_call_count - initial_call_count) <= 5
                
    finally:
        await hass.async_stop()


@pytest.mark.asyncio
async def test_end_to_end_coordinator_data_validation(real_world_config_entry):
    """Test coordinator with realistic data validation scenarios."""
    
    hass = HomeAssistant("/tmp")
    await hass.async_start()
    
    try:
        with patch("custom_components.servicewelt.api.ServiceweltApiClient") as mock_api_class:
            mock_api_instance = AsyncMock(spec=ServiceweltApiClient)
            mock_api_class.return_value = mock_api_instance
            
            with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
                mock_session.return_value = MagicMock()
                
                # Test with complete valid data
                complete_data = create_realistic_data({"outside_temp": 15.0, "flow_temp": 35.0, "return_temp": 30.0, "power": 2.0})
                mock_api_instance.async_get_data.return_value = complete_data
                
                await async_setup_entry(hass, real_world_config_entry)
                coordinator = real_world_config_entry.runtime_data.coordinator
                
                assert coordinator.data == complete_data
                
                # Test with partial data (realistic for device going offline)
                partial_data = {
                    "system": {
                        "HEATING": {
                            "OUTSIDE TEMPERATURE": {"value": 16.0, "unit": "°C"},
                        }
                    }
                }
                mock_api_instance.async_get_data.return_value = partial_data
                
                await coordinator.async_refresh()
                await hass.async_block_till_done()
                
                # Coordinator should accept partial data
                assert coordinator.data == partial_data
                assert coordinator.last_update_success is True
                
                # Test with empty data (device communication lost)
                mock_api_instance.async_get_data.return_value = {}
                
                await coordinator.async_refresh()
                await hass.async_block_till_done()
                
                # Should handle empty data gracefully
                assert coordinator.data == {}
                assert coordinator.last_update_success is True
                
                # Test with None response (complete communication failure)
                mock_api_instance.async_get_data.return_value = None
                
                await coordinator.async_refresh()
                await hass.async_block_till_done()
                
                # Should handle None gracefully
                assert coordinator.data is None
                assert coordinator.last_update_success is True
                
    finally:
        await hass.async_stop()