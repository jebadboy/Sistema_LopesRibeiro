"""
Rate Limiter para proteção contra brute force e abuso de API.

Implementa rate limiting baseado em IP e username, com persistência
em banco de dados para funcionar entre sessões/deploys.

Features:
- Limite de 5 tentativas em 15 minutos
- Bloqueio por IP e username (o que for mais restritivo)
- Mensagens amigáveis com tempo de reset
- Logging de auditoria completo
- Limpeza automática de dados antigos

Uso:
    from rate_limiter import get_rate_limiter
    
    limiter = get_rate_limiter()
    check = limiter.check_login_attempts(ip_address, username)
    
    if not check['allowed']:
        st.error(check['message'])
    else:
        # Prosseguir com login
        ...
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

# Banco de dados separado para rate limiting (mais seguro e performático)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RATE_LIMIT_DB = os.path.join(BASE_DIR, 'rate_limit_events.db')

def _get_connection():
    """Cria conexão com banco de rate limiting."""
    conn = sqlite3.connect(RATE_LIMIT_DB)
    conn.row_factory = sqlite3.Row
    return conn

class RateLimiter:
    """
    Rate limiter baseado em IP e username com persistência em banco.
    
    Configuração:
    - MAX_ATTEMPTS = 5 tentativas
    - WINDOW_MINUTES = 15 minutos
    - Usa tabela rate_limit_events
    """
    
    MAX_ATTEMPTS = 5
    WINDOW_MINUTES = 15
    
    def __init__(self):
        """Inicializa rate limiter e cria tabela se necessário."""
        self._init_table()
    
    def _init_table(self):
        """Cria tabela de rate limiting se não existir."""
        conn = _get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    username TEXT,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Índices para performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_ip_time 
                ON rate_limit_events(ip_address, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_user_time 
                ON rate_limit_events(username, timestamp)
            """)
            
            conn.commit()
            logger.info("Tabela rate_limit_events inicializada")
        except Exception as e:
            logger.error(f"Erro ao criar tabela rate_limit_events: {e}")
        finally:
            conn.close()
    
    def check_login_attempts(
        self, 
        ip_address: str, 
        username: Optional[str] = None
    ) -> Dict:
        """
        Verifica se IP ou username excedeu limite de tentativas.
        
        Args:
            ip_address: Endereço IP do cliente
            username: Nome de usuário (opcional)
        
        Returns:
            {
                'allowed': bool,        # Se pode prosseguir
                'remaining': int,       # Tentativas restantes
                'reset_at': datetime,   # Quando bloqueio expira (se bloqueado)
                'message': str          # Mensagem amigável
            }
        """
        conn = _get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff = datetime.now() - timedelta(minutes=self.WINDOW_MINUTES)
            
            # Contar tentativas falhadas por IP nos últimos 15 min
            cursor.execute("""
                SELECT COUNT(*) FROM rate_limit_events
                WHERE ip_address = ? 
                AND event_type = 'login_attempt'
                AND timestamp > ?
                AND success = 0
            """, (ip_address, cutoff.isoformat()))
            
            ip_attempts = cursor.fetchone()[0]
            
            # Se username fornecido, contar também
            user_attempts = 0
            if username:
                cursor.execute("""
                    SELECT COUNT(*) FROM rate_limit_events
                    WHERE username = ? 
                    AND event_type = 'login_attempt'
                    AND timestamp > ?
                    AND success = 0
                """, (username, cutoff.isoformat()))
                
                user_attempts = cursor.fetchone()[0]
            
            # Usar o maior (mais restritivo)
            total_attempts = max(ip_attempts, user_attempts)
            
            if total_attempts >= self.MAX_ATTEMPTS:
                # Buscar timestamp da primeira tentativa para calcular reset
                cursor.execute("""
                    SELECT timestamp FROM rate_limit_events
                    WHERE (ip_address = ? OR username = ?)
                    AND event_type = 'login_attempt'
                    AND timestamp > ?
                    AND success = 0
                    ORDER BY timestamp ASC
                    LIMIT 1
                """, (ip_address, username or '', cutoff.isoformat()))
                
                first_attempt = cursor.fetchone()
                if first_attempt:
                    first_time = datetime.fromisoformat(first_attempt[0])
                    reset_at = first_time + timedelta(minutes=self.WINDOW_MINUTES)
                else:
                    reset_at = datetime.now() + timedelta(minutes=self.WINDOW_MINUTES)
                
                minutes_left = max(1, int((reset_at - datetime.now()).total_seconds() / 60))
                
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_at': reset_at,
                    'message': f'🚫 Muitas tentativas. Aguarde {minutes_left} minuto(s).'
                }
            
            remaining = self.MAX_ATTEMPTS - total_attempts
            
            return {
                'allowed': True,
                'remaining': remaining,
                'reset_at': None,
                'message': f'⚠️ {remaining} tentativa(s) restante(s)' if remaining <= 2 else ''
            }
        
        finally:
            conn.close()
    
    def record_login_attempt(
        self, 
        ip_address: str, 
        username: str, 
        success: bool
    ):
        """
        Registra tentativa de login.
        
        Args:
            ip_address: IP do cliente
            username: Username tentado
            success: Se login foi bem-sucedido
        """
        try:
            conn = _get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO rate_limit_events (ip_address, username, event_type, success, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (ip_address, username, 'login_attempt', 1 if success else 0, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            status = 'sucesso' if success else 'falha'
            logger.info(f"Login {status}: {username} de {ip_address}")
        except Exception as e:
            logger.error(f"Erro ao registrar tentativa de login: {e}")
    
    def cleanup_old_events(self, days: int = 30) -> int:
        """
        Remove eventos antigos (chamado por cron job de manutenção).
        
        Args:
            days: Manter apenas últimos N dias
            
        Returns:
            Número de registros deletados
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            conn = _get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM rate_limit_events
                WHERE timestamp < ?
            """, (cutoff.isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Limpeza rate limiting: {deleted} eventos antigos removidos")
            return deleted
        except Exception as e:
            logger.error(f"Erro na limpeza de rate limiting: {e}")
            return 0
    
    def get_blocked_ips(self) -> list:
        """
        Retorna lista de IPs atualmente bloqueados.
        Útil para dashboard de segurança.
        
        Returns:
            Lista de dicts com {ip, attempts, reset_at}
        """
        conn = _get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff = datetime.now() - timedelta(minutes=self.WINDOW_MINUTES)
            
            cursor.execute("""
                SELECT 
                    ip_address,
                    COUNT(*) as attempts,
                    MIN(timestamp) as first_attempt
                FROM rate_limit_events
                WHERE timestamp > ?
                AND success = 0
                AND event_type = 'login_attempt'
                GROUP BY ip_address
                HAVING attempts >= ?
                ORDER BY attempts DESC
            """, (cutoff.isoformat(), self.MAX_ATTEMPTS))
            
            blocked = []
            for row in cursor.fetchall():
                first_time = datetime.fromisoformat(row[2])
                reset_at = first_time + timedelta(minutes=self.WINDOW_MINUTES)
                
                blocked.append({
                    'ip': row[0],
                    'attempts': row[1],
                    'reset_at': reset_at,
                    'minutes_left': max(0, int((reset_at - datetime.now()).total_seconds() / 60))
                })
            
            return blocked
        finally:
            conn.close()

# ========== INSTÂNCIA GLOBAL (SINGLETON) ==========

_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Retorna instância singleton do rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

# ========== UTILITÁRIOS ==========

def get_client_ip() -> str:
    """
    Obtém IP real do cliente (considerando proxies).
    
    Streamlit Cloud e outros proxies usam headers X-Forwarded-For
    para passar o IP original do cliente.
    
    Returns:
        Endereço IP do cliente ou 'unknown'
    """
    try:
        import streamlit.web.server.websocket_headers as wsh
        headers = wsh.get_websocket_headers()
        
        # X-Forwarded-For pode ter múltiplos IPs (proxy chain)
        # Formato: "client, proxy1, proxy2"
        # Pegar o primeiro (IP real do cliente)
        forwarded_for = headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Fallback para X-Real-IP
        real_ip = headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip
        
        # Se nada funcionar
        return 'unknown'
    except Exception as e:
        logger.warning(f"Erro ao obter IP: {e}")
        return 'unknown'
