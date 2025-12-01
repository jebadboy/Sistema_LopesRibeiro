import sqlite3
import pandas as pd
from datetime import datetime
import shutil
import os
from contextlib import contextmanager
import logging
import hashlib
import re

DB_NAME = 'dados_escritorio.db'
TABELAS_VALIDAS = [
    'clientes', 'financeiro', 'processos', 'andamentos',
    'agenda', 'documentos_processo', 'parcelamentos', 'modelos_proposta',
    'usuarios', 'config'
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_lopes_ribeiro.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONEXÃO E BACKUP ---

@contextmanager
def get_connection():
    """Gerenciador de contexto para conexão segura com o banco."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # Permite acesso por nome de coluna
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro na conexão com banco: {e}")
        raise
    finally:
        if conn:
            conn.close()

def criar_backup():
    """Cria backup manual do banco de dados."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    backup_name = f"{backup_dir}/backup_{timestamp}.db"
    try:
        shutil.copy(DB_NAME, backup_name)
        logger.info(f"Backup criado: {backup_name}")
        return f"Backup criado: {backup_name}"
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return f"Erro no backup: {e}"

# Alias para compatibilidade com app.py
backup_database = criar_backup

def init_db():
    """
    Inicializa o banco de dados criando tabelas principais se não existirem.
    Chamada pelo app.py na inicialização do sistema.
    """
    try:
        with get_connection() as conn:
            c = conn.cursor()
            
            # Tabela de Clientes
            c.execute('''
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
                    proposta_data_pagamento TEXT,
                    tipo_pessoa TEXT DEFAULT 'Física',
                    link_procuracao TEXT,
                    link_hipossuficiencia TEXT
                )
            ''')
            
            # Tabela Financeira
            c.execute('''
                CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    tipo TEXT,
                    categoria TEXT,
                    descricao TEXT,
                    valor REAL,
                    vencimento TEXT,
                    status_pagamento TEXT,
                    comprovante TEXT,
                    id_cliente INTEGER,
                    id_processo INTEGER,
                    percentual_parceria REAL,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id),
                    FOREIGN KEY (id_processo) REFERENCES processos(id)
                )
            ''')
            
            # Tabela de Processos
            c.execute('''
                CREATE TABLE IF NOT EXISTS processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_processo TEXT,
                    cliente TEXT,
                    parte_contraria TEXT,
                    vara TEXT,
                    comarca TEXT,
                    status TEXT,
                    fase_processual TEXT,
                    valor_causa REAL,
                    data_distribuicao TEXT,
                    link_drive TEXT,
                    obs TEXT,
                    id_cliente INTEGER,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id)
                )
            ''')
            
            # Tabela de Andamentos
            c.execute('''
                CREATE TABLE IF NOT EXISTS andamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_processo INTEGER,
                    data TEXT,
                    descricao TEXT,
                    responsavel TEXT,
                    FOREIGN KEY (id_processo) REFERENCES processos(id)
                )
            ''')
            
            conn.commit()
            logger.info("Banco de dados inicializado com sucesso (Tabelas Core)")
            
            # Inicializar tabelas v2
            inicializar_tabelas_v2()
            
            # Inicializar tabela de tokens públicos
            try:
                import token_manager
                token_manager.inicializar_tabela_tokens()
            except Exception as e:
                logger.warning(f"Erro ao inicializar tokens públicos: {e}")
            
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise

# --- FUNÇÕES GERAIS DE SQL ---

def sql_run(query, params=()):
    """Executa uma query SQL de modificação (INSERT, UPDATE, DELETE)."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return c.lastrowid
    except Exception as e:
        logger.error(f"Erro ao executar SQL: {query} - Params: {params} - Erro: {e}")
        raise

def sql_get(tabela, ordem=""):
    """Busca dados de uma tabela com validação de segurança."""
    if tabela not in TABELAS_VALIDAS:
        logger.error(f"Tentativa de acesso a tabela inválida: {tabela}")
        raise ValueError(f"Tabela inválida: {tabela}. Tabelas permitidas: {TABELAS_VALIDAS}")
    
    # Validação rigorosa do parâmetro 'ordem' para prevenir SQL Injection
    if ordem:
        # Permite apenas letras, números, espaços, vírgulas e underscores
        # Exemplo válido: "nome ASC", "data_criacao DESC, id ASC"
        if not re.match(r"^[a-zA-Z0-9_, ]+$", ordem):
             logger.warning(f"Tentativa de injeção em ORDER BY: {ordem}")
             raise ValueError("Parâmetro de ordenação inválido.")

    try:
        with get_connection() as conn:
            sql = f"SELECT * FROM {tabela}"
            if ordem: 
                sql += f" ORDER BY {ordem}"
            return pd.read_sql_query(sql, conn)
    except Exception as e:
        logger.error(f"Erro ao buscar dados da tabela {tabela}: {e}")
        return pd.DataFrame()  # Retorna DataFrame vazio em caso de erro

# --- FUNÇÕES HELPER CRUD COM LOGGING AUTOMÁTICO ---

def crud_insert(tabela, dados_dict, contexto=""):
    """
    Helper para INSERT com logging automático.
    """
    colunas = ', '.join(dados_dict.keys())
    placeholders = ', '.join(['?' for _ in dados_dict])
    valores = tuple(dados_dict.values())
    
    query = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
    
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(query, valores)
            conn.commit()
            novo_id = c.lastrowid
            logger.info(f"INSERT bem-sucedido em '{tabela}' (ID: {novo_id}) - {contexto}")
            return novo_id
    except sqlite3.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir em '{tabela}': {e} - {contexto}")
        raise ValueError(f"Erro de integridade: {e}")
    except Exception as e:
        logger.error(f"Erro ao inserir em '{tabela}': {e} - {contexto}")
        raise RuntimeError(f"Erro no banco de dados: {e}")

def crud_update(tabela, dados_dict, condicao, valores_condicao, contexto=""):
    """
    Helper para UPDATE com logging automático.
    """
    set_clause = ', '.join([f"{col} = ?" for col in dados_dict.keys()])
    valores = tuple(dados_dict.values()) + valores_condicao
    
    query = f"UPDATE {tabela} SET {set_clause} WHERE {condicao}"
    
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(query, valores)
            conn.commit()
            linhas_afetadas = c.rowcount
            logger.info(f"UPDATE em '{tabela}' ({linhas_afetadas} linha(s)) - {contexto}")
            return linhas_afetadas
    except Exception as e:
        logger.error(f"Erro ao atualizar '{tabela}': {e} - {contexto}")
        raise RuntimeError(f"Erro no banco de dados: {e}")

def crud_delete(tabela, condicao, valores_condicao, contexto=""):
    """
    Helper para DELETE com logging automático.
    """
    query = f"DELETE FROM {tabela} WHERE {condicao}"
    
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(query, valores_condicao)
            conn.commit()
            linhas_deletadas = c.rowcount
            logger.info(f"DELETE em '{tabela}' ({linhas_deletadas} linha(s)) - {contexto}")
            return linhas_deletadas
    except Exception as e:
        logger.error(f"Erro ao deletar de '{tabela}': {e} - {contexto}")
        raise RuntimeError(f"Erro no banco de dados: {e}")

# --- FUNÇÕES ESPECÍFICAS EXISTENTES ---

def cpf_existe(cpf):
    """Verifica se CPF já está cadastrado."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM clientes WHERE cpf_cnpj = ?", (cpf,))
        return c.fetchone() is not None

def ver_inadimplencia(nome):
    """Verifica inadimplência de forma segura (sem SQL Injection)."""
    try:
        with get_connection() as conn:
            hoje = datetime.now().strftime("%Y-%m-%d")
            query = "SELECT * FROM financeiro WHERE descricao LIKE ? AND status_pagamento = 'Pendente' AND vencimento < ? AND tipo = 'Entrada'"
            df = pd.read_sql_query(query, conn, params=(f'%{nome}%', hoje))
            return "INADIMPLENTE" if not df.empty else "Adimplente"
    except Exception as e:
        logger.error(f"Erro ao verificar inadimplência para {nome}: {e}")
        return "Erro ao verificar"

def get_historico(id_processo):
    """Busca histórico de andamentos de um processo."""
    try:
        with get_connection() as conn:
            return pd.read_sql("SELECT data, descricao, responsavel FROM andamentos WHERE id_processo=? ORDER BY data DESC", conn, params=(id_processo,))
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do processo {id_processo}: {e}")
        return pd.DataFrame(columns=['data', 'descricao', 'responsavel'])

def kpis():
    """Calcula KPIs financeiros e operacionais."""
    with get_connection() as conn:
        try:
            saldo = pd.read_sql("SELECT SUM(CASE WHEN tipo='Entrada' THEN valor ELSE -valor END) FROM financeiro WHERE status_pagamento='Pago'", conn).iloc[0, 0] or 0.0
            receber = pd.read_sql("SELECT SUM(valor) FROM financeiro WHERE tipo='Entrada' AND status_pagamento='Pendente'", conn).iloc[0, 0] or 0.0
            num_clientes = pd.read_sql("SELECT COUNT(*) FROM clientes WHERE status_cliente='ATIVO'", conn).iloc[0, 0]
            num_processos = pd.read_sql("SELECT COUNT(*) FROM processos WHERE status='Ativo'", conn).iloc[0, 0]
        except Exception as e:
            logger.error(f"Erro ao calcular KPIs: {e}")
            return 0.0, 0.0, 0, 0
        
    return saldo, receber, num_clientes, num_processos

# --- NOVAS FUNÇÕES PARA MÓDULOS APRIMORADOS ---

def inicializar_tabelas_v2():
    """
    Cria/atualiza tabelas para as novas funcionalidades.
    Executa de forma segura, criando apenas se não existir.
    """
    with get_connection() as conn:
        c = conn.cursor()
        
        # Tabela de Agenda (prazos, audiências, tarefas)
        c.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT CHECK(tipo IN ('prazo', 'audiencia', 'tarefa')),
                titulo TEXT NOT NULL,
                descricao TEXT,
                data_evento TEXT,
                responsavel TEXT,
                id_processo INTEGER,
                status TEXT DEFAULT 'pendente',
                google_calendar_id TEXT,
                cor TEXT,
                prioridade TEXT CHECK(prioridade IN ('baixa', 'media', 'alta', 'urgente')),
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_processo) REFERENCES processos(id)
            )
        ''')
        
        # Tabela de Documentos do Processo
        c.execute('''
            CREATE TABLE IF NOT EXISTS documentos_processo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_processo INTEGER NOT NULL,
                tipo_documento TEXT CHECK(tipo_documento IN ('peticao_inicial', 'procuracao', 'sentenca', 'acordao', 'outro')),
                nome_documento TEXT,
                link_drive TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_processo) REFERENCES processos(id)
            )
        ''')
        
        # Tabela de Parcelamentos
        c.execute('''
            CREATE TABLE IF NOT EXISTS parcelamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lancamento_financeiro INTEGER NOT NULL,
                numero_parcela INTEGER,
                total_parcelas INTEGER,
                valor_parcela REAL,
                vencimento TEXT,
                status_parcela TEXT DEFAULT 'pendente',
                pago_em TEXT,
                FOREIGN KEY (id_lancamento_financeiro) REFERENCES financeiro(id)
            )
        ''')
        
        # Tabela de Modelos de Proposta
        c.execute('''
            CREATE TABLE IF NOT EXISTS modelos_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_modelo TEXT UNIQUE NOT NULL,
                area_atuacao TEXT,
                descricao_padrao TEXT,
                valor_sugerido REAL,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de Usuários
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabela de Configurações (Chave-Valor)
        c.execute('''
            CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')
        
        # Criar usuário admin padrão se não existir
        c.execute("SELECT count(*) FROM usuarios")
        if c.fetchone()[0] == 0:
            senha_admin = hashlib.sha256("admin".encode()).hexdigest()
            c.execute("INSERT INTO usuarios (username, password_hash, nome, role, ativo) VALUES (?, ?, ?, ?, ?)",
                      ('admin', senha_admin, 'Administrador', 'admin', 1))
            logger.info("Usuário admin padrão criado.")
        
        conn.commit()
        logger.info("Tabelas v2 inicializadas com sucesso")

def get_config(chave, padrao=None):
    """Busca valor de configuração."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT valor FROM config WHERE chave=?", (chave,))
            res = c.fetchone()
            return res[0] if res else padrao
    except:
        return padrao

def set_config(chave, valor):
    """Define valor de configuração."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, str(valor)))
        conn.commit()

def get_usuario_by_username(username):
    """Busca usuário pelo username de forma segura."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            # Converter para dict/Series compatível com o resto do app
            cols = [description[0] for description in c.description]
            return pd.Series(dict(zip(cols, row)))
        return None

def get_agenda_eventos(filtro_tipo=None, filtro_responsavel=None, filtro_status=None):
    """
    Busca eventos da agenda com filtros opcionais.
    """
    with get_connection() as conn:
        query = "SELECT * FROM agenda WHERE 1=1"
        params = []
        
        if filtro_tipo:
            query += " AND tipo = ?"
            params.append(filtro_tipo)
        if filtro_responsavel:
            query += " AND responsavel = ?"
            params.append(filtro_responsavel)
        if filtro_status:
            query += " AND status = ?"
            params.append(filtro_status)
        
        query += " ORDER BY data_evento ASC"
        
        return pd.read_sql_query(query, conn, params=params)

def get_agenda_por_processo(id_processo):
    """Busca todos os eventos de agenda vinculados a um processo."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM agenda WHERE id_processo = ? ORDER BY data_evento ASC",
            conn,
            params=(id_processo,)
        )

# --- FUNÇÕES PARA PROCESSOS ---

def get_documentos_processo(id_processo):
    """Busca todos os documentos vinculados a um processo."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM documentos_processo WHERE id_processo = ? ORDER BY criado_em DESC",
            conn,
            params=(id_processo,)
        )

def get_vinculos_financeiros(id_processo):
    """Busca todos os lançamentos financeiros vinculados a um processo."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM financeiro WHERE id_processo = ? ORDER BY vencimento DESC",
            conn,
            params=(id_processo,)
        )

def get_parcelamentos(id_lancamento):
    """Busca todas as parcelas de um lançamento financeiro."""
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM parcelamentos WHERE id_lancamento_financeiro = ? ORDER BY numero_parcela ASC",
            conn,
            params=(id_lancamento,)
        )

# --- FUNÇÕES PARA RELATÓRIOS ---

def relatorio_inadimplencia():
    """Gera relatório de clientes inadimplentes."""
    with get_connection() as conn:
        hoje = datetime.now().strftime("%Y-%m-%d")
        query = """
            SELECT 
                f.descricao,
                f.valor,
                f.vencimento,
                julianday(?) - julianday(f.vencimento) as dias_atraso
            FROM financeiro f
            WHERE f.tipo = 'Entrada'
            AND f.status_pagamento = 'Pendente'
            AND f.vencimento < ?
            ORDER BY f.vencimento ASC
        """
        return pd.read_sql_query(query, conn, params=(hoje, hoje))

def get_dre_data(data_inicio, data_fim):
    """
    Busca dados financeiros para geração do DRE (Demonstrativo de Resultado).
    """
    try:
        with get_connection() as conn:
            query = """
                SELECT 
                    tipo,
                    categoria,
                    SUM(valor) as total
                FROM financeiro
                WHERE status_pagamento = 'Pago'
                AND data BETWEEN ? AND ?
                GROUP BY tipo, categoria
                ORDER BY tipo, total DESC
            """
            return pd.read_sql_query(query, conn, params=(str(data_inicio), str(data_fim)))
    except Exception as e:
        logger.error(f"Erro ao buscar dados DRE: {e}")
        return pd.DataFrame(columns=['tipo', 'categoria', 'total'])

def get_rentabilidade_clientes(data_inicio, data_fim):
    """
    Calcula a rentabilidade por cliente no período especificado.
    """
    try:
        with get_connection() as conn:
            query = """
                SELECT 
                    c.nome as cliente,
                    COALESCE(SUM(CASE WHEN f.tipo = 'Entrada' AND f.status_pagamento = 'Pago' THEN f.valor ELSE 0 END), 0) as receita,
                    COALESCE(SUM(CASE WHEN f.tipo = 'Saída' AND f.status_pagamento = 'Pago' THEN f.valor ELSE 0 END), 0) as despesa,
                    (COALESCE(SUM(CASE WHEN f.tipo = 'Entrada' AND f.status_pagamento = 'Pago' THEN f.valor ELSE 0 END), 0) - 
                     COALESCE(SUM(CASE WHEN f.tipo = 'Saída' AND f.status_pagamento = 'Pago' THEN f.valor ELSE 0 END), 0)) as lucro
                FROM clientes c
                LEFT JOIN financeiro f ON c.id = f.id_cliente
                WHERE f.data BETWEEN ? AND ?
                GROUP BY c.id, c.nome
                HAVING receita > 0
            """
            df = pd.read_sql_query(query, conn, params=(str(data_inicio), str(data_fim)))
            
            # Calcular margem percentual
            if not df.empty:
                df['margem'] = (df['lucro'] / df['receita'] * 100).round(1)
                df = df.sort_values('lucro', ascending=False)
            
            return df
    except Exception as e:
        logger.error(f"Erro ao calcular rentabilidade de clientes: {e}")
        return pd.DataFrame(columns=['cliente', 'receita', 'despesa', 'lucro', 'margem'])

def get_modelos_proposta():
    """Busca todos os modelos de proposta cadastrados."""
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM modelos_proposta ORDER BY nome_modelo ASC", conn)

def gerar_proposta_texto(id_modelo, dados_cliente):
    """
    Gera o texto da proposta substituindo placeholders pelos dados do cliente.
    """
    with get_connection() as conn:
        modelo = conn.execute("SELECT * FROM modelos_proposta WHERE id = ?", (id_modelo,)).fetchone()
        
        if not modelo:
            return "Erro: Modelo não encontrado."
            
        texto = modelo['descricao_padrao']
        
        # Substituições
        # Usar .get() para evitar erros se a chave não existir
        texto = texto.replace("{nome}", str(dados_cliente.get('nome', '')))
        texto = texto.replace("{cpf}", str(dados_cliente.get('cpf_cnpj', '')))
        texto = texto.replace("{email}", str(dados_cliente.get('email', '')))
        texto = texto.replace("{endereco}", str(dados_cliente.get('endereco', '')))
        
        # Formatar valor se existir na proposta do cliente, senão usar do modelo
        valor = dados_cliente.get('proposta_valor')
        if not valor: valor = modelo['valor_sugerido']
        texto = texto.replace("{valor}", f"R$ {valor:,.2f}")
        
        return texto