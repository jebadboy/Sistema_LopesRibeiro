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

        # 14. Tabela de Logs de Auditoria (NOVA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                details TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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
    """Atualiza registros no banco."""
    placeholders = ['%s' if adapter.USE_POSTGRES else '?' for _ in data]
    set_clause = ', '.join([f"{k} = {p}" for k, p in zip(data.keys(), placeholders)])
    
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    
    # Ajustar placeholders do where_clause se for Postgres
    if adapter.USE_POSTGRES:
        # Substituição mais segura: apenas se o where_clause usar ?
        # Idealmente, o caller já deveria passar %s se soubesse que é Postgres,
        # mas para manter compatibilidade com código existente que usa ?, fazemos replace.
        # Risco: Se houver '?' literal na string de busca, vai quebrar.
        # Solução: Assumimos que where_clause é estrutural (ex: "id = ?") e params contém os dados.
        query = query.replace('?', '%s')
    
    full_params = tuple(data.values()) + tuple(params)
    adapter.get_adapter().execute_query(query, full_params)
    logger.info(log_msg)
    
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

def criar_backup():
    """Cria um backup do banco de dados (apenas SQLite)."""
    if adapter.USE_POSTGRES:
        # Backups no Postgres/Supabase são gerenciados pela plataforma
        return
        
    import shutil
    import os
    
    try:
        db_file = 'sistema.db'
        if os.path.exists(db_file):
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{backup_dir}/sistema_backup_{timestamp}.db"
            shutil.copy2(db_file, backup_file)
            logger.info(f"Backup criado com sucesso: {backup_file}")
            
            # Manter apenas os últimos 5 backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('sistema_backup_')])
            while len(backups) > 5:
                os.remove(os.path.join(backup_dir, backups.pop(0)))
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")

def audit(action, details, user_id=None, username=None):
    """Registra um evento de auditoria."""
    try:
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
