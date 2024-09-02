"""Constants for the Correios integration."""
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "correios"
PLATFORMS: Final = [Platform.SENSOR]

DEFAULT_NAME: Final = "Rastreamento Correios"

CONF_TRACKING = "track"
CONF_DESCRIPTION = "description"
DEFAULT_DESCRIPTION: Final = "Encomenda"

BASE_API = "https://www.linkcorreios.com.br/?id={}"
