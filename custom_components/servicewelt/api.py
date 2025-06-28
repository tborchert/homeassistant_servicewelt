"""Servicewelt API Client."""

from __future__ import annotations

import re
import socket
from typing import Any
from bs4 import BeautifulSoup

import aiohttp
import async_timeout


class ServiceweltApiClientError(Exception):
    """Exception to indicate a general API error."""


class ServiceweltApiClientCommunicationError(
    ServiceweltApiClientError,
):
    """Exception to indicate a communication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    response.raise_for_status()


class ServiceweltApiClient:
    """Servicewelt API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize Servicewelt API Client."""
        self._username = username
        self._password = password
        self._session = session
        self._base_url = "https://servicewelt.stiebel-eltron.com"

    async def async_get_data(self) -> dict[str, Any]:
        """Get data from the Servicewelt portal."""
        data = {}

        pages = [
            ("system", "?s=1,0"),
            ("heat_pump", "?s=1,1"),
            ("energy_footprint", "?s=1,8"),
            ("system_status", "?s=2,0"),
            ("heat_pump_status", "?s=2,2"),
        ]

        for page_name, page_path in pages:
            try:
                html = await self._fetch_page(page_path)
                parsed_data = self._parse_html_data(html)
                data[page_name] = parsed_data
            except Exception as e:
                data[page_name] = {"error": str(e)}

        return data

    async def _fetch_page(self, path: str) -> str:
        """Fetch a page from the Servicewelt portal."""
        url = f"{self._base_url}/{path}"
        response = await self._api_wrapper(method="get", url=url)
        return response

    def _parse_html_data(self, html: str) -> dict[str, Any]:
        """Parse HTML and extract sensor data."""
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        tables = soup.find_all("table", class_="info")

        for table in tables:
            header = table.find("th")
            if not header:
                continue

            category = header.get_text(strip=True)
            category_data = {}

            rows = table.find_all("tr")[1:]  # Skip header row

            for row in rows:
                cells = row.find_all("td")
                if len(cells) != 2:
                    continue

                key = cells[0].get_text(strip=True)
                value_cell = cells[1]

                # Check for image (binary state)
                img = value_cell.find("img")
                if img:
                    # Extract state from image filename
                    src = img.get("src", "")
                    value = "on" if "symbol_an" in src else "off"
                else:
                    value = value_cell.get_text(strip=True)
                    # Parse numeric values and units
                    value = self._parse_value(value)

                category_data[key] = value

            if category_data:
                data[category] = category_data

        return data

    def _parse_value(self, value: str) -> Any:
        """Parse and convert values to appropriate types."""
        if not value or value == "":
            return None

        # Remove common separators and normalize
        value = value.replace(",", ".")

        # Try to extract numeric value with unit
        match = re.match(r"^(-?\d+(?:\.\d+)?)\s*([A-Za-z%°]+)?", value)
        if match:
            num_str, unit = match.groups()
            try:
                num_value = float(num_str)
                if unit:
                    return {"value": num_value, "unit": unit}
                else:
                    return num_value
            except ValueError:
                pass

        return value

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.text()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise ServiceweltApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise ServiceweltApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise ServiceweltApiClientError(
                msg,
            ) from exception
