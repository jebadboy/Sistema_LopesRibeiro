"""
Módulo de Integração com Google Gemini AI
Sistema Lopes & Ribeiro - Assistente Jurídico Inteligente
"""

import os
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
API_KEY = os.getenv('GEMINI_API_KEY')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DB = os.path.join(BASE_DIR, 'ai_cache.db')
CACHE_VALIDITY_DAYS = 7
MAX_REQUESTS_PER_DAY = 100

class GeminiAI:
    """Classe principal para interação com API Gemini"""
    
    
    def __init__(self):
        load_dotenv(override=True)
        self.model = None
        self.inicializado = False
        self._request_count = 0
        self.api_key = None

        import streamlit as st
        
        # Tentar pegar do banco de dados (Configurações Administrador)
        try:
            import database as db
            db_key = db.get_config('gemini_api_key')
            if db_key and len(db_key) > 20: # Key válida simples check
                self.api_key = db_key
        except Exception:
            pass
        
        # Se não tiver no banco, tenta variável de ambiente
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if not self.api_key and "GEMINI_API_KEY" in st.secrets:
                self.api_key = st.secrets["GEMINI_API_KEY"]
                
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Usando gemini-2.5-flash-lite (Modelo disponível no ambiente)
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
                self.inicializado = True
                self._init_db() # Garantir que tabela existe
                logger.info("Gemini AI inicializado com sucesso (modelo: gemini-2.5-flash-lite)")
            except Exception as e:
                logger.error(f"Erro ao configurar Gemini: {e}")
        else:
            logger.error("GEMINI_API_KEY não encontrada (env ou secrets)")

    def _init_db(self):
        """Cria tabela de cache se não existir"""
        try:
            with sqlite3.connect(CACHE_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_cache (
                        hash_input TEXT PRIMARY KEY,
                        resposta TEXT,
                        data_criacao TEXT,
                        validade INTEGER
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao criar tabela de cache: {e}")

    def inicializar(self) -> bool:
        """Método de compatibilidade - retorna status da inicialização"""
        return self.inicializado
    
    def _verificar_limite_requests(self) -> bool:
        """Verifica se não excedeu limite de requisições"""
        if self._request_count >= MAX_REQUESTS_PER_DAY:
            logger.warning("Limite diário de requisições atingido")
            return False
        return True
    
    def _gerar_hash(self, texto: str) -> str:
        """Gera hash MD5 para cache"""
        return hashlib.md5(texto.encode()).hexdigest()
    
    def _buscar_cache(self, hash_input: str) -> Optional[str]:
        """Busca resposta em cache"""
        try:
            # Usar gerenciador de contexto para conexão segura
            with sqlite3.connect(CACHE_DB) as conn:
                cursor = conn.cursor()
                
                # Buscar cache válido
                data_limite = datetime.now() - timedelta(days=CACHE_VALIDITY_DAYS)
                cursor.execute("""
                    SELECT resposta FROM ai_cache 
                    WHERE hash_input = ? AND data_criacao > ?
                """, (hash_input, data_limite.isoformat()))
                
                resultado = cursor.fetchone()
                
                if resultado:
                    logger.info("Resposta encontrada em cache")
                    return resultado[0]
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar cache: {e}")
            return None
    
    def _salvar_cache(self, hash_input: str, resposta: str):
        """Salva resposta em cache"""
        try:
            with sqlite3.connect(CACHE_DB) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_cache (hash_input, resposta, data_criacao, validade)
                    VALUES (?, ?, ?, ?)
                """, (hash_input, resposta, datetime.now().isoformat(), CACHE_VALIDITY_DAYS))
                
                conn.commit()
            logger.info("Resposta salva em cache")
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
    
    def _construir_prompt_chat(self, mensagem: str, contexto: Optional[Dict] = None) -> str:
        """Constrói o prompt enriquecido com contexto"""
        
        PERSONALIDADE_JURIDICA = """
        Você é o Consultor Jurídico e Estratégico (IA) do escritório Lopes & Ribeiro Advocacia.
        Sua missão é auxiliar os sócios Dr. Eduardo Ribeiro e Dra. Sheila Lopes com análises jurídicas, financeiras e comerciais de alta precisão.

        CONTEXTO:
        - Localização: Maricá/RJ (mas com atuação nacional digital).
        - Especialidades: Direito de Família, Sucessões, Cível e Trabalhista.
        - Tom de Voz: Profissional, culto, direto e estratégico. Evite "juridiquês" desnecessário, foque na solução.

        REGRAS DE RESPOSTA:
        1. Fundamentação: Sempre cite a legislação aplicável (CF/88, CC/02, CPC/15, CLT) e jurisprudência recente quando relevante.
        2. Formatação: Use tópicos (bullet points) e negrito para destacar prazos, valores e artigos de lei.
        3. Postura: Aja como um parceiro sênior. Se houver risco jurídico ou financeiro, alette imediatamente.
        4. Identidade: Nunca diga "sou uma IA". Diga "Nossa análise preliminar indica..." ou "Como consultor do escritório...".
        5. Análise de Dados: Ao receber dados financeiros ou de processos, seja analítico. Identifique padrões, sugira cortes de gastos ou estratégias de cobrança.

        Se o usuário pedir um esboço, entregue uma estrutura completa de peça.
        """

        prompt = f"""
        {PERSONALIDADE_JURIDICA}
        
        Contexto Atual:
        {str(contexto) if contexto else 'Nenhum contexto específico fornecido.'}
        
        Pergunta/Comando do Usuário:
        {mensagem}
        """
        return prompt

    def chat(self, mensagem: str, contexto: Optional[Dict] = None) -> str:
        """Chat com assistente jurídico"""
        if not self.inicializado or not self.model:
            return "❌ IA não inicializada. Verifique a configuração da API."
        
        if not self._verificar_limite_requests():
            return "⚠️ Limite diário de requisições atingido."
        
        try:
            prompt = self._construir_prompt_chat(mensagem, contexto)
            
            # Verificar cache
            hash_input = self._gerar_hash(prompt)
            resposta_cache = self._buscar_cache(hash_input)
            
            if resposta_cache:
                return resposta_cache
            
            # Gerar resposta
            response = self.model.generate_content(prompt)
            resposta = response.text
            
            # Salvar em cache
            self._salvar_cache(hash_input, resposta)
            self._request_count += 1
            
            return resposta
            
        except Exception as e:
            logger.error(f"Erro no chat: {e}")
            return f"❌ Erro ao processar mensagem: {str(e)}"

    def analisar_andamento(self, texto_movimentacao: str, contexto_processo: str = "", nome_cliente: str = "") -> Dict:
        """
        Analisa movimentação processual com 3 regras inteligentes:
        1. Anti-alucinação: Não inventa dados
        2. WhatsApp-ready: Gera mensagem pronta para cliente
        3. Gatilhos financeiros: Detecta oportunidades de receita
        """
        if not self.inicializado or not self.model:
            return {"erro": "IA não inicializada"}
        
        # Gatilhos financeiros para detectar oportunidades de receita
        GATILHOS_FINANCEIROS = [
            "alvará", "levantamento", "sucumbência", "honorários", 
            "trânsito em julgado", "procedente", "acordo homologado",
            "sentença favorável", "recurso provido", "depósito judicial",
            "pagamento", "expedição de alvará", "cumprimento de sentença"
        ]
            
        try:
            prompt = f"""
            VOCÊ É O CONSULTOR JURÍDICO-FINANCEIRO DO ESCRITÓRIO LOPES & RIBEIRO.
            
            === REGRAS FUNDAMENTAIS (NUNCA VIOLE) ===
            
            REGRA 1 - ANTI-ALUCINAÇÃO:
            - Se uma informação NÃO estiver EXPLÍCITA no texto, responda "Não informado nos autos"
            - NUNCA presuma, deduza ou invente dados como tipo de documento, valores ou datas
            - Prefira dizer "não identificado" do que arriscar informação incorreta
            
            REGRA 2 - COMUNICAÇÃO HUMANIZADA:
            - Gere uma mensagem pronta para WhatsApp, em linguagem simples e amigável
            - Use emojis para deixar a comunicação leve
            - O cliente é LEIGO, não use termos técnicos
            - Comece com saudação usando o nome do cliente (se disponível)
            
            REGRA 3 - FOCO EM RECEITA:
            - Identifique se há OPORTUNIDADE FINANCEIRA (honorários, sucumbência, alvará, levantamento)
            - Se detectar dinheiro na mesa, sinalize com prioridade ALTA
            - Gatilhos: alvará, levantamento, sucumbência, honorários, trânsito em julgado, acordo homologado
            
            === DADOS PARA ANÁLISE ===
            
            Movimentação: "{texto_movimentacao}"
            
            Contexto: {contexto_processo}
            
            Nome do Cliente: {nome_cliente if nome_cliente else "Cliente"}
            
            === RESPONDA NO FORMATO JSON ===
            {{
                "urgente": boolean,
                "acao_requerida": boolean,
                "resumo": "Resumo técnico curto (1 frase)",
                "mensagem_cliente": "Mensagem pronta para WhatsApp, humanizada com emojis",
                "gatilho_financeiro": boolean,
                "tipo_gatilho": "Tipo: alvará/sucumbência/honorários/levantamento/nenhum",
                "sugestao_financeira": "Ação financeira sugerida (ex: Lançar recebimento de R$ X) ou null"
            }}
            """
            
            hash_input = self._gerar_hash(prompt)
            resposta_cache = self._buscar_cache(hash_input)
            
            if resposta_cache:
                import json
                try: 
                    return {**json.loads(resposta_cache), "from_cache": True}
                except:
                     pass # Se cache estiver inválido, gera dnovo
            
            response = self.model.generate_content(prompt)
            texto_resp = response.text.replace("```json", "").replace("```", "").strip()
            
            self._salvar_cache(hash_input, texto_resp)
            self._request_count += 1
            
            import json
            resultado = json.loads(texto_resp)
            
            # Validação adicional: verificar gatilhos por regex como fallback
            texto_lower = texto_movimentacao.lower()
            if not resultado.get('gatilho_financeiro'):
                for gatilho in GATILHOS_FINANCEIROS:
                    if gatilho in texto_lower:
                        resultado['gatilho_financeiro'] = True
                        resultado['tipo_gatilho'] = gatilho
                        break
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao analisar andamento: {e}")
            return {"urgente": False, "resumo": f"Erro Técnico: {str(e)}", "erro": str(e)}

    def extrair_partes_processo(self, movimentos: List[str], classe_processo: str = "", orgao: str = "") -> Dict:
        """
        Extrai partes do processo analisando os movimentos via IA.
        Usado quando a API DataJud não retorna as partes diretamente.
        
        Args:
            movimentos: Lista de descrições de movimentações
            classe_processo: Classe do processo (ex: Procedimento Comum Cível)
            orgao: Órgão julgador
            
        Returns:
            Dict com lista de partes identificadas
        """
        if not self.inicializado or not self.model:
            return {"partes": [], "erro": "IA não inicializada"}
        
        if not movimentos:
            return {"partes": [], "aviso": "Nenhum movimento para analisar"}
        
        try:
            # Juntar os primeiros movimentos (mais informativos geralmente)
            texto_movimentos = "\n".join([f"- {m[:200]}" for m in movimentos[:15]])
            
            prompt = f"""
            TAREFA: Extrair nomes das PARTES do processo a partir das movimentações judiciais.
            
            === REGRAS ===
            1. Identifique APENAS nomes de pessoas ou empresas mencionados como partes (autor, réu, requerente, requerido)
            2. IGNORE nomes de juízes, advogados, servidores, peritos
            3. Se não conseguir identificar com certeza, retorne lista vazia
            4. NÃO INVENTE nomes - só extraia o que estiver EXPLÍCITO no texto
            
            === DADOS DO PROCESSO ===
            Classe: {classe_processo}
            Órgão: {orgao}
            
            === MOVIMENTAÇÕES ===
            {texto_movimentos}
            
            === RESPONDA EM JSON ===
            {{
                "partes": [
                    {{"nome": "NOME COMPLETO", "tipo": "AUTOR ou REU", "confianca": "alta/media/baixa"}}
                ],
                "observacao": "Qualquer observação relevante"
            }}
            
            Se não encontrar partes com certeza, retorne: {{"partes": [], "observacao": "Partes não identificadas nos movimentos"}}
            """
            
            hash_input = self._gerar_hash(prompt)
            resposta_cache = self._buscar_cache(hash_input)
            
            if resposta_cache:
                import json
                try: 
                    return {**json.loads(resposta_cache), "from_cache": True}
                except:
                    pass
            
            response = self.model.generate_content(prompt)
            texto_resp = response.text.replace("```json", "").replace("```", "").strip()
            
            self._salvar_cache(hash_input, texto_resp)
            self._request_count += 1
            
            import json
            resultado = json.loads(texto_resp)
            
            # Formatar partes para compatibilidade com o sistema
            partes_formatadas = []
            for p in resultado.get('partes', []):
                partes_formatadas.append({
                    'nome': p.get('nome', ''),
                    'tipo': p.get('tipo', 'INDEFINIDO').upper(),
                    'cpf_cnpj': '',  # Não disponível via IA
                    'tipo_pessoa': 'Física',  # Assumir física por padrão
                    'fonte': 'IA',
                    'confianca': p.get('confianca', 'baixa')
                })
            
            return {
                "partes": partes_formatadas,
                "observacao": resultado.get('observacao', ''),
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair partes via IA: {e}")
            return {"partes": [], "erro": str(e)}


    def analisar_documento(self, texto: str, tipo_documento: str = "genérico") -> Dict:
        """Analisa documento jurídico"""
        if not self.inicializado or not self.model:
            return {"erro": "IA não inicializada"}
        
        if not self._verificar_limite_requests():
            return {"erro": "Limite de requisições atingido"}
        
        try:
            prompt = f"""
            Você é um assistente jurídico especializado. Analise o seguinte documento do tipo "{tipo_documento}":
            
            {texto[:4000]} 
            
            Forneça uma análise estruturada contendo:
            1. Resumo executivo (3-5 linhas)
            2. Partes envolvidas
            3. Prazos mencionados (se houver)
            4. Principais pontos jurídicos
            5. Recomendações de ação
            
            Seja objetivo e use linguagem técnica jurídica.
            """
            
            hash_input = self._gerar_hash(prompt)
            resposta_cache = self._buscar_cache(hash_input)
            
            if resposta_cache:
                return {"analise": resposta_cache, "from_cache": True}
            
            response = self.model.generate_content(prompt)
            analise = response.text
            
            self._salvar_cache(hash_input, analise)
            self._request_count += 1
            
            return {
                "analise": analise,
                "tipo_documento": tipo_documento,
                "data_analise": datetime.now().isoformat(),
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar documento: {e}")
            return {"erro": str(e)}


    def analisar_estrategia_completa(self, dados_processo: Dict, historico_movimentos: List[Dict]) -> Dict:
        """Analisa o processo sob a ótica de um Sócio Sênior"""
        if not self.inicializado or not self.model:
            return {"erro": "IA não inicializada"}
            
        try:
            # Preparar o contexto do histórico (últimos 15 movimentos)
            historico_texto = ""
            for mov in historico_movimentos[:15]:
                historico_texto += f"- {mov.get('data', '?')}: {mov.get('descricao', '')}\n"
            
            prompt = f"""
            ATUE COMO UM SÓCIO SÊNIOR DE UM GRANDE ESCRITÓRIO DE ADVOCACIA.
            
            Analise este caso e forneça um PARECER ESTRATÉGICO para o advogado júnior responsável.

            DADOS DO PROCESSO:
            - Ação: {dados_processo.get('acao', 'N/A')}
            - Cliente: {dados_processo.get('cliente_nome', 'N/A')}
            - Assunto: {dados_processo.get('assunto', 'N/A')}
            - Fase Atual: {dados_processo.get('fase_processual', 'N/A')}
            - Valor da Causa: R$ {dados_processo.get('valor_causa', 0)}
            
            HISTÓRICO RECENTE (Recente primeiro):
            {historico_texto}
            
            GERE UM RELATÓRIO ESTRATÉGICO (FORMATO JSON):
            {{
                "probabilidade_exito": "Alta/Média/Baixa/Incerta",
                "justificativa_exito": "Explicação curta de 1 frase",
                "analise_fase": "Em que momento processual estamos realmente? (ex: 'Fase de instrução', 'Recurso pendente')",
                "proximos_passos_sugeridos": ["passo 1", "passo 2", "passo 3"],
                "riscos_alertas": ["risco 1", "alerta 2"],
                "sugestao_financeira": "Sugestão sobre honorários (ex: 'Pedir levantamento de alvará', 'Lançar sucumbência', 'Cobrar parcela de êxito')",
                "tom_sugestao": "Urgente/Normal/Informativo"
            }}
            """
            
            # Usar hash apenas do prompt base (menos volátil) + id do ultimo movimento para cachear por estado do processo
            ultimo_mov_hash = historico_movimentos[0].get('descricao', '') if historico_movimentos else 'vazio'
            hash_input = self._gerar_hash(prompt + ultimo_mov_hash)
            
            resposta_cache = self._buscar_cache(hash_input)
            if resposta_cache:
                import json
                try: 
                    return {**json.loads(resposta_cache), "from_cache": True}
                except: pass

            response = self.model.generate_content(prompt)
            texto_resp = response.text.replace("```json", "").replace("```", "")
            
            import json
            resultado = json.loads(texto_resp)
            
            self._salvar_cache(hash_input, texto_resp)
            self._request_count += 3 # Conta como 3 requests pois é complexo
            
            return resultado

        except Exception as e:
            logger.error(f"Erro na análise estratégica: {e}")
            return {"erro": str(e)}

# Instância global
_gemini_instance = None

def reset_gemini():
    """Força recriação da instância (útil quando troca a chave API)"""
    global _gemini_instance
    _gemini_instance = None

def inicializar_gemini() -> bool:
    """Função helper para inicializar a instância global"""
    global _gemini_instance
    if _gemini_instance is None:
        _gemini_instance = GeminiAI()
    return _gemini_instance.inicializar()

def chat_assistente(mensagem: str, contexto: Optional[Dict] = None) -> str:
    """Wrapper para função de chat"""
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.chat(mensagem, contexto)

def analisar_documento(texto: str, tipo: str = "genérico") -> Dict:
    """Wrapper para função de análise"""
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.analisar_documento(texto, tipo)

def analisar_andamento(texto: str, contexto: str = "", nome_cliente: str = "") -> Dict:
    """Wrapper para função de análise de andamento com 3 regras inteligentes"""
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.analisar_andamento(texto, contexto, nome_cliente)

def analisar_estrategia_completa(dados_processo: Dict, historico_movimentos: List[Dict]) -> Dict:
    """Wrapper para análise estratégica"""
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.analisar_estrategia_completa(dados_processo, historico_movimentos)

def extrair_partes_processo(movimentos: List[str], classe_processo: str = "", orgao: str = "") -> Dict:
    """Wrapper para extração de partes via IA quando DataJud não retorna"""
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.extrair_partes_processo(movimentos, classe_processo, orgao)
