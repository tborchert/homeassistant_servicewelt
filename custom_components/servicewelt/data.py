"""Custom types for servicewelt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import ServiceweltApiClient
    from .coordinator import ServiceweltDataUpdateCoordinator


type ServiceweltConfigEntry = ConfigEntry[ServiceweltData]


@dataclass
class ServiceweltData:
    """Data for the Servicewelt integration."""

    client: ServiceweltApiClient
    coordinator: ServiceweltDataUpdateCoordinator
    integration: Integration
