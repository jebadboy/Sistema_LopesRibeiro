import logging
import pandas as pd
import database_adapter as adapter
from datetime import datetime

logger = logging.getLogger(__name__)

# Inicializar signals (pode ser None se módulo signals não for usado)
signals = None
try:
    from modules import signals
except ImportError:
    pass  # signals é opcional

def init_db():
    """Inicializa o banco de dados (Schema) se necessário."""
    if adapter.USE_POSTGRES:
        # Em produção com Supabase, assumimos que o schema já foi criado via scripts
        # ou que o usuário vai rodar o script de migração.
        return

    # Schema para SQLite (Desenvolvimento Local)
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabela de Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                pergunta_secreta TEXT,
                resposta_secreta_hash TEXT,
                email TEXT,
                reset_token TEXT,
                reset_expiry TEXT
            )
        ''')

        # Migração: Adicionar colunas se não existirem (para bancos já criados)
        try:
            cursor.execute("SELECT pergunta_secreta FROM usuarios LIMIT 1")
        except:
            logger.info("Migrando tabela usuarios: adicionando colunas de segurança (pergunta)")
            try:
                cursor.execute("ALTER TABLE usuarios ADD COLUMN pergunta_secreta TEXT")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN resposta_secreta_hash TEXT")
                conn.commit()
            except Exception as e:
                logger.error(f"Erro na migração de usuarios (pergunta): {e}")

        try:
            cursor.execute("SELECT email FROM usuarios LIMIT 1")
        except:
            logger.info("Migrando tabela usuarios: adicionando colunas de email")
            try:
                cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN reset_token TEXT")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN reset_expiry TEXT")
                conn.commit()
            except Exception as e:
                logger.error(f"Erro na migração de usuarios (email): {e}")

        # 2. Tabela de Clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf_cnpj TEXT,
                email TEXT,
                telefone TEXT,
                telefone_fixo TEXT,
                profissao TEXT,
                estado_civil TEXT,
                cep TEXT,
                endereco TEXT,
                numero_casa TEXT,
                complemento TEXT,
                bairro TEXT,
                cidade TEXT,
                estado TEXT,
                obs TEXT,
                status_cliente TEXT DEFAULT 'EM NEGOCIAÇÃO',
                link_drive TEXT,
                data_cadastro TEXT,
                proposta_valor REAL,
                proposta_entrada REAL,
                proposta_parcelas INTEGER,
                proposta_objeto TEXT,
                proposta_pagamento TEXT,
                status_proposta TEXT,
                tipo_pessoa TEXT,
                proposta_data_pagamento TEXT,
                link_procuracao TEXT,
                link_hipossuficiencia TEXT,
                nacionalidade TEXT,
                rg TEXT,
                orgao_emissor TEXT,
                data_nascimento TEXT
            )
        ''')
        
        # 3. Tabela de Processos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                cliente_nome TEXT,
                area TEXT,
                acao TEXT,
                vara TEXT,
                status TEXT DEFAULT 'Ativo',
                proximo_prazo TEXT,
                responsavel TEXT,
                status_processo TEXT,
                parceiro_nome TEXT,
                parceiro_percentual REAL,
                pasta_drive_link TEXT,
                tipo_honorario TEXT,
                fase_processual TEXT,
                id_cliente INTEGER REFERENCES clientes(id),
                valor_causa REAL,
                data_distribuicao TEXT,
                link_drive TEXT,
                comarca TEXT,
                obs TEXT
            )
        ''')
        
        # 4. Tabela de Financeiro (NOVA - necessária para outras tabelas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financeiro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                tipo TEXT NOT NULL,
                categoria TEXT,
                descricao TEXT,
                valor REAL NOT NULL,
                status_pagamento TEXT DEFAULT 'Pendente',
                vencimento TEXT,
                id_cliente INTEGER REFERENCES clientes(id),
                id_processo INTEGER REFERENCES processos(id),
                meio_pagamento TEXT,
                comprovante_link TEXT,
                obs TEXT,
                cliente TEXT,
                status TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5. Tabela de Andamentos (CORRIGIDA - removido PRIMARY KEY duplicado)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS andamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_processo INTEGER NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                tipo TEXT,
                responsavel TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 6. Tabela de Parcelas (NOVA - separada de andamentos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parcelas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lancamento_financeiro INTEGER NOT NULL REFERENCES financeiro(id) ON DELETE CASCADE,
                numero_parcela INTEGER NOT NULL,
                total_parcelas INTEGER NOT NULL,
                valor_parcela REAL NOT NULL,
                vencimento TEXT NOT NULL,
                status_parcela TEXT DEFAULT 'pendente',
                pago_em TEXT,
                obs TEXT
            )
        ''')
        
        # 7. Tabela de Agenda (NOVA - necessária para get_agenda_eventos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                data_evento TEXT NOT NULL,
                hora_evento TEXT,
                tipo_evento TEXT,
                id_processo INTEGER REFERENCES processos(id),
                id_cliente INTEGER REFERENCES clientes(id),
                google_event_id TEXT,
                status TEXT DEFAULT 'pendente',
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 8. Tabela de Configurações (NOVA - necessária para get_config/set_config)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 9. Tabela de Timeline do Cliente (NOVA - para histórico do cliente)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cliente_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                tipo_evento TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                icone TEXT,
                data_evento TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 10. Tabela de Documentos Drive (NOVA - para vincular docs do Drive)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documentos_drive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT,
                drive_id TEXT,
                web_link TEXT,
                id_cliente INTEGER REFERENCES clientes(id),
                id_processo INTEGER REFERENCES processos(id),
                data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
                obs TEXT
            )
        ''')
        
        # 11. Tabela Modelos de Proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_modelo TEXT UNIQUE NOT NULL,
                area_atuacao TEXT,
                titulo TEXT,
                descricao TEXT,
                lido INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 12. Tabela Configurações de Aniversários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_aniversarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dias_antecedencia INTEGER DEFAULT 7,
                template_mensagem TEXT,
                ativo INTEGER DEFAULT 1
            )
        ''')

        # 13. Tabela Histórico de IA (NOVA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT,
                tipo TEXT,
                input TEXT,
                output TEXT,
                data_hora TEXT,
                processo_id INTEGER
            )
        ''')

        # 14. Tabela de Logs de Auditoria (EXPANDIDA para Sprint 2)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                tabela TEXT,
                registro_id INTEGER,
                campo TEXT,
                valor_anterior TEXT,
                valor_novo TEXT,
                details TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migração: Adicionar colunas novas se tabela já existir
        try:
            cursor.execute("SELECT action FROM audit_logs LIMIT 1")
        except:
            logger.info("Migrando tabela audit_logs: adicionando coluna action")
            try:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN action TEXT")
                conn.commit()
            except Exception as e:
                logger.error(f"Erro na migração de audit_logs (action): {e}")

        try:
            cursor.execute("SELECT tabela FROM audit_logs LIMIT 1")
        except:
            logger.info("Migrando tabela audit_logs: adicionando colunas de auditoria detalhada")
            try:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN tabela TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN registro_id INTEGER")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN campo TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN valor_anterior TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN valor_novo TEXT")
                conn.commit()
            except Exception as e:
                logger.error(f"Erro na migração de audit_logs (detalhes): {e}")

        # 15. Tabela Partes do Processo (NOVA - Faltava no Schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partes_processo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_processo INTEGER REFERENCES processos(id) ON DELETE CASCADE,
                nome TEXT NOT NULL,
                tipo TEXT,
                cpf_cnpj TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 16. Tabela Modelos de Documentos (NOVA - Faltava no Schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos_documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                categoria TEXT,
                conteudo TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 17. Tabela Tokens Públicos (Refatorado para o DB principal)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens_publicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                id_processo INTEGER NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                data_expiracao TEXT,
                ativo INTEGER DEFAULT 1,
                acessos INTEGER DEFAULT 0,
                ultimo_acesso TEXT
            )
        ''')
        
        # 18. Tabela AI Insights (NOVA - Faltava no Schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                titulo TEXT,
                descricao TEXT,
                prioridade TEXT DEFAULT 'media',
                acao_sugerida TEXT,
                link_acao TEXT,
                lido INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 19. Tabela AI Cache (NOVA - Faltava no Schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_cache (
                hash_input TEXT PRIMARY KEY,
                resposta TEXT,
                data_criacao TEXT,
                validade INTEGER
            )
        ''')

        # 20. Tabela Alertas de E-mail (NOVA - Workspace Integration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alertas_email (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                remetente TEXT,
                assunto TEXT,
                numero_processo TEXT,
                valor_detectado REAL,
                data_recebimento TEXT,
                corpo_resumo TEXT,
                processado INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 21. Tabela Transações Bancárias (Conciliação)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacoes_bancarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_transacao TEXT NOT NULL,
                valor REAL NOT NULL,
                tipo TEXT NOT NULL,
                descricao TEXT,
                transaction_id TEXT UNIQUE NOT NULL,
                arquivo_origem TEXT,
                data_importacao TEXT DEFAULT CURRENT_TIMESTAMP,
                status_conciliacao TEXT DEFAULT 'Pendente',
                id_financeiro INTEGER REFERENCES financeiro(id),
                conciliado_por TEXT,
                data_conciliacao TEXT,
                link_google_drive TEXT,
                tipo_origem TEXT,
                conta_origem TEXT
            )
        ''')


        # Run Migration for Andamentos (IA)
        check_migration_andamentos(cursor)
        
        
        # --- MIGRAÇÕES AUTOMÁTICAS ---
        # Garantir que processos tenha coluna 'status'
        try:
            cursor.execute("SELECT status FROM processos LIMIT 1")
        except:
             logger.info("Migrando tabela processos: adicionando coluna status")
             try:
                 cursor.execute("ALTER TABLE processos ADD COLUMN status TEXT DEFAULT 'Ativo'")
                 conn.commit()
             except Exception as e:
                 logger.error(f"Erro na migração de processos (status): {e}")

        # Garantir que processos tenha coluna 'assunto'
        try:
            cursor.execute("SELECT assunto FROM processos LIMIT 1")
        except:
             logger.info("Migrando tabela processos: adicionando coluna assunto")
             try:
                 cursor.execute("ALTER TABLE processos ADD COLUMN assunto TEXT")
                 conn.commit()
             except Exception as e:
                 logger.error(f"Erro na migração de processos (assunto): {e}")
        
        # Garantir que processos tenha coluna 'comarca'
        try:
            cursor.execute("SELECT comarca FROM processos LIMIT 1")
        except:
             logger.info("Migrando tabela processos: adicionando coluna comarca")
             try:
                 cursor.execute("ALTER TABLE processos ADD COLUMN comarca TEXT")
                 conn.commit()
             except Exception as e:
                 logger.error(f"Erro na migração de processos (comarca): {e}")
        
        # Inserir configuração padrão se não existir
        cursor.execute("SELECT COUNT(*) as cnt FROM config_aniversarios")
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute('''
                INSERT INTO config_aniversarios (template_mensagem) 
                VALUES ('Olá {nome}! 🎉🎂\n\nFeliz Aniversário! Desejamos muita saúde, paz e prosperidade neste novo ciclo de vida!\n\nUm abraço da equipe!')
            ''')
            conn.commit()
        
        # --- MIGRAÇÃO LGPD (Fase 2) ---
        # Adicionar colunas de consentimento se não existirem
        try:
            cursor.execute("SELECT lgpd_consentimento FROM clientes LIMIT 1")
        except:
            logger.info("Migrando tabela clientes: adicionando colunas LGPD")
            try:
                cursor.execute("ALTER TABLE clientes ADD COLUMN lgpd_consentimento INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE clientes ADD COLUMN lgpd_data_consentimento TEXT")
                cursor.execute("ALTER TABLE clientes ADD COLUMN lgpd_ip_consentimento TEXT")
                conn.commit()
                logger.info("Colunas LGPD adicionadas com sucesso")
            except Exception as e:
                logger.error(f"Erro na migração LGPD: {e}")
        
        # Configuração de prazo de retenção LGPD (5 anos)
        if not get_config('lgpd_retencao_anos'):
            try:
                cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('lgpd_retencao_anos', '5')")
                conn.commit()
            except Exception as e:
                logger.debug(f"Erro ao configurar retenção LGPD: {e}")

        # --- MIGRAÇÃO TRANSAÇÕES BANCÁRIAS (Novos Campos) ---
        try:
            cursor.execute("SELECT tipo_origem FROM transacoes_bancarias LIMIT 1")
        except:
             logger.info("Migrando tabela transacoes_bancarias: adicionando colunas de origem")
             try:
                 cursor.execute("ALTER TABLE transacoes_bancarias ADD COLUMN tipo_origem TEXT")
                 cursor.execute("ALTER TABLE transacoes_bancarias ADD COLUMN conta_origem TEXT")
                 conn.commit()
             except Exception as e:
                 # Se a tabela não existir, vai falhar silenciosamente aqui, mas o CREATE TABLE acima já resolveu
                 pass
        
def crud_insert(table, data, log_msg=""):
    """Insere um registro no banco e retorna o ID."""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s' if adapter.USE_POSTGRES else '?'] * len(data))
    
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    
    if adapter.USE_POSTGRES:
        query += " RETURNING id"
    
    cursor = adapter.get_adapter().execute_query(query, tuple(data.values()))
    
    row_id = None
    if adapter.USE_POSTGRES:
        result = cursor.fetchone()
        if result:
            row_id = result['id']
    else:
        row_id = cursor.lastrowid
        
    logger.info(f"{log_msg} (ID: {row_id})")
    
    # Emitir sinal
    if signals:
        signals.emit(f"insert_{table}", {'id': row_id, 'data': data})
        
    return row_id

def crud_update(table, data, where_clause, params, log_msg=""):
    """Atualiza registros no banco COM auditoria automática."""
    
    # NOVO: Buscar valores anteriores para auditoria (antes do UPDATE)
    registro_id = None
    valores_anteriores = None
    try:
        # Tentar obter registro_id do params
        if params:
            registro_id = params[0] if isinstance(params[0], int) else None
        
        # Buscar valores anteriores para comparar
        select_query = f"SELECT * FROM {table} WHERE {where_clause}"
        if adapter.USE_POSTGRES:
            select_query = select_query.replace('?', '%s')
        valores_anteriores = sql_get_query(select_query, params)
    except Exception as e:
        logger.debug(f"Não foi possível obter valores anteriores para auditoria: {e}")
    
    # Executar o UPDATE
    placeholders = ['%s' if adapter.USE_POSTGRES else '?' for _ in data]
    set_clause = ', '.join([f"{k} = {p}" for k, p in zip(data.keys(), placeholders)])
    
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    
    # Ajustar placeholders do where_clause se for Postgres
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
    
    full_params = tuple(data.values()) + tuple(params)
    adapter.get_adapter().execute_query(query, full_params)
    logger.info(log_msg)
    
    # NOVO: Registrar alterações na auditoria
    if valores_anteriores is not None and not valores_anteriores.empty:
        try:
            row_anterior = valores_anteriores.iloc[0]
            for campo, valor_novo in data.items():
                valor_anterior = row_anterior.get(campo)
                # Só registrar se realmente mudou
                if str(valor_anterior) != str(valor_novo):
                    audit_detalhado(
                        tabela=table,
                        registro_id=registro_id,
                        campo=campo,
                        valor_anterior=valor_anterior,
                        valor_novo=valor_novo,
                        acao="UPDATE"
                    )
        except Exception as e:
            logger.debug(f"Erro ao registrar auditoria: {e}")
    
    # Emitir sinal
    if signals:
        signals.emit(f"update_{table}", {'data': data, 'where': where_clause, 'params': params})

def crud_delete(table, where_clause, params, log_msg=""):
    """Remove registros do banco."""
    query = f"DELETE FROM {table} WHERE {where_clause}"
    
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
        
    # Garantir que params seja uma tupla
    if not isinstance(params, (list, tuple)):
        params = (params,)
        
    adapter.get_adapter().execute_query(query, params)
    logger.info(log_msg)
    
    # Emitir sinal
    if signals:
        signals.emit(f"delete_{table}", {'where': where_clause, 'params': params})

# --- Funções Restauradas ---

def sql_get_query(query, params=None):
    """Executa uma query SELECT e retorna um DataFrame."""
    try:
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
            
        rows = adapter.get_adapter().fetch_all(query, params)
        
        # Converter sqlite3.Row (ou RealDictRow) para dict para preservar nomes das colunas
        if rows:
            data = [dict(row) for row in rows]
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Erro no sql_get_query: {e}")
        return pd.DataFrame()

def sql_get(table, order_by=None):
    """Retorna todos os registros de uma tabela."""
    query = f"SELECT * FROM {table}"
    if order_by:
        query += f" ORDER BY {order_by}"
    return sql_get_query(query)

def sql_run(query, params=None):
    """Executa uma query que não retorna dados (INSERT, UPDATE, DELETE)."""
    try:
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
            
        adapter.get_adapter().execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"Erro no sql_run: {e}")
        return False

def salvar_modelo_documento(titulo, categoria, conteudo):
    """Salva um modelo de documento no banco."""
    query = "INSERT INTO modelos_documentos (titulo, categoria, conteudo) VALUES (?, ?, ?)"
    sql_run(query, (titulo, categoria, conteudo))

def excluir_modelo_documento(id_modelo):
    """Exclui um modelo de documento."""
    sql_run("DELETE FROM modelos_documentos WHERE id = ?", (id_modelo,))

def gerar_documento_final(id_modelo, dados_cliente):
    """Gera o texto final do documento substituindo os placeholders."""
    # Buscar modelo
    df = sql_get_query("SELECT conteudo FROM modelos_documentos WHERE id = ?", (id_modelo,))
    if df.empty:
        return "Erro: Modelo não encontrado."
    
    conteudo = df.iloc[0]['conteudo']
    
    # Substituir placeholders
    for chave, valor in dados_cliente.items():
        placeholder = f"{{{chave}}}"
        if placeholder in conteudo:
            conteudo = conteudo.replace(placeholder, str(valor))
            
    return conteudo

def busca_global(termo: str, limite: int = 20) -> dict:
    """
    Busca termo em clientes, processos e financeiro simultaneamente.
    
    Args:
        termo: Texto a buscar
        limite: Máximo de resultados por categoria
    
    Returns:
        dict: {
            'clientes': DataFrame,
            'processos': DataFrame,
            'financeiro': DataFrame,
            'total': int
        }
    """
    resultado = {
        'clientes': pd.DataFrame(), 
        'processos': pd.DataFrame(), 
        'financeiro': pd.DataFrame(),
        'total': 0
    }
    
    if not termo or len(termo) < 2:
        return resultado
    
    termo_like = f"%{termo}%"
    
    try:
        # Buscar em clientes
        resultado['clientes'] = sql_get_query("""
            SELECT id, nome, cpf_cnpj, telefone, email, 'cliente' as tipo_resultado
            FROM clientes 
            WHERE nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ? OR telefone LIKE ?
            ORDER BY nome ASC
            LIMIT ?
        """, (termo_like, termo_like, termo_like, termo_like, limite))
    except Exception as e:
        logger.debug(f"Erro na busca de clientes: {e}")
    
    try:
        # Buscar em processos
        resultado['processos'] = sql_get_query("""
            SELECT id, numero, cliente_nome, acao, fase_processual, 'processo' as tipo_resultado
            FROM processos 
            WHERE numero LIKE ? OR cliente_nome LIKE ? OR acao LIKE ? OR obs LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (termo_like, termo_like, termo_like, termo_like, limite))
    except Exception as e:
        logger.debug(f"Erro na busca de processos: {e}")
    
    try:
        # Buscar em financeiro
        resultado['financeiro'] = sql_get_query("""
            SELECT id, descricao, cliente, valor, tipo, status, 'financeiro' as tipo_resultado
            FROM financeiro 
            WHERE descricao LIKE ? OR cliente LIKE ? OR categoria LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (termo_like, termo_like, termo_like, limite))
    except Exception as e:
        logger.debug(f"Erro na busca de financeiro: {e}")
    
    # Calcular total
    resultado['total'] = (
        len(resultado['clientes']) + 
        len(resultado['processos']) + 
        len(resultado['financeiro'])
    )
    
    return resultado

def get_agenda_eventos():
    """Retorna eventos da agenda."""
    return sql_get("agenda")


def get_connection():
    """Retorna conexão com o banco de dados (wrapper para adapter)."""
    return adapter.get_connection()

# Funções auxiliares para compatibilidade
def run_query(query, params=None):
    return adapter.get_adapter().fetch_all(query, params)

def get_config(key, default=None):
    """Retorna valor de configuração."""
    query = "SELECT value FROM config WHERE key = ?"
    res = adapter.get_adapter().fetch_one(query, (key,))
    return res['value'] if res else default

def set_config(key, value):
    """Define valor de configuração."""
    if adapter.USE_POSTGRES:
        query = """
            INSERT INTO config (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    else:
        query = "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)"
    
    adapter.get_adapter().execute_query(query, (key, value))

def get_historico(id_processo):
    """Retorna histórico de andamentos de um processo."""
    # Selecionar colunas extras para IA
    query = "SELECT data, descricao, responsavel, analise_ia, urgente, tipo FROM andamentos WHERE id_processo = ? ORDER BY data DESC"
    return sql_get_query(query, (id_processo,))

def get_dre_data(data_inicio, data_fim):
    """Retorna dados para o DRE."""
    query = """
        SELECT tipo, categoria, SUM(valor) as total
        FROM financeiro
        WHERE data BETWEEN ? AND ?
        AND status_pagamento = 'Pago'
        GROUP BY tipo, categoria
    """
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
    
    return sql_get_query(query, (data_inicio, data_fim))

def get_rentabilidade_clientes(data_inicio, data_fim):
    """Retorna dados de rentabilidade por cliente."""
    query = """
        SELECT 
            c.nome as cliente,
            SUM(CASE WHEN f.tipo = 'Entrada' THEN f.valor ELSE 0 END) as receita,
            SUM(CASE WHEN f.tipo = 'Saída' THEN f.valor ELSE 0 END) as despesa
        FROM financeiro f
        JOIN clientes c ON f.id_cliente = c.id
        WHERE f.data BETWEEN ? AND ?
        AND f.status_pagamento = 'Pago'
        GROUP BY c.nome
    """
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
        
    df = sql_get_query(query, (data_inicio, data_fim))
    if not df.empty:
        df['lucro'] = df['receita'] - df['despesa']
        df['margem'] = (df['lucro'] / df['receita']) * 100
        df = df.sort_values('lucro', ascending=False)
    return df

def relatorio_inadimplencia():
    """Retorna relatório de inadimplência."""
    query = """
        SELECT 
            c.nome as Cliente,
            f.descricao as Descrição,
            f.vencimento as Vencimento,
            f.valor as Valor
        FROM financeiro f
        LEFT JOIN clientes c ON f.id_cliente = c.id
        WHERE f.tipo = 'Entrada'
        AND f.status_pagamento = 'Pendente'
        AND f.vencimento < DATE('now')
    """
    if adapter.USE_POSTGRES:
        query = query.replace("DATE('now')", "CURRENT_DATE")
        
    return sql_get_query(query)

def cpf_existe(cpf_cnpj):
    """Verifica se um CPF/CNPJ já existe no banco."""
    query = "SELECT id FROM clientes WHERE cpf_cnpj = ?"
    res = adapter.get_adapter().fetch_one(query, (cpf_cnpj,))
    return res is not None

def criar_backup(force: bool = False) -> dict:
    """
    Cria um backup do banco de dados com melhorias Sprint 3.
    
    Features:
    - Compressão gzip para economizar espaço
    - Rotação automática (mantém últimos 7 dias)
    - Verificação de integridade
    - Log de auditoria
    
    Args:
        force: Forçar backup mesmo se já existe um do dia
        
    Returns:
        dict: {'success': bool, 'file': str, 'size_mb': float, 'message': str}
    """
    import shutil
    import os
    import gzip
    import hashlib
    
    result = {'success': False, 'file': None, 'size_mb': 0, 'message': ''}
    
    if adapter.USE_POSTGRES:
        # Backups no Postgres/Supabase são gerenciados pela plataforma
        result['message'] = 'PostgreSQL: backups gerenciados pela plataforma'
        return result
        
    try:
        db_file = 'sistema.db'
        if not os.path.exists(db_file):
            result['message'] = 'Banco de dados não encontrado'
            return result
            
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Verificar se já existe backup do dia (evitar duplicados)
        today = datetime.now().strftime('%Y%m%d')
        existing_today = [f for f in os.listdir(backup_dir) if today in f]
        
        if existing_today and not force:
            result['message'] = f'Backup do dia já existe: {existing_today[0]}'
            result['success'] = True  # Não é erro, apenas skip
            return result
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/sistema_backup_{timestamp}.db.gz"
        backup_temp = f"{backup_dir}/sistema_backup_{timestamp}.db"
        
        # 1. Copiar banco de dados
        shutil.copy2(db_file, backup_temp)
        
        # 2. Verificar integridade do backup
        original_size = os.path.getsize(db_file)
        backup_size = os.path.getsize(backup_temp)
        
        if backup_size != original_size:
            os.remove(backup_temp)
            result['message'] = 'Erro: tamanho do backup não corresponde ao original'
            return result
        
        # 3. Compactar com gzip
        with open(backup_temp, 'rb') as f_in:
            with gzip.open(backup_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remover arquivo temporário não compactado
        os.remove(backup_temp)
        
        # 4. Calcular hash para verificação futura
        with gzip.open(backup_file, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # Salvar hash em arquivo separado
        with open(f"{backup_file}.md5", 'w') as f:
            f.write(file_hash)
        
        compressed_size = os.path.getsize(backup_file)
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(
            f"Backup criado: {backup_file} | "
            f"Original: {original_size/1024/1024:.2f}MB | "
            f"Compactado: {compressed_size/1024/1024:.2f}MB | "
            f"Compressão: {compression_ratio:.1f}%"
        )
        
        # 5. Rotação: manter últimos 7 backups
        backups = sorted([
            f for f in os.listdir(backup_dir) 
            if f.startswith('sistema_backup_') and f.endswith('.db.gz')
        ])
        
        while len(backups) > 7:
            old_backup = backups.pop(0)
            old_path = os.path.join(backup_dir, old_backup)
            old_md5 = f"{old_path}.md5"
            
            os.remove(old_path)
            if os.path.exists(old_md5):
                os.remove(old_md5)
            
            logger.info(f"Backup antigo removido (rotação): {old_backup}")
        
        # 6. Log de auditoria
        try:
            audit('backup_created', {
                'file': backup_file,
                'size_mb': round(compressed_size / 1024 / 1024, 2),
                'hash': file_hash,
                'compression': f'{compression_ratio:.1f}%'
            })
        except:
            pass  # Não falhar se auditoria falhar
        
        result['success'] = True
        result['file'] = backup_file
        result['size_mb'] = round(compressed_size / 1024 / 1024, 2)
        result['message'] = f'Backup criado com sucesso ({compression_ratio:.1f}% compressão)'
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        result['message'] = str(e)
        return result

def verificar_backup(backup_file: str) -> bool:
    """
    Verifica integridade de um backup.
    
    Args:
        backup_file: Caminho do arquivo de backup (.db.gz)
        
    Returns:
        True se backup está íntegro
    """
    import gzip
    import hashlib
    
    try:
        md5_file = f"{backup_file}.md5"
        
        if not os.path.exists(md5_file):
            logger.warning(f"Arquivo MD5 não encontrado para {backup_file}")
            return False
        
        # Ler hash esperado
        with open(md5_file, 'r') as f:
            expected_hash = f.read().strip()
        
        # Calcular hash atual
        with gzip.open(backup_file, 'rb') as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        
        if actual_hash == expected_hash:
            logger.info(f"Backup verificado OK: {backup_file}")
            return True
        else:
            logger.error(f"Backup CORROMPIDO: {backup_file}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao verificar backup: {e}")
        return False

def restaurar_backup(backup_file: str) -> bool:
    """
    Restaura banco de dados a partir de um backup.
    
    Args:
        backup_file: Caminho do arquivo de backup (.db.gz)
        
    Returns:
        True se restauração foi bem-sucedida
    """
    import gzip
    import shutil
    
    if adapter.USE_POSTGRES:
        logger.error("Restauração não disponível para PostgreSQL")
        return False
    
    try:
        db_file = 'sistema.db'
        
        # 1. Verificar integridade do backup
        if not verificar_backup(backup_file):
            return False
        
        # 2. Fazer backup do banco atual (segurança)
        if os.path.exists(db_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy2(db_file, f'{db_file}.before_restore_{timestamp}')
        
        # 3. Descompactar e restaurar
        with gzip.open(backup_file, 'rb') as f_in:
            with open(db_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        logger.info(f"Banco restaurado de: {backup_file}")
        
        # 4. Auditoria
        try:
            audit('backup_restored', {'file': backup_file})
        except:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}")
        return False



def audit(action, details, user_id=None, username=None):
    """Registra um evento de auditoria."""
    try:
        import json
        
        # Converter dict para JSON string (compatibilidade PostgreSQL)
        if isinstance(details, dict):
            details = json.dumps(details, default=str)
        
        # Tentar pegar do contexto do Streamlit se não fornecido
        if not user_id or not username:
             import streamlit as st
             if hasattr(st, 'session_state') and 'user_data' in st.session_state:
                 if not user_id: user_id = st.session_state.user_data.get('id')
                 if not username: username = st.session_state.user_data.get('username')
                 
        query = "INSERT INTO audit_logs (user_id, username, action, details) VALUES (?, ?, ?, ?)"
        sql_run(query, (user_id, username, action, details))
    except Exception as e:
        logger.error(f"Erro ao auditar: {e}")


def log_acesso_dados(tabela: str, registro_id: int, tipo_acesso: str = "VIEW"):
    """
    Registra acesso a dados pessoais conforme LGPD Art. 37.
    
    Args:
        tabela: Nome da tabela acessada (clientes, processos, etc.)
        registro_id: ID do registro acessado
        tipo_acesso: Tipo de acesso (VIEW, EXPORT, PRINT)
    """
    try:
        import streamlit as st
        user_id = None
        username = "Anônimo"
        
        if hasattr(st, 'session_state'):
            username = st.session_state.get('user', 'Sistema')
            if 'user_data' in st.session_state:
                user_id = st.session_state.user_data.get('id')
        
        audit(
            action=f"ACESSO_DADOS_{tipo_acesso}",
            details=f"Acesso a {tabela} ID {registro_id}",
            user_id=user_id,
            username=username
        )
        logger.debug(f"Log LGPD: {username} acessou {tabela}#{registro_id} ({tipo_acesso})")
        
    except Exception as e:
        # Não deixar erro de log quebrar a aplicação
        logger.debug(f"Erro no log_acesso_dados: {e}")

def audit_detalhado(tabela, registro_id, campo, valor_anterior, valor_novo, acao="UPDATE"):
    """
    Registra alteração detalhada para auditoria completa.
    
    Args:
        tabela: Nome da tabela alterada
        registro_id: ID do registro alterado
        campo: Nome do campo alterado
        valor_anterior: Valor antes da alteração
        valor_novo: Novo valor
        acao: Tipo de ação (INSERT, UPDATE, DELETE)
    """
    try:
        import streamlit as st
        username = "Sistema"
        user_id = None
        
        if hasattr(st, 'session_state'):
            username = st.session_state.get('user', 'Sistema')
            if 'user_data' in st.session_state:
                user_id = st.session_state.user_data.get('id')
        
        query = """
            INSERT INTO audit_logs 
            (user_id, username, action, tabela, registro_id, campo, valor_anterior, valor_novo, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Limitar tamanho dos valores para não sobrecarregar o banco
        val_ant = str(valor_anterior)[:500] if valor_anterior is not None else None
        val_novo = str(valor_novo)[:500] if valor_novo is not None else None
        
        sql_run(query, (
            user_id, 
            username, 
            acao, 
            tabela, 
            registro_id, 
            campo, 
            val_ant, 
            val_novo,
            datetime.now().isoformat()
        ))
        
        logger.debug(f"Auditoria: {acao} em {tabela}.{campo} (ID {registro_id})")
        
    except Exception as e:
        # Não deixar erro de auditoria quebrar a operação principal
        logger.debug(f"Erro no audit_detalhado: {e}")

def get_audit_logs(limite=100, filtro_tabela=None, filtro_usuario=None):
    """
    Retorna histórico de auditoria com filtros opcionais.
    
    Args:
        limite: Número máximo de registros
        filtro_tabela: Filtrar por tabela específica
        filtro_usuario: Filtrar por usuário específico
    
    Returns:
        DataFrame com os logs de auditoria
    """
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if filtro_tabela:
        query += " AND tabela = ?"
        params.append(filtro_tabela)
    
    if filtro_usuario:
        query += " AND username = ?"
        params.append(filtro_usuario)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limite)
    
    return sql_get_query(query, tuple(params))


def get_usuario_by_username(username):
    """Retorna dados de um usuário pelo username."""
    query = "SELECT * FROM usuarios WHERE username = ?"
    res = adapter.get_adapter().fetch_one(query, (username,))
    return res

def check_migration_andamentos(cursor):
    """
    Verifica e aplica migração na tabela de andamentos para suportar IA.
    Adiciona colunas: hash_id, analise_ia, urgente, data_analise
    """
    try:
        cursor.execute("PRAGMA table_info(andamentos)")
        cols = [c[1] for c in cursor.fetchall()]
        
        # Mapeamento de colunas novas
        new_cols = {
            'hash_id': 'TEXT',
            'analise_ia': 'TEXT',
            'urgente': 'BOOLEAN DEFAULT 0',
            'data_analise': 'TEXT'
        }
        
        for col, dtype in new_cols.items():
            if col not in cols:
                print(f"Migrating 'andamentos': Adding {col}...")
                try:
                    cursor.execute(f"ALTER TABLE andamentos ADD COLUMN {col} {dtype}")
                except Exception as e:
                    print(f"Error adding {col}: {e}")
        
        # Criar índice único separadamente
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_andamentos_hash ON andamentos(hash_id)")
        except Exception as e:
            print(f"Error creating index for hash_id: {e}")
                    
    except Exception as e:
        print(f"Migration check failed: {e}")


# ==================== CACHE DE PARTES POR NÚMERO CNJ ====================

def criar_tabela_partes_cache():
    """Cria tabela de cache de partes por número CNJ"""
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS partes_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_cnj TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    tipo TEXT,
                    cpf_cnpj TEXT,
                    tipo_pessoa TEXT DEFAULT 'Física',
                    is_cliente INTEGER DEFAULT 0,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(numero_cnj, nome)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_partes_cache_cnj ON partes_cache(numero_cnj)')
            conn.commit()
        except Exception as e:
            print(f"Erro ao criar tabela partes_cache: {e}")


def salvar_partes_cache(numero_cnj: str, partes: list):
    """
    Salva partes no cache associadas a um número CNJ.
    
    Args:
        numero_cnj: Número do processo (formatado ou não)
        partes: Lista de dicts com nome, tipo, cpf_cnpj, tipo_pessoa, is_cliente
    """
    import re
    numero_limpo = re.sub(r'\D', '', numero_cnj)
    
    # Garantir que a tabela existe
    criar_tabela_partes_cache()
    
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            for parte in partes:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO partes_cache 
                        (numero_cnj, nome, tipo, cpf_cnpj, tipo_pessoa, is_cliente)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        numero_limpo,
                        parte.get('nome', ''),
                        parte.get('tipo', 'INDEFINIDO'),
                        parte.get('cpf_cnpj', ''),
                        parte.get('tipo_pessoa', 'Física'),
                        1 if parte.get('is_cliente') else 0
                    ))
                except Exception as e:
                    print(f"Erro ao inserir parte: {e}")
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao salvar partes no cache: {e}")
            return False


def buscar_partes_cache(numero_cnj: str) -> list:
    """
    Busca partes do cache por número CNJ.
    
    Args:
        numero_cnj: Número do processo (formatado ou não)
        
    Returns:
        Lista de dicts com as partes encontradas
    """
    import re
    numero_limpo = re.sub(r'\D', '', numero_cnj)
    
    # Garantir que a tabela existe
    criar_tabela_partes_cache()
    
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT nome, tipo, cpf_cnpj, tipo_pessoa, is_cliente 
                FROM partes_cache 
                WHERE numero_cnj = ?
                ORDER BY is_cliente DESC, id ASC
            ''', (numero_limpo,))
            
            rows = cursor.fetchall()
            
            partes = []
            for row in rows:
                partes.append({
                    'nome': row[0],
                    'tipo': row[1],
                    'cpf_cnpj': row[2],
                    'tipo_pessoa': row[3],
                    'is_cliente': bool(row[4]),
                    'fonte': 'Cache'
                })
            
            return partes
            
        except Exception as e:
            print(f"Erro ao buscar partes do cache: {e}")
            return []


def limpar_partes_cache(numero_cnj: str):
    """Remove partes do cache para um número CNJ específico"""
    import re
    numero_limpo = re.sub(r'\D', '', numero_cnj)
    
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM partes_cache WHERE numero_cnj = ?', (numero_limpo,))
            conn.commit()
        except Exception as e:
            print(f"Erro ao limpar cache: {e}")
