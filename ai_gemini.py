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
        
        # Ordem de prioridade para buscar API key:
        # 1. Secret Manager (produção)
        # 2. Banco de dados (configuração admin)
        # 3. Variável de ambiente (dev local)
        # 4. Streamlit secrets
        
        # 1. Tentar Secret Manager primeiro
        try:
            import secrets_manager
            self.api_key = secrets_manager.get_gemini_api_key()
            logger.info("API Key do Gemini obtida do Secret Manager")
        except Exception as e:
            logger.debug(f"Secret Manager não disponível: {e}")
        
        # 2. Se não encontrou, tentar banco de dados (Configurações Admin)
        if not self.api_key:
            try:
                import database as db
                db_key = db.get_config('gemini_api_key')
                if db_key and len(db_key) > 20:  # Key válida simples check
                    self.api_key = db_key
                    logger.info("API Key do Gemini obtida do banco de dados")
            except Exception:
                pass
        
        # 3. Se não tiver no banco, tentar variável de ambiente
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if self.api_key:
                logger.info("API Key do Gemini obtida de variável de ambiente")
        
        # 4. Fallback para Streamlit secrets
        if not self.api_key and "GEMINI_API_KEY" in st.secrets:
            self.api_key = st.secrets["GEMINI_API_KEY"]
            logger.info("API Key do Gemini obtida de Streamlit secrets")
                
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Usando gemini-2.5-flash-lite (Modelo disponível no ambiente)
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
                self.inicializado = True
                self._init_db()  # Garantir que tabela existe
                logger.info("Gemini AI inicializado com sucesso (modelo: gemini-2.5-flash-lite)")
            except Exception as e:
                logger.error(f"Erro ao configurar Gemini: {e}")
        else:
            logger.error("❌ GEMINI_API_KEY não encontrada em nenhuma fonte (Secret Manager, DB, env, secrets)")

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
            
            # Gerar resposta com Retry Loop (Tratamento Erro 429)
            import time
            max_tentativas = 3
            tentativa = 0
            response = None
            
            while tentativa < max_tentativas:
                try:
                    response = self.model.generate_content(prompt)
                    break
                except Exception as e:
                    tentativa += 1
                    erro_str = str(e)
                    
                    if ("429" in erro_str or "quota" in erro_str.lower()) and tentativa < max_tentativas:
                        tempo_espera = 10 * tentativa  # Espera progressiva (10s, 20s, 30s)
                        logger.warning(f"⏳ Chat: Cota atingida (Tentativa {tentativa}/{max_tentativas}). Aguardando {tempo_espera}s...")
                        time.sleep(tempo_espera)
                    else:
                        raise e
            
            resposta = response.text
            
            # Salvar em cache
            self._salvar_cache(hash_input, resposta)
            self._request_count += 1
            
            return resposta
            
        except Exception as e:
            erro_str = str(e)
            logger.error(f"Erro no chat: {e}")
            
            if "429" in erro_str or "quota" in erro_str.lower():
                return "⏳ Limite de requisições atingido. Aguarde 1 minuto e tente novamente."
            
            return f"❌ Erro ao processar mensagem: {erro_str}"

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
            
            REGRA 4 - TRADUTOR JURÍDICO (EDUCATIVO):
            - No campo "explicacao_didatica", explique O QUE É aquele ato processual
            - Defina o termo para um LEIGO de forma clara e simples
            - Exemplo: Se for "Conclusos para Despacho", a explicação deve ser: "Significa que o processo está na mesa do Juiz para que ele tome uma decisão ou dê uma ordem."
            - Exemplo: Se for "Juntada de AR", explique: "Significa que o correio devolveu o comprovante confirmando se a pessoa recebeu ou não a carta judicial."
            - Exemplo: Se for "Citação", explique: "É o ato oficial que avisa a outra parte que existe um processo contra ela e que ela precisa se defender."
            
            === DADOS PARA ANÁLISE ===
            
            Movimentação: "{texto_movimentacao}"
            
            Contexto: {contexto_processo}
            
            Nome do Cliente: {nome_cliente if nome_cliente else "Cliente"}
            
            === RESPONDA NO FORMATO JSON ===
            {{
                "urgente": boolean,
                "acao_requerida": boolean,
                "resumo": "Resumo técnico curto (1 frase)",
                "explicacao_didatica": "Definição do termo jurídico em linguagem simples para leigos - O QUE É esse ato processual",
                "mensagem_cliente": "Mensagem pronta para WhatsApp, humanizada com emojis",
                "gatilho_financeiro": boolean,
                "tipo_gatilho": "Tipo: alvará/sucumbência/honorários/levantamento/nenhum",
                "sugestao_financeira": "Ação financeira sugerida (ex: Lançar recebimento de R$ X) ou null",
                "evolucao_processual": "Explicação CONTEXTUALIZADA do que isso significa no andamento geral (ex: 'O processo saiu da fase de conhecimento e iniciou a execução')",
                "proxima_fase": "Previsão do próximo passo lógico (ex: 'Expedição de mandato', 'Sentença', 'Recurso')",
                "recomendacao_advogado": "Recomendação explícita para o advogado: 'AGUARDAR' ou 'PETICIONAR' ou 'CONTATAR CLIENTE'"
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
            
            # Gerar resposta com Retry Loop (Tratamento Erro 429)
            import time
            max_tentativas = 3
            tentativa = 0
            response = None
            
            while tentativa < max_tentativas:
                try:
                    response = self.model.generate_content(prompt)
                    break
                except Exception as e:
                    tentativa += 1
                    erro_str = str(e)
                    
                    if ("429" in erro_str or "quota" in erro_str.lower()) and tentativa < max_tentativas:
                        tempo_espera = 10 * tentativa
                        logger.warning(f"⏳ Andamento: Cota atingida (Tentativa {tentativa}/{max_tentativas}). Aguardando {tempo_espera}s...")
                        time.sleep(tempo_espera)
                    else:
                        raise e
            
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
            error_str = str(e)
            logger.error(f"Erro ao analisar andamento: {e}")
            
            # Tratamento específico para erro de quota
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                return {
                    "urgente": False, 
                    "resumo": "⏳ Limite de requisições atingido. Aguarde 1 minuto e tente novamente.", 
                    "erro": "quota_exceeded",
                    "mensagem_usuario": "O limite gratuito da IA foi atingido. Aguarde alguns segundos ou atualize seu plano Google AI."
                }
            
            return {"urgente": False, "resumo": f"Erro Técnico: {error_str}", "erro": error_str}

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
            error_str = str(e)
            logger.error(f"Erro na análise estratégica: {e}")
            
            # Tratamento específico para erro de quota
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                return {
                    "erro": "quota_exceeded",
                    "probabilidade_exito": "Indisponível",
                    "justificativa_exito": "Limite de requisições da IA atingido. Aguarde 1 minuto.",
                    "analise_fase": "Análise temporariamente indisponível",
                    "proximos_passos_sugeridos": ["Aguarde 1 minuto e tente novamente"],
                    "riscos_alertas": ["Limite de quota da API Gemini atingido"],
                    "mensagem_usuario": "⏳ O limite gratuito da IA foi atingido. Aguarde alguns segundos ou atualize seu plano Google AI."
                }
            
            return {"erro": error_str}

    def analisar_processo_completo(self, id_processo: int, dados_processo: Dict, historico_movimentos: List[Dict], force_refresh: bool = False) -> Dict:
        """
        OTIMIZAÇÃO DE CONSUMO: Single Shot Prompting
        
        Faz UMA ÚNICA chamada à API Gemini retornando TODAS as análises:
        - Estratégia
        - Riscos
        - Oportunidades Financeiras
        - Próximos Passos
        - Mensagem para Cliente
        
        Cache em banco de dados do sistema (TTL: 24h)
        Reduz consumo de API em ~80%
        
        Args:
            id_processo: ID do processo no banco
            dados_processo: Dict com dados do processo
            historico_movimentos: Lista de movimentos
            force_refresh: Se True, ignora cache
            
        Returns:
            Dict completo com todas as análises
        """
        import database as db_main
        import json
        
        CACHE_TTL_HOURS = 24
        
        # 1. VERIFICAR CACHE EM BANCO (não arquivo local)
        if not force_refresh:
            try:
                cache_query = """
                    SELECT analise_json, data_analise 
                    FROM ai_analises_cache 
                    WHERE id_processo = ? 
                    ORDER BY data_analise DESC 
                    LIMIT 1
                """
                cache_result = db_main.sql_get_query(cache_query, (id_processo,))
                
                if not cache_result.empty:
                    data_cache = cache_result.iloc[0]['data_analise']
                    # Verificar TTL
                    try:
                        data_cache_dt = datetime.fromisoformat(data_cache)
                        idade_horas = (datetime.now() - data_cache_dt).total_seconds() / 3600
                        
                        if idade_horas < CACHE_TTL_HOURS:
                            resultado = json.loads(cache_result.iloc[0]['analise_json'])
                            resultado['from_cache'] = True
                            resultado['cache_age_hours'] = round(idade_horas, 1)
                            logger.info(f"Análise carregada do cache (idade: {idade_horas:.1f}h)")
                            return resultado
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Cache não disponível: {e}")
        
        # 2. SE NÃO TEM CACHE VÁLIDO, FAZER CHAMADA ÚNICA
        if not self.inicializado or not self.model:
            return {"erro": "IA não inicializada"}
        
        try:
            # Preparar contexto
            historico_texto = ""
            for mov in historico_movimentos[:20]:  # Aumentar para 20 movimentos
                historico_texto += f"- {mov.get('data', '?')}: {mov.get('descricao', '')}\n"
            
            # PROMPT ÚNICO (SINGLE SHOT) - Retorna tudo de uma vez
            prompt = f"""
            ATUE COMO SÓCIO SÊNIOR DO ESCRITÓRIO LOPES & RIBEIRO.
            
            Analise o processo abaixo e retorne UM ÚNICO JSON com TODAS as análises.
            
            === DADOS DO PROCESSO ===
            - Número: {dados_processo.get('numero', 'N/A')}
            - Ação: {dados_processo.get('acao', 'N/A')}
            - Cliente: {dados_processo.get('cliente_nome', 'N/A')}
            - Fase Atual: {dados_processo.get('fase_processual', 'N/A')}
            - Valor da Causa: R$ {dados_processo.get('valor_causa', 0)}
            - Assunto: {dados_processo.get('assunto', 'N/A')}
            
            === HISTÓRICO DE MOVIMENTAÇÕES ===
            {historico_texto if historico_texto else "Sem movimentações registradas."}
            
            === RETORNE UM ÚNICO JSON NO FORMATO ===
            {{
                "resumo_executivo": "Resumo em 2-3 frases do estado atual do processo",
                
                "probabilidade_exito": "Alta/Média/Baixa/Incerta",
                "justificativa_exito": "Explicação de 1 frase",
                
                "analise_fase": "Em que fase estamos realmente",
                
                "proximos_passos": ["passo 1", "passo 2", "passo 3"],
                
                "riscos": ["risco 1", "risco 2"],
                "urgencia": 1-5,
                
                "oportunidade_financeira": true/false,
                "tipo_oportunidade": "alvara/sucumbencia/honorarios/nenhum",
                "sugestao_financeira": "Ação sugerida ou null",
                
                "mensagem_cliente": "Mensagem curta e amigável para enviar ao cliente por WhatsApp, com emojis",
                
                "tom": "Urgente/Normal/Informativo"
            }}
            
            IMPORTANTE: Responda APENAS com o JSON, sem texto adicional.
            """
            
            # Chamar API com Lógica de Retry (Modo Teimoso)
            max_tentativas = 3
            tentativa = 0
            response = None
            
            while tentativa < max_tentativas:
                try:
                    # Tenta chamar o Google
                    response = self.model.generate_content(prompt)
                    break # Se der certo, sai do loop
                except Exception as e:
                    tentativa += 1
                    erro_str = str(e)
                    
                    # Se for erro de COTA (429) e ainda tiver tentativas sobrando
                    if ("429" in erro_str or "quota" in erro_str.lower()) and tentativa < max_tentativas:
                        tempo_espera = 25 * tentativa # Espera progressiva (25s, 50s...)
                        logger.warning(f"⏳ Cota atingida (Tentativa {tentativa}/{max_tentativas}). Aguardando {tempo_espera}s...")
                        import time
                        time.sleep(tempo_espera)
                    else:
                        # Se for outro erro ou se acabaram as tentativas, estoura o erro original
                        raise e
            texto_resp = response.text.replace("```json", "").replace("```", "").strip()
            
            resultado = json.loads(texto_resp)
            resultado['from_cache'] = False
            resultado['data_analise'] = datetime.now().isoformat()
            
            # 3. SALVAR NO CACHE DO BANCO
            try:
                # Criar tabela se não existir
                db_main.sql_run("""
                    CREATE TABLE IF NOT EXISTS ai_analises_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_processo INTEGER NOT NULL,
                        analise_json TEXT NOT NULL,
                        data_analise TEXT NOT NULL,
                        UNIQUE(id_processo)
                    )
                """)
                
                # Inserir ou atualizar
                db_main.sql_run("""
                    INSERT OR REPLACE INTO ai_analises_cache (id_processo, analise_json, data_analise)
                    VALUES (?, ?, ?)
                """, (id_processo, json.dumps(resultado, ensure_ascii=False), datetime.now().isoformat()))
                
                logger.info(f"Análise salva no cache para processo {id_processo}")
            except Exception as e:
                logger.warning(f"Erro ao salvar cache: {e}")
            
            self._request_count += 1  # Conta como 1 requisição apenas!
            
            return resultado
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Erro na análise completa: {e}")
            
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                return {
                    "erro": "quota_exceeded",
                    "resumo_executivo": "Limite de requisições atingido",
                    "probabilidade_exito": "Indisponível",
                    "mensagem_usuario": "⏳ Limite da IA atingido. Aguarde 1 minuto."
                }
            
            return {"erro": error_str}

    def analisar_email_juridico(self, assunto: str, corpo: str, remetente: str = "") -> Dict:
        """
        Analisa email de intimação/citação com IA.
        Extrai prazo, calcula data fatal, classifica urgência.
        
        REGRAS DE SEGURANÇA JURÍDICA:
        - Retorna prazo como SUGESTÃO, não definitivo
        - Requer confirmação manual do advogado
        """
        if not self.inicializado or not self.model:
            return {"erro": "IA não inicializada", "prazo_identificado": False}
        
        try:
            prompt = f"""
            VOCÊ É O CONSULTOR JURÍDICO DO ESCRITÓRIO LOPES & RIBEIRO.
            
            === TAREFA ===
            Analise este EMAIL DE TRIBUNAL e extraia informações sobre PRAZOS PROCESSUAIS.
            
            === REGRAS DE EXTRAÇÃO ===
            1. PRAZO: Identifique se há prazo mencionado (ex: "15 dias", "48 horas", "5 dias úteis")
            2. TIPO DE ATO: Classificar (intimação, citação, alvará, mandado, despacho, sentença)
            3. URGÊNCIA: Avaliar de 1 a 5 (5 = urgentíssimo)
            4. Se NÃO encontrar prazo explícito, retorne prazo_dias: null
            5. NUNCA INVENTE prazos - só extraia o que estiver EXPLÍCITO
            
            === EMAIL PARA ANÁLISE ===
            REMETENTE: {remetente}
            ASSUNTO: {assunto}
            CORPO:
            {corpo[:3000]}
            
            === RESPONDA EM JSON ===
            {{
                "prazo_identificado": true/false,
                "prazo_dias": numero ou null,
                "prazo_tipo": "dias_corridos" ou "dias_uteis" ou "horas" ou null,
                "tipo_ato": "intimacao/citacao/alvara/mandado/despacho/sentenca/outro",
                "urgencia": 1-5,
                "resumo_breve": "Resumo em 1 frase do que o email diz",
                "acao_sugerida": "O que o advogado deve fazer",
                "numero_processo": "numero CNJ se identificado ou null",
                "valor_mencionado": numero ou null,
                "observacao_ia": "Qualquer observação relevante"
            }}
            """
            
            hash_input = self._gerar_hash(prompt)
            resposta_cache = self._buscar_cache(hash_input)
            
            if resposta_cache:
                import json
                try:
                    resultado = json.loads(resposta_cache)
                    resultado["from_cache"] = True
                    return self._processar_resultado_email(resultado)
                except:
                    pass
            
            response = self.model.generate_content(prompt)
            texto_resp = response.text.replace("```json", "").replace("```", "").strip()
            
            self._salvar_cache(hash_input, texto_resp)
            self._request_count += 2
            
            import json
            resultado = json.loads(texto_resp)
            resultado["from_cache"] = False
            
            return self._processar_resultado_email(resultado)
            
        except Exception as e:
            logger.error(f"Erro ao analisar email jurídico: {e}")
            return {"erro": str(e), "prazo_identificado": False, "resumo_breve": "Erro na análise IA"}
    
    def _processar_resultado_email(self, resultado: Dict) -> Dict:
        """Processa resultado da análise de email e calcula data fatal sugerida."""
        if resultado.get("prazo_identificado") and resultado.get("prazo_dias"):
            prazo_dias = int(resultado["prazo_dias"])
            hoje = datetime.now()
            
            if resultado.get("prazo_tipo") == "dias_uteis":
                dias_corridos = prazo_dias + (prazo_dias // 5) * 2
                data_fatal = hoje + timedelta(days=dias_corridos)
            elif resultado.get("prazo_tipo") == "horas":
                data_fatal = hoje + timedelta(hours=prazo_dias)
            else:
                data_fatal = hoje + timedelta(days=prazo_dias)
            
            resultado["data_fatal_sugerida"] = data_fatal.strftime("%Y-%m-%d")
            resultado["data_fatal_formatada"] = data_fatal.strftime("%d/%m/%Y")
            resultado["dias_restantes"] = prazo_dias
            resultado["mensagem_usuario"] = (
                f"⚠️ IA identificou prazo de {prazo_dias} dias. "
                f"Data fatal sugerida: {resultado['data_fatal_formatada']}. Confere?"
            )
        else:
            resultado["data_fatal_sugerida"] = None
            resultado["mensagem_usuario"] = "IA não identificou prazo explícito neste email."
        
        resultado["status"] = "sugestao_ia"
        resultado["requer_confirmacao"] = True
        return resultado

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

def analisar_email_juridico(assunto: str, corpo: str, remetente: str = "") -> Dict:
    """
    Wrapper para análise de email de intimação com IA.
    Extrai prazos, calcula data fatal sugerida.
    
    Returns:
        Dict com prazo_identificado, prazo_dias, data_fatal_sugerida, etc
    """
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.analisar_email_juridico(assunto, corpo, remetente)

def analisar_processo_completo(id_processo: int, dados_processo: Dict, historico_movimentos: List[Dict], force_refresh: bool = False) -> Dict:
    """
    OTIMIZAÇÃO: Single Shot Prompting com cache em banco.
    Retorna análise completa do processo (estratégia, riscos, financeiro, mensagem).
    Reduz consumo de API em ~80%.
    
    Args:
        id_processo: ID do processo
        dados_processo: Dict com dados do processo
        historico_movimentos: Lista de movimentos
        force_refresh: Se True, ignora cache e força nova análise
        
    Returns:
        Dict com todas as análises consolidadas
    """
    global _gemini_instance
    if _gemini_instance is None:
        inicializar_gemini()
    return _gemini_instance.analisar_processo_completo(id_processo, dados_processo, historico_movimentos, force_refresh)
