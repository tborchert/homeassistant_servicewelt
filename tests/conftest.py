"""Global fixtures for servicewelt integration."""

from __future__ import annotations

import pytest
from unittest.mock import patch

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_servicewelt_api():
    """Fixture that mocks the ServiceweltApiClient."""
    with patch("custom_components.servicewelt.api.ServiceweltApiClient") as mock_api:
        yield mock_api


@pytest.fixture
def sample_html_files():
    """Fixture that provides sample HTML file contents."""
    import os
    
    sample_files = {}
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_pages")
    
    files = {
        "s_1_0.html": "system",
        "s_1_1.html": "heat_pump", 
        "s_1_8.html": "energy_footprint",
        "s_2_0.html": "system_status",
        "s_2_2.html": "heat_pump_status",
    }
    
    for filename, key in files.items():
        filepath = os.path.join(sample_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                sample_files[key] = f.read()
    
    return sample_files


@pytest.fixture
def parsed_sample_data():
    """Fixture that provides parsed sample data from HTML files."""
    return {
        "system": {
            "HEATING": {
                "OUTSIDE TEMPERATURE": {"value": 26.3, "unit": "°C"},
                "ACTUAL TEMPERATURE HK 1": {"value": 24.5, "unit": "°C"},
                "SET TEMPERATURE HK 1": {"value": 5.0, "unit": "°C"},
                "ACTUAL BUFFER TEMPERATURE": {"value": 24.5, "unit": "°C"},
                "SET BUFFER TEMPERATURE": {"value": 5.0, "unit": "°C"},
                "FROST PROTECTION": {"value": 4.0, "unit": "°C"},
            },
            "DHW": {
                "ACTUAL TEMPERATURE": {"value": 46.2, "unit": "°C"},
                "SET TEMPERATURE": {"value": 52.0, "unit": "°C"},
            },
            "ELECTRIC BOOSTER HEATER": {
                "DUAL MODE TEMP HZG": {"value": -4.0, "unit": "°C"},
                "LOWER APP LIMIT HZG": {"value": -20.0, "unit": "°C"},
                "DUAL MODE TEMP WW": {"value": -19.5, "unit": "°C"},
                "LOWER APP LIMIT WW": {"value": -20.0, "unit": "°C"},
            },
        },
        "heat_pump": {
            "PROCESS DATA": {
                "RETURN TEMPERATURE": {"value": 47.4, "unit": "°C"},
                "FLOW TEMPERATURE": {"value": 53.1, "unit": "°C"},
                "OUTSIDE TEMPERATURE": {"value": 26.5, "unit": "°C"},
                "HOT GAS TEMPERATURE": {"value": 84.5, "unit": "°C"},
                "LOW PRESSURE": {"value": 12.43, "unit": "bar"},
                "HIGH PRESSURE": {"value": 34.63, "unit": "bar"},
                "INVERTER POWER": {"value": 2.4, "unit": "kW"},
                "INVERTER CURRENT": {"value": 14.4, "unit": "A"},
                "INVERTER VOLTAGE": {"value": 238.0, "unit": "V"},
                "ACTUAL COMPRESSOR SPEED": {"value": 50, "unit": "Hz"},
                "REL FAN RATE": {"value": 40, "unit": "%"},
            },
            "AMOUNT OF HEAT": {
                "VD HEATING DAY": {"value": 0.045, "unit": "KWh"},
                "VD HEATING TOTAL": {"value": 10.281, "unit": "MWh"},
                "VD DHW DAY": {"value": 6.335, "unit": "KWh"},
                "VD DHW TOTAL": {"value": 1.747, "unit": "MWh"},
            },
        },
        "system_status": {
            "OPERATING MODE": {
                "HEATING CIRCUIT 1 PUMP": "on",
                "DHW HEATING": "on",
                "COMPRESSOR": "on",
                "SUMMER MODE": "on",
            },
            "SYSTEM STATUS": {
                "BUFFER CHARGING PUMP 1": "on",
                "DHW CHARGING PUMP": "on",
            },
        },
        "heat_pump_status": {
            "HEAT PUMP STATUS": {
                "COMPRESSOR": "on",
                "OUTPUT COMPRESSOR ON": "on",
            },
        },
    }