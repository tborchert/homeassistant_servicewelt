"""
In-process integration tests on a real Home Assistant test instance.

Uses pytest-homeassistant-custom-component: ``hass`` is a fully bootstrapped
HA, and ``aioclient_mock`` replaces HA's aiohttp session so the captured
``sample_pages/`` are served for ``http://servicewelt/?s=...``. Faster than
the Docker suite in ``tests/e2e`` and runs anywhere, but nothing goes over
a real network.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_HOST,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.servicewelt.api import ServiceweltApiClient
from custom_components.servicewelt.const import DEFAULT_HOST, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

SAMPLE_PAGES = Path(__file__).parent.parent / "sample_pages"
PAGES = ("1,0", "1,1", "1,8", "2,0", "2,2")
ENTRY_DATA = {CONF_HOST: DEFAULT_HOST}
POLL_INTERVAL = timedelta(seconds=10)


def sample(page: str) -> str:
    return (SAMPLE_PAGES / f"s_{page.replace(',', '_')}.html").read_text()


def serve(
    aioclient_mock: AiohttpClientMocker,
    replace: dict[str, list[tuple[str, str]]] | None = None,
    status: dict[str, int] | None = None,
) -> None:
    """Serve the sample pages, optionally with edits or error statuses."""
    aioclient_mock.clear_requests()
    for page in PAGES:
        html = sample(page)
        for old, new in (replace or {}).get(page, []):
            html = html.replace(old, new)
        aioclient_mock.get(
            f"{DEFAULT_HOST}/?s={page}",
            text=html,
            status=(status or {}).get(page, 200),
        )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let HA load custom_components/servicewelt."""


@pytest.fixture
async def entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    serve(aioclient_mock)
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id="http-servicewelt"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def poll(hass: HomeAssistant) -> None:
    """Advance time past one polling interval and let the refresh run."""
    async_fire_time_changed(hass, dt_util.utcnow() + POLL_INTERVAL)
    await hass.async_block_till_done()


# --- scraper ---------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_parser_extracts_every_row_of_sample_page(page: str) -> None:
    client = ServiceweltApiClient(session=None)  # type: ignore[arg-type]
    html = sample(page)

    parsed = client._parse_html_data(html)

    rows = sum(len(category) for category in parsed.values())
    assert parsed, "no tables found"
    # Every key/value row on the page ends up in exactly one category. Pages
    # can repeat a key in different tables (1,1 has VD HEATING DAY twice).
    assert rows == html.count('class="key')


def test_parser_converts_values() -> None:
    client = ServiceweltApiClient(session=None)  # type: ignore[arg-type]

    system = client._parse_html_data(sample("1,0"))
    heat_pump = client._parse_html_data(sample("1,1"))
    status = client._parse_html_data(sample("2,0"))

    assert system["HEATING"]["OUTSIDE TEMPERATURE"] == {"value": 26.3, "unit": "°C"}
    assert system["ELECTRIC BOOSTER HEATER"]["DUAL MODE TEMP HZG"] == {
        "value": -4.0,
        "unit": "°C",
    }
    assert system["HEATING"]["FIXED VALUE OPERATION"] == "Off"
    assert system["ENERGIEMANAGEMENT"]["SG READY 1"] == 0.0
    assert heat_pump["PROCESS DATA"]["LOW PRESSURE"] == {"value": 12.43, "unit": "bar"}
    assert heat_pump["AMOUNT OF HEAT"]["VD HEATING DAY"] == {
        "value": 0.045,
        "unit": "KWh",
    }
    # The same key in a later table does not overwrite the first one
    assert heat_pump["POWER CONSUMPTION"]["VD HEATING DAY"] == {
        "value": 0.0,
        "unit": "KWh",
    }
    assert status["OPERATING MODE"]["COMPRESSOR"] == "on"


# --- setup and entities ----------------------------------------------------


async def test_setup_creates_entities_with_sample_values(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.outside_temperature").state == "26.3"
    assert hass.states.get("sensor.dhw_actual_temperature").state == "46.2"
    assert hass.states.get("sensor.inverter_power").state == "2.4"
    assert hass.states.get("sensor.heating_energy_total").state == "10.281"
    assert hass.states.get("binary_sensor.compressor_output").state == STATE_ON

    entity_ids = hass.states.async_entity_ids()
    assert len([e for e in entity_ids if e.startswith("sensor.")]) == 21
    assert len([e for e in entity_ids if e.startswith("binary_sensor.")]) == 7


async def test_each_poll_fetches_every_page(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == len(PAGES)

    await poll(hass)

    assert aioclient_mock.call_count == 2 * len(PAGES)
    assert {str(url) for _, url, _, _ in aioclient_mock.mock_calls} == {
        f"{DEFAULT_HOST}/?s={page}" for page in PAGES
    }


async def test_poll_updates_entity_state(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    assert entry.state is ConfigEntryState.LOADED
    serve(aioclient_mock, replace={"1,0": [("26,3°C", "-7,5°C")]})

    await poll(hass)

    assert hass.states.get("sensor.outside_temperature").state == "-7.5"
    assert hass.states.get("sensor.dhw_actual_temperature").state == "46.2"


async def test_poll_failure_marks_entities_unavailable_then_recovers(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    assert entry.state is ConfigEntryState.LOADED
    serve(aioclient_mock, status={"1,1": 500})

    await poll(hass)

    assert hass.states.get("sensor.outside_temperature").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.compressor").state == STATE_UNAVAILABLE

    serve(aioclient_mock)
    await poll(hass)

    assert hass.states.get("sensor.flow_temperature").state == "53.1"


async def test_setup_retries_when_portal_is_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    serve(aioclient_mock, status={"1,0": 503})
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_entry_without_host_uses_default(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Entries created before the host option existed keep working."""
    serve(aioclient_mock)
    data = {k: v for k, v in ENTRY_DATA.items() if k != CONF_HOST}
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


async def test_unload_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get("sensor.outside_temperature").state == STATE_UNAVAILABLE


# --- config flow -----------------------------------------------------------


async def test_config_flow_creates_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    serve(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], ENTRY_DATA
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_HOST
    assert result["data"] == ENTRY_DATA


async def test_config_flow_shows_connection_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    serve(aioclient_mock, status={"2,2": 500})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], ENTRY_DATA
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}


async def test_config_flow_aborts_for_configured_portal(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert entry.state is ConfigEntryState.LOADED
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], ENTRY_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
