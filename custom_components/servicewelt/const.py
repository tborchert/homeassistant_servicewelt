"""Constants for servicewelt."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "servicewelt"
# Hostname the ISG web answers to on a typical home network
DEFAULT_HOST = "http://servicewelt"
ATTRIBUTION = "Data provided by Stiebel Eltron ISG web"
DOCS_URL = "https://github.com/tborchert/homeassistant_servicewelt"
