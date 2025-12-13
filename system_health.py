"""
Sistema de Monitoramento e Health Check - Sprint 3

Verifica status de serviços críticos e fornece dashboard de saúde do sistema.

Features:
- Verificação de conexão com banco de dados
- Verificação de tokens Google (Drive/Calendar)
- Verificação de espaço em disco
- Verificação de token DataJud
- Dashboard de status para Admin
- Histórico de verificações
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# ==================== DEFINIÇÃO DE SERVIÇOS ====================

SERVICOS = {
    'database': {
        'nome': 'Banco de Dados',
        'icone': '🗄️',
        'critico': True,
        'descricao': 'Conexão com SQLite/PostgreSQL'
    },
    'google_drive': {
        'nome': 'Google Drive',
        'icone': '📁',
        'critico': False,
        'descricao': 'Upload e backup de arquivos'
    },
    'google_calendar': {
        'nome': 'Google Calendar',
        'icone': '📅',
        'critico': False,
        'descricao': 'Sincronização de agenda'
    },
    'datajud': {
        'nome': 'DataJud (CNJ)',
        'icone': '⚖️',
        'critico': False,
        'descricao': 'Consulta de processos'
    },
    'disk_space': {
        'nome': 'Espaço em Disco',
        'icone': '💾',
        'critico': True,
        'descricao': 'Espaço disponível para operação'
    },
    'backup': {
        'nome': 'Backup Automático',
        'icone': '📦',
        'critico': False,
        'descricao': 'Status do último backup'
    }
}

# Status possíveis
STATUS_OK = 'ok'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'
STATUS_UNKNOWN = 'unknown'

# ==================== FUNÇÕES DE VERIFICAÇÃO ====================

def check_database() -> Dict:
    """Verifica conexão com banco de dados."""
    try:
        import database as db
        
        # Tentar uma query simples
        result = db.sql_get_query("SELECT 1 as test")
        
        if result is not None and not result.empty:
            # Contar registros principais
            clientes = db.sql_get_query("SELECT COUNT(*) as cnt FROM clientes")
            processos = db.sql_get_query("SELECT COUNT(*) as cnt FROM processos")
            
            return {
                'status': STATUS_OK,
                'message': 'Conexão OK',
                'details': {
                    'clientes': int(clientes.iloc[0]['cnt']) if not clientes.empty else 0,
                    'processos': int(processos.iloc[0]['cnt']) if not processos.empty else 0
                }
            }
        else:
            return {
                'status': STATUS_ERROR,
                'message': 'Sem resposta do banco',
                'details': None
            }
            
    except Exception as e:
        return {
            'status': STATUS_ERROR,
            'message': f'Erro: {str(e)[:50]}',
            'details': None
        }

def check_google_drive() -> Dict:
    """Verifica integração com Google Drive."""
    try:
        import google_drive as gd
        
        service = gd.autenticar()
        
        if service:
            # Tentar listar arquivos (operação básica)
            try:
                service.files().list(pageSize=1).execute()
                return {
                    'status': STATUS_OK,
                    'message': 'Autenticado e conectado',
                    'details': {'pasta_alvo': gd.PASTA_ALVO_ID[:10] + '...'}
                }
            except Exception as e:
                if '401' in str(e) or '403' in str(e):
                    return {
                        'status': STATUS_WARNING,
                        'message': 'Token pode estar expirado',
                        'details': {'error': str(e)[:50]}
                    }
                raise
        else:
            return {
                'status': STATUS_WARNING,
                'message': 'Credenciais não configuradas',
                'details': None
            }
            
    except ImportError:
        return {
            'status': STATUS_UNKNOWN,
            'message': 'Módulo não instalado',
            'details': None
        }
    except Exception as e:
        return {
            'status': STATUS_ERROR,
            'message': f'Erro: {str(e)[:50]}',
            'details': None
        }

def check_google_calendar() -> Dict:
    """Verifica integração com Google Calendar."""
    try:
        import google_calendar as gc
        
        service = gc.autenticar()
        
        if service:
            return {
                'status': STATUS_OK,
                'message': 'Autenticado',
                'details': None
            }
        else:
            return {
                'status': STATUS_WARNING,
                'message': 'Credenciais não configuradas',
                'details': None
            }
            
    except ImportError:
        return {
            'status': STATUS_UNKNOWN,
            'message': 'Módulo não instalado',
            'details': None
        }
    except Exception as e:
        error_msg = str(e)
        if '401' in error_msg or 'expired' in error_msg.lower():
            return {
                'status': STATUS_WARNING,
                'message': 'Token expirado - renovar',
                'details': None
            }
        return {
            'status': STATUS_ERROR,
            'message': f'Erro: {error_msg[:50]}',
            'details': None
        }

def check_datajud() -> Dict:
    """Verifica disponibilidade da API DataJud."""
    try:
        import database as db
        
        # Verificar se token está configurado
        token = db.get_config('datajud_token')
        
        if not token or len(token) < 10:
            # Usar chave pública padrão
            return {
                'status': STATUS_OK,
                'message': 'Usando chave pública CNJ',
                'details': {'tipo': 'publica'}
            }
        else:
            return {
                'status': STATUS_OK,
                'message': 'Token customizado configurado',
                'details': {'tipo': 'customizado'}
            }
            
    except Exception as e:
        return {
            'status': STATUS_WARNING,
            'message': f'Erro: {str(e)[:50]}',
            'details': None
        }

def check_disk_space() -> Dict:
    """Verifica espaço disponível em disco."""
    try:
        import shutil
        
        # Pegar diretório atual
        path = os.getcwd()
        usage = shutil.disk_usage(path)
        
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        used_percent = (usage.used / usage.total) * 100
        
        # Alerta se menos de 1GB livre ou mais de 90% usado
        if free_gb < 1 or used_percent > 90:
            status = STATUS_ERROR
            message = f'CRÍTICO: {free_gb:.1f}GB livre'
        elif free_gb < 5 or used_percent > 80:
            status = STATUS_WARNING
            message = f'Alerta: {free_gb:.1f}GB livre'
        else:
            status = STATUS_OK
            message = f'{free_gb:.1f}GB livre'
        
        return {
            'status': status,
            'message': message,
            'details': {
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'used_percent': round(used_percent, 1)
            }
        }
        
    except Exception as e:
        return {
            'status': STATUS_UNKNOWN,
            'message': f'Erro: {str(e)[:50]}',
            'details': None
        }

def check_backup() -> Dict:
    """Verifica status do último backup."""
    try:
        backup_dir = 'backups'
        
        if not os.path.exists(backup_dir):
            return {
                'status': STATUS_WARNING,
                'message': 'Nenhum backup encontrado',
                'details': None
            }
        
        # Buscar backups
        backups = sorted([
            f for f in os.listdir(backup_dir)
            if f.startswith('sistema_backup_') and f.endswith('.db.gz')
        ], reverse=True)
        
        if not backups:
            return {
                'status': STATUS_WARNING,
                'message': 'Nenhum backup encontrado',
                'details': {'count': 0}
            }
        
        ultimo = backups[0]
        ultimo_path = os.path.join(backup_dir, ultimo)
        ultimo_size = os.path.getsize(ultimo_path) / (1024 * 1024)
        
        # Extrair data do nome do arquivo
        try:
            date_str = ultimo.replace('sistema_backup_', '').replace('.db.gz', '')[:8]
            backup_date = datetime.strptime(date_str, '%Y%m%d')
            days_ago = (datetime.now() - backup_date).days
            
            if days_ago > 7:
                status = STATUS_ERROR
                message = f'Backup antigo ({days_ago} dias)'
            elif days_ago > 3:
                status = STATUS_WARNING
                message = f'Backup de {days_ago} dias'
            else:
                status = STATUS_OK
                message = f'Backup recente ({days_ago}d)'
                
        except:
            status = STATUS_OK
            message = f'Último: {ultimo[:20]}...'
            days_ago = None
        
        return {
            'status': status,
            'message': message,
            'details': {
                'ultimo': ultimo,
                'size_mb': round(ultimo_size, 2),
                'count': len(backups),
                'days_ago': days_ago
            }
        }
        
    except Exception as e:
        return {
            'status': STATUS_ERROR,
            'message': f'Erro: {str(e)[:50]}',
            'details': None
        }

# ==================== FUNÇÃO PRINCIPAL ====================

def health_check() -> Dict:
    """
    Executa verificação completa de saúde do sistema.
    
    Returns:
        Dict com status de cada serviço e resumo geral
    """
    results = {}
    timestamp = datetime.now().isoformat()
    
    # Executar todas as verificações
    checks = {
        'database': check_database,
        'google_drive': check_google_drive,
        'google_calendar': check_google_calendar,
        'datajud': check_datajud,
        'disk_space': check_disk_space,
        'backup': check_backup,
    }
    
    critical_ok = True
    warnings = 0
    errors = 0
    
    for service_id, check_func in checks.items():
        try:
            result = check_func()
            results[service_id] = {
                **SERVICOS[service_id],
                **result
            }
            
            # Contar problemas
            if result['status'] == STATUS_ERROR:
                errors += 1
                if SERVICOS[service_id]['critico']:
                    critical_ok = False
            elif result['status'] == STATUS_WARNING:
                warnings += 1
                
        except Exception as e:
            results[service_id] = {
                **SERVICOS[service_id],
                'status': STATUS_ERROR,
                'message': f'Falha na verificação: {str(e)[:30]}',
                'details': None
            }
            errors += 1
    
    # Calcular status geral
    if errors > 0 and not critical_ok:
        overall_status = STATUS_ERROR
        overall_message = 'Sistema com problemas críticos'
    elif errors > 0 or warnings > 0:
        overall_status = STATUS_WARNING
        overall_message = f'{errors} erro(s), {warnings} alerta(s)'
    else:
        overall_status = STATUS_OK
        overall_message = 'Todos os serviços operacionais'
    
    return {
        'timestamp': timestamp,
        'overall_status': overall_status,
        'overall_message': overall_message,
        'services': results,
        'summary': {
            'total': len(results),
            'ok': sum(1 for r in results.values() if r['status'] == STATUS_OK),
            'warnings': warnings,
            'errors': errors
        }
    }

def render_health_dashboard():
    """
    Renderiza dashboard de saúde no Streamlit.
    Chamar de modules/admin.py
    """
    import streamlit as st
    
    st.markdown("### 🏥 Saúde do Sistema")
    
    with st.spinner('Verificando serviços...'):
        health = health_check()
    
    # Status geral
    status_colors = {
        STATUS_OK: '🟢',
        STATUS_WARNING: '🟡',
        STATUS_ERROR: '🔴',
        STATUS_UNKNOWN: '⚪'
    }
    
    overall_icon = status_colors.get(health['overall_status'], '⚪')
    st.markdown(f"**Status Geral**: {overall_icon} {health['overall_message']}")
    st.caption(f"Última verificação: {health['timestamp'][:19]}")
    
    st.divider()
    
    # Grid de serviços
    cols = st.columns(3)
    
    for i, (service_id, service) in enumerate(health['services'].items()):
        col = cols[i % 3]
        
        with col:
            icon = service.get('icone', '❓')
            status_icon = status_colors.get(service['status'], '⚪')
            nome = service.get('nome', service_id)
            
            # Card do serviço
            st.markdown(f"""
            <div style="
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 12px; 
                margin-bottom: 10px;
                background: {'#f0fff0' if service['status'] == STATUS_OK else '#fffef0' if service['status'] == STATUS_WARNING else '#fff0f0'}
            ">
                <div style="font-size: 24px; text-align: center;">{icon} {status_icon}</div>
                <div style="font-weight: bold; text-align: center;">{nome}</div>
                <div style="font-size: 12px; text-align: center; color: #666;">{service['message']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Detalhes expandíveis
    with st.expander("📊 Detalhes Técnicos"):
        st.json(health)

# ==================== TESTE ====================

if __name__ == "__main__":
    print("=== Health Check ===")
    result = health_check()
    print(json.dumps(result, indent=2, default=str))
