"""
A platform that provides information about the tracking of objects in the post office in Brazil
For more details about this component, please refer to the documentation at
https://github.com/oridestomkiel/home-assistant-correios
"""

import json
import logging
import async_timeout
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from correios import extrair_dados_correios

import json
from .const import (
    BASE_API,
    CONF_TRACKING,
    CONF_DESCRIPTION,
    DOMAIN,
    ICON,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tuya sensor dynamically through Tuya discovery."""
    track = entry.data[CONF_TRACKING]
    description = entry.data[CONF_DESCRIPTION]
    session = async_create_clientsession(hass)
    name = f"{description} ({track})"

    async_add_entities(
        [CorreiosSensor(track, entry.entry_id, name, description, session)],
        True,
    )


class CorreiosSensor(SensorEntity):
    def __init__(
        self,
        track,
        config_entry_id,
        name,
        description,
        session,
    ):
        self.session = session
        self.track = track
        self._name = name
        self.description = description
        self._image = None
        self.dtPrevista = None
        self.data_movimentacao = None
        self.origem = None
        self.destino = None
        self.local = None
        self._state = None
        self._attr_unique_id = track

        self._attr_device_info = DeviceInfo(
            entry_type=dr.DeviceEntryType.SERVICE,
            config_entry_id=config_entry_id,
            connections=None,
            identifiers={(DOMAIN, track)},
            manufacturer="Correios",
            name=track,
            model="Não aplicável",
            sw_version=None,
            hw_version=None,
        )

    async def async_update(self):
        try:
            url = BASE_API.format(self.track)
            async with async_timeout.timeout(3000):
                data = await extrair_dados_correios(url)

                if data["status"]:
                    self._state = data["status"]
                    self.data_movimentacao = f'{data["data"]} às {data["hora"]}'

                    if data["origem"]:
                        self.origem = data["origem"]
                        self.destino = data["destino"]
                    else:
                        self.local = data["local"]


                f = open('data.json')
                icons = json.load(f)

                if icons[data["status"]]:
                    self._image = icons[data["status"]]
                else:
                    self._image = icons["default"]

        except Exception as error:
            _LOGGER.error("ERRO - Não foi possível atualizar - %s", error)

    @property
    def name(self):
        return self._name

    @property
    def entity_picture(self):
        return self._image

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return ICON

    @property
    def extra_state_attributes(self):

        return {
            "Descrição": self.description,
            "Código Objeto": self.track,
            "Origem": self.origem,
            "Destino": self.destino,
            "Local": self.local,
            "Última Movimentação": self.data_movimentacao,
        }
