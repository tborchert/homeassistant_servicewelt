"""Global fixtures for servicewelt coordinator tests."""

import pytest


@pytest.fixture
def parsed_sample_data():
    """Fixture that provides parsed sample data for coordinator testing."""
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
