"""Adds config flow for Servicewelt."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .api import (
    ServiceweltApiClient,
    ServiceweltApiClientCommunicationError,
    ServiceweltApiClientError,
)
from .const import DEFAULT_HOST, DOCS_URL, DOMAIN, LOGGER


class ServiceweltFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Servicewelt."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                await self._test_connection(host=host)
            except ServiceweltApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except ServiceweltApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(unique_id=slugify(host.rstrip("/")))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=host,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                },
            ),
            errors=_errors,
            description_placeholders={"docs_url": DOCS_URL},
        )

    async def _test_connection(self, host: str) -> None:
        """Validate that the portal is reachable."""
        client = ServiceweltApiClient(
            session=async_create_clientsession(self.hass),
            host=host,
        )
        await client.async_get_data()
