"""
End-to-end tests: real Home Assistant polling a fake Servicewelt portal.

Expected values are read off the captured pages in ``sample_pages/`` by hand,
so they are an independent check of the scraper rather than a copy of it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from .conftest import PORTAL_HOST_FOR_HA, HomeAssistant, Portal, ha_logs_since, wait_for

# Polling interval is 10s; allow for one missed poll plus slack.
POLL_TIMEOUT = 30

# friendly name -> (state, unit_of_measurement)
EXPECTED_SENSORS = {
    # ?s=1,0 SYSTEM
    "Outside Temperature": ("26.3", "°C"),
    "Actual Temperature HK1": ("24.5", "°C"),
    "Set Temperature HK1": ("5.0", "°C"),
    "Actual Buffer Temperature": ("24.5", "°C"),
    "Set Buffer Temperature": ("5.0", "°C"),
    "DHW Actual Temperature": ("46.2", "°C"),
    "DHW Set Temperature": ("52.0", "°C"),
    # ?s=1,1 HEAT PUMP / PROCESS DATA
    "Return Temperature": ("47.4", "°C"),
    "Flow Temperature": ("53.1", "°C"),
    "Hot Gas Temperature": ("84.5", "°C"),
    "Low Pressure": ("12.43", "bar"),
    "High Pressure": ("34.63", "bar"),
    "Inverter Power": ("2.4", "kW"),
    "Inverter Current": ("14.4", "A"),
    "Inverter Voltage": ("238.0", "V"),
    "Compressor Speed": ("50.0", "Hz"),
    "Fan Rate": ("40.0", "%"),
    # ?s=1,1 HEAT PUMP / AMOUNT OF HEAT
    "Heating Energy Today": ("0.045", "kWh"),
    "Heating Energy Total": ("10.281", "MWh"),
    "DHW Energy Today": ("6.335", "kWh"),
    "DHW Energy Total": ("1.747", "MWh"),
}

# ?s=2,0 and ?s=2,2: every indicator in the samples shows the "an" (on) symbol
EXPECTED_BINARY_SENSORS = {
    "Heating Circuit 1 Pump": "on",
    "DHW Heating": "on",
    "Compressor": "on",
    "Summer Mode": "on",
    "Buffer Charging Pump 1": "on",
    "DHW Charging Pump": "on",
    "Compressor Output": "on",
}

PORTAL_PAGES = {"1,0", "1,1", "1,8", "2,0", "2,2"}


def _state(ha: HomeAssistant, name: str) -> dict[str, Any]:
    return ha.servicewelt_states()[name]


def test_config_flow_form_defaults_to_local_portal(ha: HomeAssistant) -> None:
    flow = ha.start_flow()
    try:
        assert flow["type"] == "form"
        assert flow["step_id"] == "user"
        fields = {f["name"]: f for f in flow["data_schema"]}
        assert set(fields) == {"host"}
        assert fields["host"]["default"] == "http://servicewelt"
    finally:
        ha.http.delete(f"/api/config/config_entries/flow/{flow['flow_id']}")


def test_all_entities_report_sample_values(
    ha: HomeAssistant,
    portal: Portal,
    entry: dict[str, Any],
) -> None:
    assert entry["title"] == PORTAL_HOST_FOR_HA
    states = ha.servicewelt_states()

    assert set(states) == set(EXPECTED_SENSORS) | set(EXPECTED_BINARY_SENSORS)
    assert len({s["entity_id"] for s in states.values()}) == len(states)

    actual_sensors = {
        name: (
            states[name]["state"],
            states[name]["attributes"].get("unit_of_measurement"),
        )
        for name in EXPECTED_SENSORS
    }
    assert actual_sensors == EXPECTED_SENSORS

    actual_binary = {name: states[name]["state"] for name in EXPECTED_BINARY_SENSORS}
    assert actual_binary == EXPECTED_BINARY_SENSORS

    assert set(portal.requests()) >= PORTAL_PAGES


def test_happy_path_logs_no_errors(ha: HomeAssistant, portal: Portal) -> None:
    started = datetime.now(UTC)
    flow = ha.start_flow()
    result = ha.submit_flow(
        flow["flow_id"],
        {"host": PORTAL_HOST_FOR_HA},
    )
    assert result["type"] == "create_entry", result
    try:
        # Let a couple of polls happen
        wait_for(
            lambda: portal.requests().count("1,0") >= 3,
            timeout=POLL_TIMEOUT,
            message="three polls of ?s=1,0",
        )
        errors = [
            line
            for line in ha_logs_since(started).splitlines()
            if ("ERROR" in line or "Traceback" in line)
            and "servicewelt" in line.lower()
        ]
        assert errors == []
    finally:
        ha.delete_entry(result["result"]["entry_id"])


def test_values_follow_portal_on_next_poll(
    ha: HomeAssistant,
    portal: Portal,
    entry: dict[str, Any],  # noqa: ARG001
) -> None:
    assert _state(ha, "Outside Temperature")["state"] == "26.3"

    portal.override("1,0", replace=[["26,3°C", "-7,5°C"]])

    wait_for(
        lambda: _state(ha, "Outside Temperature")["state"] == "-7.5",
        timeout=POLL_TIMEOUT,
        message="outside temperature to become -7.5",
    )
    # Untouched values on the same page stay put
    assert _state(ha, "DHW Actual Temperature")["state"] == "46.2"


def test_binary_sensor_turns_off(
    ha: HomeAssistant,
    portal: Portal,
    entry: dict[str, Any],  # noqa: ARG001
) -> None:
    assert _state(ha, "Compressor Output")["state"] == "on"

    portal.override("2,2", replace=[["ste-symbol_an-", "ste-symbol_aus-"]])

    wait_for(
        lambda: _state(ha, "Compressor Output")["state"] == "off",
        timeout=POLL_TIMEOUT,
        message="compressor output to turn off",
    )
    # Page 2,0 was not changed
    assert _state(ha, "Compressor")["state"] == "on"


@pytest.mark.parametrize("override", [{"status": 500}, {"delay": 15}])
def test_portal_outage_marks_unavailable_then_recovers(
    ha: HomeAssistant,
    portal: Portal,
    entry: dict[str, Any],  # noqa: ARG001
    override: dict[str, Any],
) -> None:
    portal.override("1,1", **override)

    wait_for(
        lambda: all(
            s["state"] == "unavailable" for s in ha.servicewelt_states().values()
        ),
        timeout=POLL_TIMEOUT + 15,
        message="all entities to become unavailable",
    )

    portal.reset()

    wait_for(
        lambda: _state(ha, "Flow Temperature")["state"] == "53.1",
        timeout=POLL_TIMEOUT + 15,
        message="entities to recover",
    )


def test_config_flow_reports_unreachable_portal(
    ha: HomeAssistant,
    portal: Portal,  # noqa: ARG001
) -> None:
    flow = ha.start_flow()
    try:
        result = ha.submit_flow(
            flow["flow_id"],
            {
                "host": "http://nothing-here.invalid",
            },
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "connection"}
    finally:
        ha.http.delete(f"/api/config/config_entries/flow/{flow['flow_id']}")
    assert ha.config_entries() == []


def test_config_flow_reports_portal_error(ha: HomeAssistant, portal: Portal) -> None:
    portal.override("1,0", status=503)
    flow = ha.start_flow()
    try:
        result = ha.submit_flow(
            flow["flow_id"],
            {"host": PORTAL_HOST_FOR_HA},
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "connection"}
    finally:
        ha.http.delete(f"/api/config/config_entries/flow/{flow['flow_id']}")


def test_second_entry_for_same_portal_is_rejected(
    ha: HomeAssistant,
    entry: dict[str, Any],  # noqa: ARG001
) -> None:
    flow = ha.start_flow()
    result = ha.submit_flow(
        flow["flow_id"],
        {"host": PORTAL_HOST_FOR_HA},
    )
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    assert len(ha.config_entries()) == 1


def test_removing_entry_removes_entities(
    ha: HomeAssistant,
    entry: dict[str, Any],
) -> None:
    assert ha.servicewelt_entity_ids()

    ha.delete_entry(entry["entry_id"])

    wait_for(
        lambda: not ha.servicewelt_entity_ids(),
        timeout=10,
        message="servicewelt entities to be removed",
    )
