"""
Módulo de consulta pública ao TJRJ para extração de partes
Alternativa ao DataJud quando partes não estão disponíveis
"""

import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)

# URLs do TJRJ
TJRJ_CONSULTA_URL = "http://www4.tjrj.jus.br/ConsultaUnificada/consulta.do"
TJRJ_CONSULTA_NOVA_URL = "https://www3.tjrj.jus.br/consultaprocessual/"

# Headers para simular navegador real
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def extrair_numero_tjrj(numero_cnj: str) -> Optional[str]:
    """
    Extrai o número do processo no formato TJRJ (14 dígitos)
    CNJ: 0001866-76.2022.8.19.0031
    TJRJ: 00018667620228190031 (sem pontos/traços)
    """
    numeros = re.sub(r'\D', '', numero_cnj)
    if len(numeros) == 20:
        return numeros
    return None


def consultar_partes_tjrj(numero_processo: str, timeout: int = 15) -> Dict:
    """
    Consulta o TJRJ para obter as partes do processo.
    
    Args:
        numero_processo: Número do processo (CNJ ou TJRJ)
        timeout: Tempo máximo de espera em segundos
        
    Returns:
        Dict com 'partes' (lista) e 'erro' (se houver)
    """
    
    numero_limpo = re.sub(r'\D', '', numero_processo)
    
    if len(numero_limpo) != 20:
        return {
            "partes": [],
            "erro": f"Número de processo inválido: esperados 20 dígitos, recebidos {len(numero_limpo)}"
        }
    
    # Tentar consulta unificada antiga (mais fácil de parsear)
    resultado = _consultar_tjrj_unificada(numero_limpo, timeout)
    
    if resultado.get("partes"):
        return resultado
    
    # Se falhar, tentar nova consulta
    resultado_nova = _consultar_tjrj_nova(numero_limpo, timeout)
    
    return resultado_nova if resultado_nova.get("partes") else resultado


def _consultar_tjrj_unificada(numero: str, timeout: int) -> Dict:
    """Consulta na interface antiga do TJRJ"""
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Parâmetros do formulário
        params = {
            "FLESSION": "",
            "portal": "1",
            "NumeroProcesso": numero,
            "tipoConsulta": "1"
        }
        
        logger.info(f"Consultando TJRJ (unificada): {numero[:10]}...")
        
        response = session.post(
            TJRJ_CONSULTA_URL,
            data=params,
            timeout=timeout,
            allow_redirects=True
        )
        
        if response.status_code != 200:
            return {
                "partes": [],
                "erro": f"Erro HTTP {response.status_code}"
            }
        
        # Parsear HTML
        return _parsear_html_tjrj(response.text)
        
    except requests.Timeout:
        return {"partes": [], "erro": "Timeout na consulta ao TJRJ"}
    except requests.RequestException as e:
        logger.error(f"Erro na requisição TJRJ: {e}")
        return {"partes": [], "erro": f"Erro de conexão: {str(e)}"}
    except Exception as e:
        logger.error(f"Erro inesperado TJRJ: {e}")
        return {"partes": [], "erro": f"Erro inesperado: {str(e)}"}


def _consultar_tjrj_nova(numero: str, timeout: int) -> Dict:
    """Consulta na interface nova do TJRJ (API interna)"""
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # A nova interface usa uma API interna
        # Primeiro acessa a página para pegar cookies
        session.get(TJRJ_CONSULTA_NOVA_URL, timeout=10)
        
        # Formatar número no padrão CNJ para a API
        numero_formatado = f"{numero[0:7]}-{numero[7:9]}.{numero[9:13]}.{numero[13]}.{numero[14:16]}.{numero[16:20]}"
        
        # Tentar endpoint da API interna
        api_url = f"https://www3.tjrj.jus.br/consultaprocessual/api/processos/porNumero"
        
        params = {
            "numeroProcesso": numero_formatado
        }
        
        logger.info(f"Consultando TJRJ (nova API): {numero_formatado}")
        
        response = session.get(
            api_url,
            params=params,
            timeout=timeout
        )
        
        if response.status_code == 200:
            try:
                dados = response.json()
                return _parsear_json_tjrj(dados)
            except:
                pass
        
        return {"partes": [], "erro": "API nova não retornou dados"}
        
    except Exception as e:
        logger.error(f"Erro na nova API TJRJ: {e}")
        return {"partes": [], "erro": str(e)}


def _parsear_html_tjrj(html: str) -> Dict:
    """Extrai partes do HTML de resposta do TJRJ"""
    
    partes = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Procurar tabela de partes (estrutura comum do TJRJ)
        # Padrões comuns: "Autor", "Réu", "Requerente", "Requerido"
        
        texto_completo = soup.get_text()
        
        # Padrão 1: Buscar em tabelas
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                texto_row = ' '.join(c.get_text().strip() for c in cells)
                
                # Detectar tipo de parte
                tipo = None
                if any(x in texto_row.upper() for x in ['AUTOR', 'REQUERENTE', 'EXEQUENTE']):
                    tipo = 'AUTOR'
                elif any(x in texto_row.upper() for x in ['RÉU', 'REU', 'REQUERIDO', 'EXECUTADO']):
                    tipo = 'REU'
                
                if tipo:
                    # Extrair nome (geralmente na próxima célula ou linha)
                    for cell in cells:
                        nome = cell.get_text().strip()
                        # Filtrar labels
                        if nome and len(nome) > 3 and nome.upper() not in ['AUTOR', 'RÉU', 'REU', 'REQUERENTE', 'REQUERIDO']:
                            if not any(x in nome.upper() for x in ['AUTOR:', 'RÉU:', 'PARTE']):
                                partes.append({
                                    'nome': nome,
                                    'tipo': tipo,
                                    'cpf_cnpj': '',
                                    'tipo_pessoa': 'Física',
                                    'fonte': 'TJRJ'
                                })
        
        # Padrão 2: Regex em texto
        if not partes:
            # Autor: NOME ou Requerente: NOME
            padrao_autor = r'(?:Autor|Requerente|Exequente)\s*[:\-]?\s*([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú\s]+)'
            padrao_reu = r'(?:Réu|Requerido|Executado)\s*[:\-]?\s*([A-ZÀ-Ú][A-ZÀ-Úa-zà-ú\s]+)'
            
            for match in re.finditer(padrao_autor, texto_completo, re.IGNORECASE):
                nome = match.group(1).strip()
                if len(nome) > 3:
                    partes.append({
                        'nome': nome,
                        'tipo': 'AUTOR',
                        'cpf_cnpj': '',
                        'tipo_pessoa': 'Física',
                        'fonte': 'TJRJ'
                    })
            
            for match in re.finditer(padrao_reu, texto_completo, re.IGNORECASE):
                nome = match.group(1).strip()
                if len(nome) > 3:
                    partes.append({
                        'nome': nome,
                        'tipo': 'REU',
                        'cpf_cnpj': '',
                        'tipo_pessoa': 'Física',
                        'fonte': 'TJRJ'
                    })
        
        # Remover duplicatas
        partes_unicas = []
        nomes_vistos = set()
        for p in partes:
            if p['nome'] not in nomes_vistos:
                nomes_vistos.add(p['nome'])
                partes_unicas.append(p)
        
        return {
            "partes": partes_unicas,
            "fonte": "TJRJ HTML"
        }
        
    except Exception as e:
        logger.error(f"Erro ao parsear HTML TJRJ: {e}")
        return {"partes": [], "erro": f"Erro no parsing: {str(e)}"}


def _parsear_json_tjrj(dados: dict) -> Dict:
    """Extrai partes do JSON da API nova do TJRJ"""
    
    partes = []
    
    try:
        # Estrutura pode variar - tentar vários caminhos
        polos = dados.get('polos', dados.get('partes', []))
        
        for polo in polos:
            tipo = polo.get('polo', polo.get('tipo', 'INDEFINIDO'))
            if tipo in ['AT', 'ATIVO']: 
                tipo = 'AUTOR'
            elif tipo in ['PA', 'PASSIVO']: 
                tipo = 'REU'
            
            pessoas = polo.get('partes', polo.get('pessoas', [polo]))
            
            for pessoa in pessoas:
                nome = pessoa.get('nome', pessoa.get('nomeCompleto', ''))
                if nome:
                    partes.append({
                        'nome': nome,
                        'tipo': tipo,
                        'cpf_cnpj': pessoa.get('cpfCnpj', pessoa.get('documento', '')),
                        'tipo_pessoa': 'Jurídica' if pessoa.get('tipoPessoa') == 'PJ' else 'Física',
                        'fonte': 'TJRJ API'
                    })
        
        return {
            "partes": partes,
            "fonte": "TJRJ JSON"
        }
        
    except Exception as e:
        logger.error(f"Erro ao parsear JSON TJRJ: {e}")
        return {"partes": [], "erro": str(e)}


# Função de teste
if __name__ == "__main__":
    # Testar com um número de processo
    numero_teste = "00018667620228190031"
    print(f"Testando consulta TJRJ: {numero_teste}")
    resultado = consultar_partes_tjrj(numero_teste)
    print(f"Resultado: {resultado}")
