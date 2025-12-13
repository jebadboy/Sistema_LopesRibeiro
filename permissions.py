"""
Sistema de Permissões e Controle de Acesso

Implementa validação de permissões baseada em roles (papéis) dos usuários,
garantindo que apenas usuários autorizados possam executar ações sensíveis.

Roles disponíveis:
- admin: Acesso total ao sistema
- advogado: Acesso a processos, clientes, financeiro
- secretaria: Acesso limitado (visualização principalmente)

Conformidade:
- LGPD Art. 46: Controladores devem adotar medidas de segurança
- ISO 27001: Controle de acesso baseado em papéis

Uso:
    from permissions import require_roles, can_delete_processo
    
    @require_roles(['admin', 'advogado'])
    def excluir_processo(pid):
        # Apenas admin e advogados podem executar
        ...
    
    if can_delete_processo(st.session_state.role):
        st.button("Excluir")
"""

import streamlit as st
from functools import wraps
from typing import List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class PermissionDenied(Exception):
    """Exceção levantada quando usuário não tem permissão para uma ação."""
    pass

# ========== DECORATORS ==========

def require_roles(allowed_roles: List[str]):
    """
    Decorator para exigir roles específicos em uma função.
    
    Args:
        allowed_roles: Lista de roles permitidos (ex: ['admin', 'advogado'])
        
    Returns:
        Função decorada que verifica permissões
        
    Raises:
        PermissionDenied: Se usuário não tem permissão
        
    Exemplo:
        @require_roles(['admin'])
        def deletar_usuario(user_id):
            # Apenas admin pode executar
            db.delete_user(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = st.session_state.get('role')
            username = st.session_state.get('username', 'unknown')
            
            if user_role not in allowed_roles:
                error_msg = f"Acesso negado. Apenas {', '.join(allowed_roles)} podem executar esta ação."
                
                # Log de auditoria
                import database as db
                try:
                    db.audit('permission_denied', {
                        'user': username,
                        'role': user_role,
                        'function': func.__name__,
                        'required_roles': allowed_roles
                    })
                except Exception as e:
                    logger.error(f"Erro ao registrar negação de permissão: {e}")
                
                raise PermissionDenied(error_msg)
            
            # Usuário tem permissão, executar função
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_permission(permission_check_func: Callable[[], bool], error_message: str = None):
    """
    Decorator genérico para validações customizadas de permissão.
    
    Args:
        permission_check_func: Função que retorna True se permitido
        error_message: Mensagem de erro customizada
        
    Exemplo:
        @require_permission(lambda: st.session_state.role == 'admin', "Apenas admin")
        def funcao_admin():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not permission_check_func():
                msg = error_message or "Permissão negada"
                raise PermissionDenied(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ========== FUNÇÕES DE VALIDAÇÃO ==========

def get_current_role() -> Optional[str]:
    """Retorna role do usuário atual."""
    return st.session_state.get('role')

def get_current_username() -> Optional[str]:
    """Retorna username do usuário atual."""
    return st.session_state.get('username')

def is_admin() -> bool:
    """Verifica se usuário atual é admin."""
    return get_current_role() == 'admin'

def is_advogado() -> bool:
    """Verifica se usuário atual é advogado."""
    return get_current_role() == 'advogado'

def is_secretaria() -> bool:
    """Verifica se usuário atual é secretária."""
    return get_current_role() == 'secretaria'

# ========== PERMISSÕES ESPECÍFICAS POR MÓDULO ==========

# --- PROCESSOS ---

def can_create_processo(user_role: str = None) -> bool:
    """Verifica se pode criar processo."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado', 'secretaria']

def can_edit_processo(user_role: str = None, processo: dict = None) -> bool:
    """
    Verifica se pode editar processo.
    
    Regras:
    - Admin: Pode editar tudo
    - Advogado: Pode editar tudo
    - Secretaria: Pode editar apenas campos limitados (observações, anexos)
    """
    role = user_role or get_current_role()
    
    if role in ['admin', 'advogado']:
        return True
    
    if role == 'secretaria':
        # Secretaria pode fazer edições limitadas
        return True  # Implementar validação de campos específicos se necessário
    
    return False

def can_delete_processo(user_role: str = None) -> bool:
    """
    Verifica se pode excluir processo.
    
    Regras:
    - Admin: Sim
    - Advogado: Sim
    - Secretaria: NÃO
    """
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

def can_view_processo_estrategia(user_role: str = None) -> bool:
    """Verifica se pode ver análise estratégica de IA."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

# --- FINANCEIRO ---

def can_view_financeiro(user_role: str = None) -> bool:
    """
    Verifica se pode ver módulo financeiro.
    
    Regras:
    - Admin: Sim
    - Advogado: Sim
    - Secretaria: NÃO
    """
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

def can_edit_financeiro(user_role: str = None) -> bool:
    """Verifica se pode editar lançamentos financeiros."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

def can_delete_financeiro(user_role: str = None) -> bool:
    """Verifica se pode excluir lançamentos financeiros."""
    role = user_role or get_current_role()
    return role == 'admin'  # Apenas admin

def can_view_relatorios_financeiros(user_role: str = None) -> bool:
    """Verifica se pode ver relatórios financeiros (DRE, etc)."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

# --- CLIENTES ---

def can_create_cliente(user_role: str = None) -> bool:
    """Verifica se pode criar cliente."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado', 'secretaria']

def can_edit_cliente(user_role: str = None) -> bool:
    """Verifica se pode editar cliente."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado', 'secretaria']

def can_delete_cliente(user_role: str = None) -> bool:
    """Verifica se pode excluir cliente."""
    role = user_role or get_current_role()
    return role in ['admin', 'advogado']

def can_view_cliente_sensitive_data(user_role: str = None) -> bool:
    """
    Verifica se pode ver dados sensíveis do cliente (CPF, RG, etc).
    
    Todos podem ver, mas logs de acesso são registrados (LGPD).
    """
    return True  # Todos podem, mas com auditoria

# --- ADMINISTRAÇÃO ---

def can_manage_users(user_role: str = None) -> bool:
    """Verifica se pode gerenciar usuários."""
    role = user_role or get_current_role()
    return role == 'admin'

def can_view_audit_logs(user_role: str = None) -> bool:
    """Verifica se pode ver logs de auditoria."""
    role = user_role or get_current_role()
    return role == 'admin'

def can_manage_system_config(user_role: str = None) -> bool:
    """Verifica se pode alterar configurações do sistema."""
    role = user_role or get_current_role()
    return role == 'admin'

def can_backup_database(user_role: str = None) -> bool:
    """Verifica se pode fazer backup do banco."""
    role = user_role or get_current_role()
    return role == 'admin'

# ========== HELPERS PARA UI ==========

def show_permission_warning(required_roles: List[str]):
    """
    Exibe aviso de permissão negada na UI.
    
    Args:
        required_roles: Lista de roles necessários
    """
    st.warning(f"🔒 Permissão insuficiente. Apenas {', '.join(required_roles)} podem realizar esta ação.")

def render_with_permission(
    permission_func: Callable[[], bool],
    component_func: Callable,
    fallback_message: str = None
):
    """
    Renderiza componente apenas se usuário tem permissão.
    
    Args:
        permission_func: Função que retorna True se permitido
        component_func: Função que renderiza o componente
        fallback_message: Mensagem a exibir se sem permissão
        
    Exemplo:
        render_with_permission(
            can_delete_processo,
            lambda: st.button("Excluir"),
            "Apenas advogados podem excluir"
        )
    """
    if permission_func():
        component_func()
    elif fallback_message:
        st.caption(f"🔒 {fallback_message}")

# ========== MATRIZ DE PERMISSÕES ==========

PERMISSION_MATRIX = {
    'processos': {
        'create': ['admin', 'advogado', 'secretaria'],
        'edit': ['admin', 'advogado', 'secretaria'],
        'delete': ['admin', 'advogado'],
        'view_estrategia': ['admin', 'advogado'],
    },
    'clientes': {
        'create': ['admin', 'advogado', 'secretaria'],
        'edit': ['admin', 'advogado', 'secretaria'],
        'delete': ['admin', 'advogado'],
        'view': ['admin', 'advogado', 'secretaria'],
    },
    'financeiro': {
        'view': ['admin', 'advogado'],
        'create': ['admin', 'advogado'],
        'edit': ['admin', 'advogado'],
        'delete': ['admin'],
        'view_relatorios': ['admin', 'advogado'],
    },
    'admin': {
        'manage_users': ['admin'],
        'view_logs': ['admin'],
        'system_config': ['admin'],
        'backup': ['admin'],
    }
}

def has_permission(module: str, action: str, user_role: str = None) -> bool:
    """
    Verifica permissão baseada na matriz de permissões.
    
    Args:
        module: Módulo (ex: 'processos', 'financeiro')
        action: Ação (ex: 'delete', 'edit')
        user_role: Role do usuário (opcional, usa session_state)
        
    Returns:
        True se usuário tem permissão
        
    Exemplo:
        if has_permission('processos', 'delete'):
            # Pode excluir processo
    """
    role = user_role or get_current_role()
    
    if not role:
        return False
    
    if module not in PERMISSION_MATRIX:
        logger.warning(f"Módulo '{module}' não encontrado na matriz de permissões")
        return False
    
    if action not in PERMISSION_MATRIX[module]:
        logger.warning(f"Ação '{action}' não encontrada no módulo '{module}'")
        return False
    
    return role in PERMISSION_MATRIX[module][action]

# ========== LOGS DE AUDITORIA ==========

def log_permission_check(module: str, action: str, granted: bool):
    """
    Registra verificação de permissão nos logs de auditoria.
    
    Args:
        module: Módulo acessado
        action: Ação tentada
        granted: Se foi permitido ou negado
    """
    import database as db
    
    try:
        db.audit('permission_check', {
            'user': get_current_username(),
            'role': get_current_role(),
            'module': module,
            'action': action,
            'granted': granted
        })
    except Exception as e:
        logger.error(f"Erro ao registrar log de permissão: {e}")
