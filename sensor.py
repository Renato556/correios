"""
A platform that provides information about the tracking of objects in the post office in Brazil
For more details about this component, please refer to the documentation at
https://github.com/oridestomkiel/home-assistant-correios
"""

import logging
import async_timeout
from bs4 import BeautifulSoup
import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

import json
from .const import (
    BASE_API,
    CONF_TRACKING,
    CONF_DESCRIPTION,
    DOMAIN,
    ICON,
)

_LOGGER = logging.getLogger(__name__)

icons = {
    "Objeto postado após o horário limite da unidade": "https://meucorreios.correios.com.br/app/img/ic_busca-agencia.svg",
    "Objeto em transferência - por favor aguarde": "https://cdn-icons-png.flaticon.com/512/3900/3900465.png",
    "Sua entrega ou retirada nos Correios pode levar mais tempo do que o previsto": "https://rastreamento.correios.com.br/static/rastreamento-internet/imgs/novos/agencia-exclamacao-stroke.svg",
    "Objeto saiu para entrega ao destinatário": "https://www.correios.com.br/ppn/imagens/receber-encomenda-cor.png/@@images/1c269676-de1c-455e-a7f6-bfaec7e263cf.png",
    "Objeto entregue ao destinatário": "https://www.correios.com.br/atendimento/ferramentas/aplicativo-dos-correios/imagens/caixa-gps-cor.png",
    "Objeto aguardando retirada no endereço indicado": "https://meucorreios.correios.com.br/app/img/ic_busca-agencia.svg",
    "Objeto não entregue - prazo de retirada encerrado": "https://www.correios.com.br/ppn/imagens/locker-1.png/@@images/aab4e975-d3de-4879-98da-f288be7bcea7.png",
    "Informações enviadas para análise da autoridade aduaneira/órgãos anuentes": "https://www.correios.com.br/ppn/imagens/contrato-cor/@@images/e04dde03-88eb-4f1e-a350-23e5e030bb50.png",
    "default": "https://www.correios.com.br/++theme++tema-do-portal-correios/static/imagens/ic-personalizados/busca-cor.svg"
}


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

async def extrair_dados_correios(url, session):
    """Extrai dados de rastreamento dos Correios a partir de um ID.

    Args:
        url (str): URL completa da página de rastreamento.

    Returns:
        dict: Dicionário contendo os dados extraídos, ou None se não encontrados.
    """

    try:
        response = await session.get(url)
        info = await response.text()

        soup = BeautifulSoup(info, 'html.parser')

        # Encontra o elemento div com a classe 'accordion_2'
        accordion = soup.find('div', class_='accordion_2')

        if accordion:
            # Encontra o elemento ul com a classe 'linha_status'
            linha_status = accordion.find('ul', class_='linha_status')

            if linha_status:
                # Extrai o status
                status = linha_status.find('b').text.strip()

                # Lista para armazenar os dados
                dados = {'status': status}

                # Verifica se o status indica "Objeto em transferência"
                if "Objeto em transferência" in status:
                    origem = linha_status.find_all('li')[2].text.strip()
                    destino = linha_status.find_all('li')[3].text.strip()
                    dados['origem'] = origem
                    dados['destino'] = destino
                else:
                    local = linha_status.find_all('li')[2].text.strip().replace('Local: ', '')
                    dados['local'] = local
                
                # Caso contrário, extrai os dados de "Data", "Hora" e "Local"
                data_hora = linha_status.find_all('li')[1].text.strip()
                data, hora = data_hora.split(' | ')
                hora = hora.replace('Hora:', '').strip()

                try:
                    data_formatada = datetime.datetime.strptime(data[8:], '%d/%m/%Y').strftime('%d/%m')
                    hora_formatada = datetime.datetime.strptime(hora, '%H:%M').strftime('%H:%M')
                    dados['data'] = data_formatada
                    dados['hora'] = hora_formatada
                except ValueError:
                    _LOGGER.info("Formato de data ou hora inválido.")
                    return None

                return dados
            else:
                _LOGGER.info("Elemento 'linha_status' não encontrado.")
        else:
            _LOGGER.info("Elemento 'accordion_2' não encontrado.")

    except requests.exceptions.RequestException as e:
        _LOGGER.info(f"Erro na requisição: {e}")

    return {'status': 'Objeto não encontrado', 'data': '', 'hora': '', 'local': ''}


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

                self._image = icons["default"]

                if 'status' in data:
                    self._state = data["status"]
                    self.data_movimentacao = f'{data["data"]} às {data["hora"]}'

                    if 'origem' in data:
                        self.origem = data["origem"]
                        self.destino = data["destino"]
                    else:
                        self.local = data["local"]

                    if data["status"] in icons:
                        self._image = icons[data["status"]]

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
