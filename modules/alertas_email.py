"""
Módulo de Alertas de E-mail - Sistema Lopes & Ribeiro
Exibe alertas de intimações e e-mails importantes detectados pelo scheduler.
"""

import streamlit as st
import database as db
import utils as ut
from datetime import datetime

def render():
    """Renderiza o módulo de Alertas de E-mail."""
    st.markdown("<h1 style='color: var(--text-main);'>📧 Alertas de E-mail</h1>", unsafe_allow_html=True)
    
    # Tabs
    t1, t2, t3 = st.tabs(["🔔 Alertas Pendentes", "📋 Histórico", "⚙️ Configurações"])
    
    with t1:
        render_alertas_pendentes()
    
    with t2:
        render_historico()
    
    with t3:
        render_configuracoes()


def render_alertas_pendentes():
    """Exibe alertas não processados."""
    
    alertas = db.sql_get_query("""
        SELECT * FROM alertas_email 
        WHERE processado = 0 
        ORDER BY criado_em DESC
    """)
    
    if alertas.empty:
        st.success("✅ Nenhum alerta pendente!")
        st.caption("Execute o scheduler para verificar novos e-mails.")
        return
    
    st.warning(f"🔔 **{len(alertas)} alertas pendentes**")
    
    for idx, alerta in alertas.iterrows():
        with st.container(border=True):
            # Ícone baseado no tipo
            icones = {
                'alvará': '🏦',
                'mandado_pagamento': '💰',
                'depósito': '💵',
                'rpv': '⚖️',
                'precatório': '📜',
                'intimação': '⚠️',
                'citação': '📬'
            }
            icone = icones.get(alerta['tipo'], '📧')
            
            # Cor baseada no tipo (prioridade)
            if alerta['tipo'] in ['alvará', 'mandado_pagamento', 'depósito', 'rpv']:
                st.success(f"{icone} **{alerta['tipo'].upper()}** - Potencial entrada financeira!")
            elif alerta['tipo'] in ['intimação', 'citação']:
                st.warning(f"{icone} **{alerta['tipo'].upper()}** - Atenção ao prazo!")
            else:
                st.info(f"{icone} **{alerta['tipo'].upper()}**")
            
            # === ALERTA DE PRAZO IA (NOVO) ===
            prazo_dias = alerta.get('prazo_dias')
            data_fatal = alerta.get('data_fatal_sugerida')
            status_ia = alerta.get('status_ia', '')
            
            if prazo_dias and status_ia == 'sugestao_ia':
                st.warning(f"🤖 **IA identificou prazo de {int(prazo_dias)} dias.** Data fatal sugerida: **{data_fatal}**. Confere?")
            
            c1, c2 = st.columns([3, 1])
            
            with c1:
                st.markdown(f"**Assunto:** {alerta['assunto']}")
                st.caption(f"📮 {alerta['remetente']}")
                
                if alerta['numero_processo']:
                    st.markdown(f"📁 **Processo:** {alerta['numero_processo']}")
                    
                    # Mostrar se está vinculado
                    if alerta.get('processo_vinculado_id'):
                        st.caption(f"✅ Vinculado ao processo ID: {alerta['processo_vinculado_id']}")
                
                if alerta['valor_detectado'] and alerta['valor_detectado'] > 0:
                    st.markdown(f"💰 **Valor detectado:** {ut.formatar_moeda(alerta['valor_detectado'])}")
                
                with st.expander("Ver resumo"):
                    st.text(alerta['corpo_resumo'] or "Sem resumo disponível")
            
            with c2:
                st.caption(f"📅 {alerta['data_recebimento']}")
                
                # Botões IA para prazo
                if prazo_dias and status_ia == 'sugestao_ia':
                    if st.button("✅ Confirmar Prazo", key=f"confirmar_{alerta['id']}", use_container_width=True, type="primary"):
                        # Criar evento na agenda
                        try:
                            db.crud_insert("agenda", {
                                "tipo": "prazo",
                                "titulo": f"Prazo: {alerta['assunto'][:50]}",
                                "descricao": f"Prazo identificado pela IA. Processo: {alerta['numero_processo'] or 'N/A'}",
                                "data_evento": data_fatal,
                                "prioridade": "alta",
                                "status": "pendente",
                                "id_processo": alerta.get('processo_vinculado_id'),
                                "criado_em": datetime.now().isoformat()
                            })
                            # Atualizar status do alerta
                            db.sql_run("UPDATE alertas_email SET status_ia = 'confirmado', processado = 1 WHERE id = ?", (alerta['id'],))
                            st.success(f"📅 Prazo criado na Agenda para {data_fatal}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    
                    # Botão ajustar
                    with st.popover("✏️ Ajustar"):
                        nova_data = st.date_input("Nova data fatal", key=f"nova_data_{alerta['id']}")
                        if st.button("Salvar", key=f"salvar_data_{alerta['id']}"):
                            db.crud_insert("agenda", {
                                "tipo": "prazo",
                                "titulo": f"Prazo: {alerta['assunto'][:50]}",
                                "descricao": f"Prazo ajustado manualmente. Processo: {alerta['numero_processo'] or 'N/A'}",
                                "data_evento": nova_data.isoformat(),
                                "prioridade": "alta",
                                "status": "pendente",
                                "id_processo": alerta.get('processo_vinculado_id'),
                                "criado_em": datetime.now().isoformat()
                            })
                            db.sql_run("UPDATE alertas_email SET status_ia = 'ajustado', processado = 1 WHERE id = ?", (alerta['id'],))
                            st.success(f"📅 Prazo criado para {nova_data}!")
                            st.rerun()
                else:
                    if st.button("✅ Processar", key=f"proc_{alerta['id']}", use_container_width=True):
                        db.sql_run("UPDATE alertas_email SET processado = 1 WHERE id = ?", (alerta['id'],))
                        st.success("Alerta marcado como processado!")
                        st.rerun()
                
                # Se tiver número de processo, link para buscar
                if alerta['numero_processo']:
                    if st.button("🔍 Buscar Processo", key=f"buscar_{alerta['id']}", use_container_width=True):
                        st.session_state['busca_processo'] = alerta['numero_processo']
                        st.info(f"Busque na aba Processos: {alerta['numero_processo']}")


def render_historico():
    """Exibe histórico de alertas processados."""
    
    # Filtros
    c1, c2 = st.columns(2)
    
    with c1:
        filtro_tipo = st.multiselect(
            "Filtrar por tipo", 
            ["alvará", "mandado_pagamento", "depósito", "rpv", "precatório", "intimação", "citação"]
        )
    
    with c2:
        filtro_dias = st.selectbox("Período", ["7 dias", "30 dias", "90 dias", "Todos"], index=1)
    
    # Query base
    query = "SELECT * FROM alertas_email WHERE processado = 1"
    params = []
    
    if filtro_tipo:
        placeholders = ",".join(["?" for _ in filtro_tipo])
        query += f" AND tipo IN ({placeholders})"
        params.extend(filtro_tipo)
    
    if filtro_dias != "Todos":
        dias = int(filtro_dias.split()[0])
        query += f" AND criado_em >= date('now', '-{dias} days')"
    
    query += " ORDER BY criado_em DESC LIMIT 100"
    
    alertas = db.sql_get_query(query, tuple(params) if params else None)
    
    if alertas.empty:
        st.info("Nenhum alerta no histórico para os filtros selecionados.")
        return
    
    st.caption(f"Mostrando {len(alertas)} alertas")
    
    # Tabela resumida
    df_display = alertas[['tipo', 'assunto', 'numero_processo', 'valor_detectado', 'data_recebimento']].copy()
    df_display.columns = ['Tipo', 'Assunto', 'Processo', 'Valor', 'Data']
    df_display['Valor'] = df_display['Valor'].apply(lambda x: ut.formatar_moeda(x) if x else "-")
    
    st.dataframe(df_display, use_container_width=True)


def render_configuracoes():
    """Configurações do monitoramento de e-mails."""
    
    st.markdown("### ⚙️ Configurações do Monitoramento")
    
    st.info("""
    O monitoramento de e-mails é feito pelo **Windows Task Scheduler**.
    
    Para configurar:
    1. Abra `taskschd.msc`
    2. Criar Tarefa Básica
    3. Nome: `LopesRibeiro_EmailCheck`
    4. Disparador: Repetir a cada **30 minutos**
    5. Programa: `pythonw.exe` ou `python.exe`
    6. Argumentos: `"H:/Meu Drive/automatizacao/Sistema_LopesRibeiro/email_scheduler.py"`
    7. Iniciar em: `"H:/Meu Drive/automatizacao/Sistema_LopesRibeiro"`
    """)
    
    # Estatísticas
    st.markdown("### 📊 Estatísticas")
    
    stats = db.sql_get_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN processado = 0 THEN 1 ELSE 0 END) as pendentes,
            SUM(CASE WHEN processado = 1 THEN 1 ELSE 0 END) as processados
        FROM alertas_email
    """)
    
    if not stats.empty:
        row = stats.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Alertas", row['total'] or 0)
        c2.metric("Pendentes", row['pendentes'] or 0)
        c3.metric("Processados", row['processados'] or 0)
    
    # Por tipo
    por_tipo = db.sql_get_query("""
        SELECT tipo, COUNT(*) as qtd 
        FROM alertas_email 
        GROUP BY tipo 
        ORDER BY qtd DESC
    """)
    
    if not por_tipo.empty:
        st.markdown("#### Por Tipo")
        st.bar_chart(por_tipo.set_index('tipo'))
    
    # Botão para executar verificação manual
    st.markdown("### 🔄 Verificação Manual")
    
    if st.button("🔍 Verificar E-mails Agora", type="primary"):
        with st.spinner("Verificando e-mails..."):
            try:
                from workspace_integration import WorkspaceManager
                
                ws = WorkspaceManager()
                if ws.gmail.conectar("sistema"):
                    emails = ws.gmail.buscar_emails_recentes(max_results=20, dias_atras=1)
                    alertas = ws.gmail.processar_emails(emails)
                    
                    novos = 0
                    for alerta in alertas:
                        existente = db.sql_get_query(
                            "SELECT id FROM alertas_email WHERE assunto = ? LIMIT 1",
                            (alerta.assunto[:200],)
                        )
                        if existente.empty:
                            db.crud_insert("alertas_email", {
                                "tipo": alerta.tipo.value,
                                "remetente": alerta.remetente,
                                "assunto": alerta.assunto[:200],
                                "numero_processo": alerta.numero_processo,
                                "valor_detectado": alerta.valor_detectado,
                                "data_recebimento": alerta.data_recebimento,
                                "corpo_resumo": alerta.corpo_resumo[:1000] if alerta.corpo_resumo else "",
                                "processado": 0
                            })
                            novos += 1
                    
                    if novos > 0:
                        st.success(f"✅ {novos} novos alertas detectados!")
                    else:
                        st.info("Nenhum novo alerta encontrado.")
                    st.rerun()
                else:
                    st.error("❌ Falha ao conectar com Gmail. Verifique as credenciais.")
            except Exception as e:
                st.error(f"Erro: {e}")
