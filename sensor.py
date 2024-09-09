"""
A platform that provides information about the tracking of objects in the post office in Brazil
For more details about this component, please refer to the documentation at
https://github.com/Renato556/correios
a fork of
https://github.com/oridestomkiel/home-assistant-correios
"""

import logging
import async_timeout
from bs4 import BeautifulSoup
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .const import (
    BASE_API,
    CONF_TRACKING,
    CONF_DESCRIPTION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

icons = {
    "Objeto postado": {
        "icon": "mdi:store-outline",
        "color": "green"
    },
    "Objeto postado após o horário limite da unidade": {
        "icon": "mdi:store-clock-outline",
        "color": "green"
    },
    "Objeto em transferência - por favor aguarde": {
        "icon": "mdi:truck-fast-outline",
        "color": "blue"
    },
    "Sua entrega ou retirada nos Correios pode levar mais tempo do que o previsto": {
        "icon": "mdi:clock-alert-outline",
        "color": "yellow"
    },
    "Objeto saiu para entrega ao destinatário": {
        "icon": "mdi:truck-check-outline",
        "color": "green"
    },
    "Objeto entregue ao destinatário": {
        "icon": "mdi:package-variant-closed-check",
        "color": "purple"
    },
    "Objeto aguardando retirada no endereço indicado": {
        "icon": "mdi:package-variant-closed-minus",
        "color": "yellow"
    },
    "Objeto não entregue - prazo de retirada encerrado": {
        "icon": "mdi:package-variant-closed-remove",
        "color": "red"
    },
    "Informações enviadas para análise da autoridade aduaneira/órgãos anuentes": {
        "icon": "mdi:file-arrow-up-down-outline",
        "color": "blue"
    },
    "default": {
        "icon": "mdi:package-variant-closed",
        "color": "orange"
    }
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    track = entry.data[CONF_TRACKING]
    description = entry.data[CONF_DESCRIPTION]
    session = async_create_clientsession(hass)
    name = f"{description} ({track})"

    async_add_entities(
        [CorreiosSensor(track, entry.entry_id, name, description, session)],
        True,
    )

async def extrair_dados_correios(url, session):
    try:
        response = await session.get(url)
        info = await response.text()

        soup = BeautifulSoup(info, 'html.parser')

        accordion = soup.find('div', class_='accordion_2')

        if accordion:
            linha_status = accordion.find('ul', class_='linha_status')

            if linha_status:
                status = linha_status.find('b').text.strip()

                dados = {'status': status}

                if "Objeto em transferência" in status:
                    origem = linha_status.find_all('li')[2].text.strip()
                    destino = linha_status.find_all('li')[3].text.strip()
                    dados['origem'] = origem
                    dados['destino'] = destino
                    dados['local'] = None
                else:
                    local = linha_status.find_all('li')[2].text.strip()
                    dados['local'] = local
                
                data_hora = linha_status.find_all('li')[1].text.strip()
                data, hora = data_hora.split(' | ')
                data = data.replace('Data', '').replace(':', '').strip()
                hora = hora.replace('Hora:', '').strip()

                try:
                    data_formatada = datetime.strptime(data, '%d/%m/%Y').strftime('%d/%m')
                    hora_formatada = datetime.strptime(hora, '%H:%M').strftime('%H:%M')
                    dados['data'] = data_formatada
                    dados['hora'] = hora_formatada
                except ValueError as e:
                    _LOGGER.error(f"Formato de data ou hora inválido: {e}")
                    return None

                return dados
            else:
                _LOGGER.error("Elemento 'linha_status' não encontrado.")
        else:
            _LOGGER.warn("Elemento 'accordion_2' não encontrado.")

    except Exception as e:
        _LOGGER.error(f"Erro na requisição: {e}")

    return None


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
        self._icon = None
        self._icon_color = None
        self.data_movimentacao = None
        self.origem = 0
        self.destino = 0
        self.local = 0
        self._state = None
        self._attr_unique_id = track

        self._attr_device_info = DeviceInfo(
            entry_type=dr.DeviceEntryType.SERVICE,
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
                data = await extrair_dados_correios(url, self.session)

                self._icon = icons["default"]["icon"]

                if data != None and 'status' in data:
                    self._state = data["status"]
                    self.data_movimentacao = f'{data["data"]} às {data["hora"]}'

                    if 'origem' in data:
                        self.origem = data["origem"].replace("Origem: ", "")
                        self.destino = data["destino"].replace("Destino: ", "")
                    else:
                        self.local = data["local"].replace("Local: ", "")

                    if data["status"] in icons:
                        self._icon = icons[data["status"]]["icon"]
                        self._icon_color = icons[data["status"]]["color"]
                else:
                    self._state = 'Objeto não encontrado'

        except Exception as error:
            _LOGGER.error("ERRO - Não foi possível atualizar - %s", error)

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon
    
    @property
    def entity_picture(self):
        return self._icon_color

    @property
    def state(self):
        return self._state

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
