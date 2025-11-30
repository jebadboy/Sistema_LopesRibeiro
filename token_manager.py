"""
Módulo para gerenciamento de tokens públicos de acesso a processos.
Permite que clientes acessem status de processos sem login através de link seguro.
"""

import sqlite3
import secrets
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
DB_NAME = 'dados_escritorio.db'

def inicializar_tabela_tokens():
    """
    Cria a tabela tokens_publicos se não existir.
    Deve ser chamada durante a inicialização do banco.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens_publicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                id_processo INTEGER NOT NULL,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_expiracao DATETIME,
                ativo BOOLEAN DEFAULT 1,
                acessos INTEGER DEFAULT 0,
                ultimo_acesso DATETIME,
                FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Tabela tokens_publicos inicializada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela tokens_publicos: {e}")
        return False


def gerar_token_publico(id_processo, dias_validade=30):
    """
    Gera um token público seguro para um processo.
    
    Args:
        id_processo: ID do processo no banco de dados
        dias_validade: Número de dias até expiração (padrão: 30)
    
    Returns:
        str: Token gerado ou None em caso de erro
    """
    try:
        # Gerar token criptograficamente seguro (32 bytes = ~43 caracteres)
        token = secrets.token_urlsafe(32)
        
        # Calcular data de expiração
        data_expiracao = datetime.now() + timedelta(days=dias_validade)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Inserir token no banco
        cursor.execute('''
            INSERT INTO tokens_publicos 
            (token, id_processo, data_expiracao, ativo)
            VALUES (?, ?, ?, 1)
        ''', (token, id_processo, data_expiracao.isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Token gerado para processo ID {id_processo}, validade: {dias_validade} dias")
        return token
        
    except Exception as e:
        logger.error(f"Erro ao gerar token para processo {id_processo}: {e}")
        return None


def validar_token_publico(token):
    """
    Valida token e retorna ID do processo se válido.
    Registra o acesso para auditoria.
    
    Args:
        token: Token a ser validado
    
    Returns:
        int: ID do processo se token válido, None caso contrário
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Buscar token
        cursor.execute('''
            SELECT id_processo, data_expiracao, ativo
            FROM tokens_publicos
            WHERE token = ?
        ''', (token,))
        
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            logger.warning(f"Token não encontrado: {token[:10]}...")
            return None
        
        id_processo, data_expiracao_str, ativo = resultado
        
        # Verificar se token está ativo
        if not ativo:
            conn.close()
            logger.warning(f"Token revogado: {token[:10]}...")
            return None
        
        # Verificar expiração
        data_expiracao = datetime.fromisoformat(data_expiracao_str)
        if datetime.now() > data_expiracao:
            conn.close()
            logger.warning(f"Token expirado: {token[:10]}...")
            return None
        
        # Registrar acesso
        cursor.execute('''
            UPDATE tokens_publicos 
            SET acessos = acessos + 1,
                ultimo_acesso = ?
            WHERE token = ?
        ''', (datetime.now().isoformat(), token))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Token validado com sucesso para processo ID {id_processo}")
        return id_processo
        
    except Exception as e:
        logger.error(f"Erro ao validar token: {e}")
        return None


def revogar_token_publico(token):
    """
    Revoga (desativa) um token.
    
    Args:
        token: Token a ser revogado
    
    Returns:
        bool: True se revogado com sucesso, False caso contrário
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tokens_publicos 
            SET ativo = 0
            WHERE token = ?
        ''', (token,))
        
        linhas_afetadas = cursor.rowcount
        conn.commit()
        conn.close()
        
        if linhas_afetadas > 0:
            logger.info(f"Token revogado: {token[:10]}...")
            return True
        else:
            logger.warning(f"Token não encontrado para revogação: {token[:10]}...")
            return False
        
    except Exception as e:
        logger.error(f"Erro ao revogar token: {e}")
        return False


def listar_tokens_processo(id_processo):
    """
    Lista todos os tokens ativos de um processo.
    
    Args:
        id_processo: ID do processo
    
    Returns:
        list: Lista de dicionários com informações dos tokens
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                token,
                data_criacao,
                data_expiracao,
                ativo,
                acessos,
                ultimo_acesso
            FROM tokens_publicos
            WHERE id_processo = ?
            ORDER BY data_criacao DESC
        ''', (id_processo,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tokens = []
        for row in rows:
            tokens.append({
                'id': row['id'],
                'token': row['token'],
                'data_criacao': row['data_criacao'],
                'data_expiracao': row['data_expiracao'],
                'ativo': bool(row['ativo']),
                'acessos': row['acessos'],
                'ultimo_acesso': row['ultimo_acesso']
            })
        
        return tokens
        
    except Exception as e:
        logger.error(f"Erro ao listar tokens do processo {id_processo}: {e}")
        return []


def get_processo_por_token(token):
    """
    Busca informações completas do processo associado ao token.
    Inclui validação do token.
    
    Args:
        token: Token de acesso
    
    Returns:
        dict: Dados do processo ou None se token inválido
    """
    id_processo = validar_token_publico(token)
    
    if not id_processo:
        return None
    
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar processo
        cursor.execute('SELECT * FROM processos WHERE id = ?', (id_processo,))
        processo_row = cursor.fetchone()
        
        if not processo_row:
            conn.close()
            return None
        
        # Converter para dicionário
        processo = dict(processo_row)
        
        # Buscar andamentos
        cursor.execute('''
            SELECT * FROM andamentos 
            WHERE id_processo = ? 
            ORDER BY data DESC 
            LIMIT 10
        ''', (id_processo,))
        
        andamentos_rows = cursor.fetchall()
        processo['andamentos'] = [dict(row) for row in andamentos_rows]
        
        # Buscar cliente (se houver id_cliente no processo)
        if 'id_cliente' in processo and processo['id_cliente']:
            cursor.execute('SELECT nome, email, telefone FROM clientes WHERE id = ?', 
                         (processo['id_cliente'],))
            cliente_row = cursor.fetchone()
            if cliente_row:
                processo['cliente'] = dict(cliente_row)
        
        conn.close()
        return processo
        
    except Exception as e:
        logger.error(f"Erro ao buscar processo por token: {e}")
        return None
