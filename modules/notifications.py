"""
Módulo de Notificações In-App

Sistema de notificações internas para alertar usuários sobre:
- Prazos vencendo (hoje/amanhã)
- Pagamentos pendentes/vencidos
- Novos andamentos (DataJud/IA)
- Compromissos da agenda
"""

import streamlit as st
import database as db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Tipos de notificação
TIPOS_NOTIFICACAO = {
    "prazo": {"icone": "⚖️", "cor": "#dc3545", "nome": "Prazo"},
    "pagamento": {"icone": "💰", "cor": "#fd7e14", "nome": "Pagamento"},
    "andamento": {"icone": "📋", "cor": "#0d6efd", "nome": "Andamento"},
    "agenda": {"icone": "📅", "cor": "#198754", "nome": "Agenda"},
    "sistema": {"icone": "🔔", "cor": "#6c757d", "nome": "Sistema"},
}


def criar_tabela_notificacoes():
    """Cria tabela de notificações se não existir"""
    try:
        db.sql_run("""
            CREATE TABLE IF NOT EXISTS notificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                mensagem TEXT,
                link_acao TEXT,
                prioridade TEXT DEFAULT 'media',
                lida INTEGER DEFAULT 0,
                arquivada INTEGER DEFAULT 0,
                usuario_destino TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabela notificacoes verificada/criada")
    except Exception as e:
        logger.error(f"Erro ao criar tabela notificacoes: {e}")


def criar_notificacao(tipo: str, titulo: str, mensagem: str = "", 
                      link_acao: str = "", prioridade: str = "media",
                      usuario_destino: str = None):
    """
    Cria uma nova notificação no sistema.
    
    Args:
        tipo: prazo, pagamento, andamento, agenda, sistema
        titulo: Título curto da notificação
        mensagem: Descrição detalhada (opcional)
        link_acao: URL ou page param para navegar (opcional)
        prioridade: baixa, media, alta, urgente
        usuario_destino: Username específico ou None (todos)
    """
    try:
        criar_tabela_notificacoes()
        
        db.crud_insert("notificacoes", {
            "tipo": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "link_acao": link_acao,
            "prioridade": prioridade,
            "usuario_destino": usuario_destino,
            "criado_em": datetime.now().isoformat()
        }, f"Notificação criada: {titulo}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {e}")
        return False


def get_notificacoes_nao_lidas(usuario: str = None, limite: int = 20):
    """Retorna notificações não lidas do usuário"""
    try:
        criar_tabela_notificacoes()
        
        query = """
            SELECT * FROM notificacoes 
            WHERE lida = 0 AND arquivada = 0
            AND (usuario_destino IS NULL OR usuario_destino = ?)
            ORDER BY 
                CASE prioridade 
                    WHEN 'urgente' THEN 1 
                    WHEN 'alta' THEN 2 
                    WHEN 'media' THEN 3 
                    ELSE 4 
                END,
                criado_em DESC
            LIMIT ?
        """
        return db.sql_get_query(query, (usuario, limite))
    except Exception as e:
        logger.error(f"Erro ao buscar notificações: {e}")
        import pandas as pd
        return pd.DataFrame()


def marcar_como_lida(notificacao_id: int):
    """Marca uma notificação como lida"""
    try:
        db.sql_run("UPDATE notificacoes SET lida = 1 WHERE id = ?", (notificacao_id,))
        return True
    except:
        return False


def marcar_todas_lidas(usuario: str = None):
    """Marca todas notificações como lidas"""
    try:
        if usuario:
            db.sql_run("""
                UPDATE notificacoes SET lida = 1 
                WHERE (usuario_destino IS NULL OR usuario_destino = ?)
            """, (usuario,))
        else:
            db.sql_run("UPDATE notificacoes SET lida = 1")
        return True
    except:
        return False


def arquivar_notificacao(notificacao_id: int):
    """Arquiva uma notificação"""
    try:
        db.sql_run("UPDATE notificacoes SET arquivada = 1 WHERE id = ?", (notificacao_id,))
        return True
    except:
        return False


def contar_nao_lidas(usuario: str = None) -> int:
    """Conta notificações não lidas"""
    try:
        criar_tabela_notificacoes()
        
        result = db.sql_get_query("""
            SELECT COUNT(*) as total FROM notificacoes 
            WHERE lida = 0 AND arquivada = 0
            AND (usuario_destino IS NULL OR usuario_destino = ?)
        """, (usuario,))
        
        return result.iloc[0]['total'] if not result.empty else 0
    except:
        return 0


def gerar_notificacoes_automaticas():
    """
    Gera notificações automáticas baseadas em eventos do sistema.
    Deve ser chamada periodicamente (ex: ao carregar dashboard).
    """
    criar_tabela_notificacoes()
    
    hoje = datetime.now().date()
    amanha = hoje + timedelta(days=1)
    notificacoes_criadas = 0
    
    # --- 1. PRAZOS VENCENDO HOJE/AMANHÃ ---
    try:
        prazos = db.sql_get_query("""
            SELECT id, cliente_nome, acao, proximo_prazo 
            FROM processos 
            WHERE proximo_prazo IN (?, ?)
            AND status != 'Arquivado'
        """, (hoje.isoformat(), amanha.isoformat()))
        
        for _, prazo in prazos.iterrows():
            # Verificar se já existe notificação similar
            existente = db.sql_get_query("""
                SELECT id FROM notificacoes 
                WHERE tipo = 'prazo' 
                AND link_acao LIKE ? 
                AND DATE(criado_em) = ?
            """, (f"%id={prazo['id']}%", hoje.isoformat()))
            
            if existente.empty:
                eh_hoje = str(prazo['proximo_prazo']) == str(hoje)
                criar_notificacao(
                    tipo="prazo",
                    titulo=f"⚠️ Prazo {'HOJE' if eh_hoje else 'AMANHÃ'}: {prazo['cliente_nome']}",
                    mensagem=f"Processo: {prazo['acao']}",
                    link_acao=f"page=Processos&id={prazo['id']}",
                    prioridade="urgente" if eh_hoje else "alta"
                )
                notificacoes_criadas += 1
    except Exception as e:
        logger.debug(f"Erro ao verificar prazos: {e}")
    
    # --- 2. PAGAMENTOS VENCIDOS ---
    try:
        vencidos = db.sql_get_query("""
            SELECT id, descricao, cliente, valor, vencimento 
            FROM financeiro 
            WHERE tipo = 'Entrada' 
            AND status_pagamento = 'Pendente'
            AND vencimento < ?
            LIMIT 10
        """, (hoje.isoformat(),))
        
        for _, pag in vencidos.iterrows():
            existente = db.sql_get_query("""
                SELECT id FROM notificacoes 
                WHERE tipo = 'pagamento' 
                AND link_acao LIKE ? 
                AND DATE(criado_em) = ?
            """, (f"%id={pag['id']}%", hoje.isoformat()))
            
            if existente.empty:
                criar_notificacao(
                    tipo="pagamento",
                    titulo=f"💰 Pagamento vencido: {pag['cliente']}",
                    mensagem=f"{pag['descricao']} - R$ {pag['valor']:.2f}",
                    link_acao=f"page=Financeiro&id={pag['id']}",
                    prioridade="alta"
                )
                notificacoes_criadas += 1
    except Exception as e:
        logger.debug(f"Erro ao verificar pagamentos: {e}")
    
    # --- 3. AGENDA DE HOJE ---
    try:
        eventos = db.sql_get_query("""
            SELECT id, titulo, tipo_evento, hora_evento 
            FROM agenda 
            WHERE data_evento = ? 
            AND status = 'pendente'
        """, (hoje.isoformat(),))
        
        for _, evento in eventos.iterrows():
            existente = db.sql_get_query("""
                SELECT id FROM notificacoes 
                WHERE tipo = 'agenda' 
                AND link_acao LIKE ? 
                AND DATE(criado_em) = ?
            """, (f"%id={evento['id']}%", hoje.isoformat()))
            
            if existente.empty:
                hora = evento['hora_evento'] or "Dia todo"
                criar_notificacao(
                    tipo="agenda",
                    titulo=f"📅 Hoje: {evento['titulo']}",
                    mensagem=f"Horário: {hora}",
                    link_acao=f"page=Agenda&id={evento['id']}",
                    prioridade="media"
                )
                notificacoes_criadas += 1
    except Exception as e:
        logger.debug(f"Erro ao verificar agenda: {e}")
    
    return notificacoes_criadas


def render_badge_notificacoes():
    """Renderiza badge com contador de notificações não lidas"""
    usuario = st.session_state.get('user')
    count = contar_nao_lidas(usuario)
    
    if count > 0:
        return f"""
        <span style="
            background-color: #dc3545;
            color: white;
            border-radius: 50%;
            padding: 2px 8px;
            font-size: 12px;
            font-weight: bold;
            animation: pulse 2s infinite;
        ">{count}</span>
        """
    return ""


def render_centro_notificacoes():
    """Renderiza o centro de notificações (sidebar ou popover)"""
    usuario = st.session_state.get('user')
    
    # Gerar notificações automáticas (uma vez por sessão)
    if 'notif_geradas_hoje' not in st.session_state:
        st.session_state.notif_geradas_hoje = datetime.now().date()
        gerar_notificacoes_automaticas()
    elif st.session_state.notif_geradas_hoje != datetime.now().date():
        st.session_state.notif_geradas_hoje = datetime.now().date()
        gerar_notificacoes_automaticas()
    
    notifs = get_notificacoes_nao_lidas(usuario)
    
    if notifs.empty:
        st.success("✅ Nenhuma notificação pendente")
        return
    
    # Header com ações
    col1, col2 = st.columns([3, 1])
    col1.markdown(f"**🔔 {len(notifs)} notificação(ões)**")
    if col2.button("✓ Todas", key="mark_all_read", help="Marcar todas como lidas"):
        marcar_todas_lidas(usuario)
        st.rerun()
    
    # Lista de notificações
    for _, notif in notifs.iterrows():
        tipo_info = TIPOS_NOTIFICACAO.get(notif['tipo'], TIPOS_NOTIFICACAO['sistema'])
        
        with st.container(border=True):
            # Header da notificação
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.2em;">{tipo_info['icone']}</span>
                <strong style="color: {tipo_info['cor']};">{notif['titulo']}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            if notif['mensagem']:
                st.caption(notif['mensagem'])
            
            # Ações
            c1, c2 = st.columns(2)
            if c1.button("✓ Lida", key=f"read_{notif['id']}", use_container_width=True):
                marcar_como_lida(notif['id'])
                st.rerun()
            
            if c2.button("🗑️", key=f"archive_{notif['id']}", use_container_width=True):
                arquivar_notificacao(notif['id'])
                st.rerun()
