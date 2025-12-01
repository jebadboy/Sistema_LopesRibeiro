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
CACHE_DB = 'dados_escritorio.db'
CACHE_VALIDITY_DAYS = 7
MAX_REQUESTS_PER_DAY = 100

class GeminiAI:
    """Classe principal para interação com API Gemini"""
    
    def __init__(self):
        load_dotenv(override=True)
        self.model = None
        self.inicializado = False
        self._request_count = 0
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Usando gemini-2.5-flash-lite conforme listagem de modelos disponíveis
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
                self.inicializado = True
                logger.info("Gemini AI inicializado com sucesso (modelo: gemini-2.5-flash-lite)")
            except Exception as e:
                logger.error(f"Erro ao configurar Gemini: {e}")
        else:
            logger.error("GEMINI_API_KEY não encontrada")

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
        Você é o Consultor Jurídico Sênior (IA) do escritório Lopes & Ribeiro Advocacia.
        Sua missão é auxiliar os sócios Dr. Eduardo Ribeiro e Dra. Sheila Lopes com análises jurídicas de alta precisão.

        CONTEXTO:
        - Localização: Maricá/RJ (mas com atuação nacional digital).
        - Especialidades: Direito de Família, Sucessões, Cível e Trabalhista.
        - Tom de Voz: Profissional, culto, direto e estratégico. Evite "juridiquês" desnecessário, foque na solução.

        REGRAS DE RESPOSTA:
        1. Fundamentação: Sempre cite a legislação aplicável (CF/88, CC/02, CPC/15, CLT) e jurisprudência recente quando relevante.
        2. Formatação: Use tópicos (bullet points) e negrito para destacar prazos e artigos de lei.
        3. Postura: Aja como um parceiro sênior. Se houver risco jurídico, alette imediatamente.
        4. Identidade: Nunca diga "sou uma IA". Diga "Nossa análise preliminar indica..." ou "Como consultor do escritório...".

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

# Instância global
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
