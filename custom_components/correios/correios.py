import requests
from bs4 import BeautifulSoup
import datetime

async def extrair_dados_correios(url):
    """Extrai dados de rastreamento dos Correios a partir de um ID.

    Args:
        url (str): URL completa da página de rastreamento.

    Returns:
        dict: Dicionário contendo os dados extraídos, ou None se não encontrados.
    """

    try:
        response = await requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

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
                    local = linha_status.find_all('li')[2].text.strip()
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
                    print("Formato de data ou hora inválido.")
                    return None

                return dados
            else:
                print("Elemento 'linha_status' não encontrado.")
        else:
            print("Elemento 'accordion_2' não encontrado.")

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")

    return {'status': 'Objeto não encontrado', 'data': '', 'hora': '', 'local': ''}