"""
Módulo para gerenciamento de tokens públicos de acesso a processos.
Permite que clientes acessem status de processos sem login através de link seguro.
Refatorado para usar a infraestrutura do database.py
"""

import secrets
from datetime import datetime, timedelta
import logging
import database as db
import pandas as pd

logger = logging.getLogger(__name__)

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
        
        # Inserir token no banco usando db.encapsulado
        dados = {
            'token': token,
            'id_processo': id_processo,
            'data_expiracao': data_expiracao.isoformat(),
            'ativo': 1
        }
        
        # Como crud_insert retorna ID, usamos sql_run se quisermos garantir apenas a inserção
        # Mas podemos usar crud_insert se funcionar bem para a tabela
        # Vou usar sql_run direto para garantir controle sobre a query
        
        query = """
            INSERT INTO tokens_publicos (token, id_processo, data_expiracao, ativo)
            VALUES (?, ?, ?, 1)
        """
        success = db.sql_run(query, (token, id_processo, data_expiracao.isoformat()))
        
        if success:
            logger.info(f"Token gerado para processo ID {id_processo}, validade: {dias_validade} dias")
            return token
        else:
            logger.error("Falha ao inserir token no banco")
            return None
        
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
        # Buscar token
        query = "SELECT id_processo, data_expiracao, ativo FROM tokens_publicos WHERE token = ?"
        df = db.sql_get_query(query, (token,))
        
        if df.empty:
            logger.warning(f"Token não encontrado: {token[:10]}...")
            return None
        
        row = df.iloc[0]
        id_processo = int(row['id_processo'])
        data_exp_str = row['data_expiracao']
        ativo = bool(row['ativo'])
        
        # Verificar se token está ativo
        if not ativo:
            logger.warning(f"Token revogado: {token[:10]}...")
            return None
        
        # Verificar expiração
        try:
            # Compatibilidade com ISO e strings simples
            if 'T' in data_exp_str:
                data_expiracao = datetime.fromisoformat(data_exp_str)
            else:
                # Tentar formato simples se necessario, ou assumir string comum
                data_expiracao = datetime.fromisoformat(data_exp_str)
                
            if datetime.now() > data_expiracao:
                logger.warning(f"Token expirado: {token[:10]}...")
                return None
        except:
             # Se der erro de parse, invalida por segurança
             logger.error(f"Erro ao parsear data expiração: {data_exp_str}")
             return None
        
        # Registrar acesso
        update_query = """
            UPDATE tokens_publicos 
            SET acessos = acessos + 1, ultimo_acesso = ?
            WHERE token = ?
        """
        db.sql_run(update_query, (datetime.now().isoformat(), token))
        
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
        query = "UPDATE tokens_publicos SET ativo = 0 WHERE token = ?"
        return db.sql_run(query, (token,))
    except Exception as e:
        logger.error(f"Erro ao revogar token: {e}")
        return False


def excluir_token_publico(token):
    """
    Exclui um token permanentemente do banco de dados.
    
    Args:
        token: Token a ser excluído
    
    Returns:
        bool: True se excluído com sucesso, False caso contrário
    """
    try:
        query = "DELETE FROM tokens_publicos WHERE token = ?"
        return db.sql_run(query, (token,))
    except Exception as e:
        logger.error(f"Erro ao excluir token: {e}")
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
        query = """
            SELECT id, token, data_criacao, data_expiracao, ativo, acessos, ultimo_acesso
            FROM tokens_publicos
            WHERE id_processo = ?
            ORDER BY data_criacao DESC
        """
        df = db.sql_get_query(query, (id_processo,))
        
        if df.empty:
            return []
            
        return df.to_dict('records')
        
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
        # Buscar processo
        query_proc = "SELECT * FROM processos WHERE id = ?"
        df_proc = db.sql_get_query(query_proc, (id_processo,))
        
        if df_proc.empty:
            return None
            
        processo = df_proc.iloc[0].to_dict()
        
        # Buscar andamentos
        # Ajuste: Garantir limit 10
        query_and = """
            SELECT * FROM andamentos 
            WHERE id_processo = ? 
            ORDER BY data DESC 
            LIMIT 10
        """
        df_and = db.sql_get_query(query_and, (id_processo,))
        processo['andamentos'] = df_and.to_dict('records') if not df_and.empty else []
        
        # Buscar cliente (se houver id_cliente no processo)
        if 'id_cliente' in processo and processo['id_cliente']:
             # Verificar se não é Nan/None
             if pd.notna(processo['id_cliente']):
                try:
                    cid = int(processo['id_cliente'])
                    query_cli = "SELECT nome, email, telefone FROM clientes WHERE id = ?"
                    df_cli = db.sql_get_query(query_cli, (cid,))
                    if not df_cli.empty:
                         processo['cliente'] = df_cli.iloc[0].to_dict()
                except:
                    pass
        
        return processo
        
    except Exception as e:
        logger.error(f"Erro ao buscar processo por token: {e}")
        return None
