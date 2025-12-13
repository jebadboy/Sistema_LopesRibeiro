"""
Módulo de Agenda - Gerenciamento de prazos, audiências e tarefas
Com integração ao Google Calendar
"""

import streamlit as st
import os
import database as db
import google_calendar as gc
import utils as ut
import urllib.parse
from datetime import datetime, timedelta, time as dt_time
import pandas as pd
import calendar as cal

def render():
    """Função principal do módulo de Agenda"""
    st.title("📅 Agenda e Compromissos")
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "📆 Calendário",
        "📋 Lista de Eventos",
        "➕ Novo Evento",
        "⚙️ Configurações Google"
    ])
    
    with tab1:
        render_calendario()
    
    with tab2:
        render_lista_eventos()
    
    with tab3:
        render_novo_evento()
    
    with tab4:
        render_config_google()


def render_calendario():
    """Renderiza visualização de calendário mensal"""
    st.subheader("📆 Visualização Mensal")
    
    # Seletor de mês/ano
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        mes_atual = datetime.now().month
        mes = st.selectbox("Mês", range(1, 13), index=mes_atual-1, 
                          format_func=lambda x: [
                              "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                              "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
                          ][x-1])
    
    with col2:
        ano = st.number_input("Ano", min_value=2020, max_value=2030, 
                             value=datetime.now().year)
    
    # Filtros
    with st.sidebar:
        st.subheader("🔍 Filtros")
        filtro_tipo = st.multiselect("Tipo de Evento", 
                                      ["prazo", "audiencia", "tarefa"],
                                      default=["prazo", "audiencia", "tarefa"])
        filtro_status = st.multiselect("Status",
                                       ["pendente", "concluido", "cancelado"],
                                       default=["pendente"])
        filtro_responsavel = st.text_input("Responsável")
    
    # Buscar eventos do mês
    data_inicio = f"{ano}-{mes:02d}-01"
    ultimo_dia = cal.monthrange(ano, mes)[1]
    data_fim = f"{ano}-{mes:02d}-{ultimo_dia}"
    
    eventos_df = db.get_agenda_eventos()
    
    if not eventos_df.empty:
        # Aplicar filtros
        eventos_filtrados = eventos_df[
            (eventos_df['data_evento'] >= data_inicio) &
            (eventos_df['data_evento'] <= data_fim)
        ]
        
        if filtro_tipo:
            eventos_filtrados = eventos_filtrados[eventos_filtrados['tipo'].isin(filtro_tipo)]
        if filtro_status:
            eventos_filtrados = eventos_filtrados[eventos_filtrados['status'].isin(filtro_status)]
        if filtro_responsavel:
            eventos_filtrados = eventos_filtrados[
                eventos_filtrados['responsavel'].str.contains(filtro_responsavel, case=False, na=False)
            ]
        
        # Exibir resumo
        st.metric("Total de Eventos", len(eventos_filtrados))
        
        # Agrupar por dia
        if not eventos_filtrados.empty:
            eventos_por_dia = eventos_filtrados.groupby('data_evento').size()
            
            # Grid de calendário
            st.markdown("---")
            gerar_calendario_visual(ano, mes, eventos_por_dia, eventos_filtrados)
        else:
            st.info("Nenhum evento encontrado para este mês com os filtros selecionados.")
    else:
        st.info("Nenhum evento cadastrado ainda.")


def gerar_calendario_visual(ano, mes, eventos_por_dia, eventos_df):
    """Gera grid visual do calendário"""
    # Obter primeiro dia do mês e total de dias
    primeiro_dia_semana = cal.monthrange(ano, mes)[0]  # 0=Segunda
    total_dias = cal.monthrange(ano, mes)[1]
    
    # Dias da semana
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    cols_header = st.columns(7)
    for i, dia in enumerate(dias_semana):
        cols_header[i].markdown(f"**{dia}**")
    
    # Calcular quantas semanas precisamos
    dias_antes = (primeiro_dia_semana + 7) % 7  # Ajustar para segunda = 0
    total_celulas = dias_antes + total_dias
    semanas = (total_celulas + 6) // 7
    
    dia_atual = 1
    hoje = datetime.now().date()
    
    for semana in range(semanas):
        cols = st.columns(7)
        for dia_semana in range(7):
            indice = semana * 7 + dia_semana
            
            if indice < dias_antes or dia_atual > total_dias:
                cols[dia_semana].markdown("")  # Célula vazia
            else:
                data_str = f"{ano}-{mes:02d}-{dia_atual:02d}"
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                
                # Verificar se tem eventos neste dia
                num_eventos = eventos_por_dia.get(data_str, 0)
                
                # Estilo do dia
                estilo = ""
                if data_obj == hoje:
                    estilo = "background-color: #1f77b4; color: white; border-radius: 5px; padding: 5px;"
                elif num_eventos > 0:
                    estilo = "background-color: #ff7f0e; color: white; border-radius: 5px; padding: 5px;"
                
                # Exibir dia
                if estilo:
                    cols[dia_semana].markdown(
                        f'<div style="{estilo}"><strong>{dia_atual}</strong><br/>{num_eventos} evento(s)</div>',
                        unsafe_allow_html=True
                    )
                else:
                    cols[dia_semana].markdown(f"**{dia_atual}**")
                
                # Mostrar eventos do dia ao expandir
                if num_eventos > 0:
                    eventos_dia = eventos_df[eventos_df['data_evento'] == data_str]
                    with cols[dia_semana].expander(f"Ver {num_eventos}"):
                        for _, evento in eventos_dia.iterrows():
                            icone = {"prazo": "⚖️", "audiencia": "👥", "tarefa": "📝"}.get(evento['tipo'], "📌")
                            st.caption(f"{icone} {evento['titulo']}")
                
                dia_atual += 1


def render_lista_eventos():
    """Renderiza lista completa de eventos"""
    st.subheader("📋 Todos os Eventos")
    
    # Buscar todos os eventos primeiro (para notificações e filtros)
    todos_eventos_df = db.get_agenda_eventos()
    
    # === NOTIFICAÇÃO DE EVENTOS PRÓXIMOS (24h) ===
    if not todos_eventos_df.empty:
        agora = datetime.now()
        amanha = (agora + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')
        hoje_str = agora.strftime('%Y-%m-%d')
        
        # Filtrar eventos pendentes nas próximas 24h
        eventos_24h = todos_eventos_df[
            (todos_eventos_df['status'] == 'pendente') & 
            (todos_eventos_df['data_evento'] >= hoje_str) &
            (todos_eventos_df['data_evento'] <= (agora + timedelta(days=1)).strftime('%Y-%m-%d'))
        ]
        
        if len(eventos_24h) > 0:
            st.warning(f"⚠️ **ATENÇÃO:** {len(eventos_24h)} evento(s) nas próximas 24 horas!")
            with st.expander("Ver eventos urgentes"):
                for _, ev in eventos_24h.iterrows():
                    hora = ev.get('hora_evento', '')
                    st.markdown(f"• **{ev['titulo']}** - {ev['data_evento']} {hora}")
    
    # === CAMPO DE BUSCA ===
    busca = st.text_input("🔍 Buscar por título", placeholder="Digite para pesquisar...")
    
    # === FILTROS RÁPIDOS ===
    st.markdown("**Filtros rápidos:**")
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        if st.button("📅 Hoje", use_container_width=True):
            st.session_state['filtro_rapido'] = 'hoje'
    with col_btn2:
        if st.button("⚡ Amanhã", use_container_width=True):
            st.session_state['filtro_rapido'] = 'amanha'
    with col_btn3:
        if st.button("📆 7 dias", use_container_width=True):
            st.session_state['filtro_rapido'] = '7dias'
    with col_btn4:
        if st.button("🔄 Limpar", use_container_width=True):
            st.session_state['filtro_rapido'] = None
    
    st.markdown("---")
    
    # Filtros regulares
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "prazo", "audiencia", "tarefa"])
    with col2:
        filtro_status = st.selectbox("Status", ["Todos", "pendente", "concluido", "cancelado"], index=1)
    with col3:
        filtro_periodo = st.selectbox("Período", ["Hoje", "Amanhã", "Próximos 7 dias", "Próximos 30 dias", "Todos"])
    
    # === BOTÕES DE EXPORTAÇÃO ===
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        exportar_excel = st.button("📊 Exportar Excel", use_container_width=True)
    with col_exp2:
        exportar_pdf = st.button("📄 Exportar PDF", use_container_width=True)
    
    if not todos_eventos_df.empty:
        eventos_df = todos_eventos_df.copy()
        
        # Aplicar filtro rápido se existir
        filtro_rapido = st.session_state.get('filtro_rapido')
        hoje = datetime.now().strftime('%Y-%m-%d')
        amanha_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        if filtro_rapido == 'hoje':
            eventos_df = eventos_df[eventos_df['data_evento'] == hoje]
        elif filtro_rapido == 'amanha':
            eventos_df = eventos_df[eventos_df['data_evento'] == amanha_str]
        elif filtro_rapido == '7dias':
            data_limite = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            eventos_df = eventos_df[(eventos_df['data_evento'] >= hoje) & (eventos_df['data_evento'] <= data_limite)]
        
        # Aplicar busca por título
        if busca:
            eventos_df = eventos_df[eventos_df['titulo'].str.contains(busca, case=False, na=False)]
        
        # Aplicar filtros regulares
        if filtro_tipo != "Todos":
            eventos_df = eventos_df[eventos_df['tipo'] == filtro_tipo]
        
        if filtro_status != "Todos":
            eventos_df = eventos_df[eventos_df['status'] == filtro_status]
        
        # Filtrar por período
        if filtro_periodo == "Hoje":
            eventos_df = eventos_df[eventos_df['data_evento'] == hoje]
        elif filtro_periodo == "Amanhã":
            eventos_df = eventos_df[eventos_df['data_evento'] == amanha_str]
        elif filtro_periodo == "Próximos 7 dias":
            data_limite = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            eventos_df = eventos_df[(eventos_df['data_evento'] >= hoje) & (eventos_df['data_evento'] <= data_limite)]
        elif filtro_periodo == "Próximos 30 dias":
            data_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            eventos_df = eventos_df[(eventos_df['data_evento'] >= hoje) & (eventos_df['data_evento'] <= data_limite)]
        
        # Ordenar por data e hora
        eventos_df = eventos_df.sort_values(['data_evento', 'hora_evento'])
        
        # === EXPORTAÇÃO ===
        if exportar_excel and not eventos_df.empty:
            try:
                import io
                output = io.BytesIO()
                eventos_df.to_excel(output, index=False, engine='openpyxl')
                st.download_button(
                    "⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name=f"agenda_{hoje}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Erro ao exportar: {e}")
        
        if exportar_pdf and not eventos_df.empty:
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                import io
                
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, 800, f"Agenda - {hoje}")
                c.setFont("Helvetica", 10)
                
                y = 770
                for _, ev in eventos_df.iterrows():
                    if y < 50:
                        c.showPage()
                        y = 800
                    hora = ev.get('hora_evento', '')
                    linha = f"{ev['data_evento']} {hora} - {ev['titulo']} [{ev['status']}]"
                    c.drawString(50, y, linha[:80])
                    y -= 15
                
                c.save()
                buffer.seek(0)
                st.download_button(
                    "⬇️ Download PDF",
                    data=buffer.getvalue(),
                    file_name=f"agenda_{hoje}.pdf",
                    mime="application/pdf"
                )
            except ImportError:
                st.warning("Biblioteca reportlab não instalada. Use: pip install reportlab")
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")
        
        # Exibir eventos
        st.info(f"Total: {len(eventos_df)} evento(s)")
        
        for idx, evento in eventos_df.iterrows():
            # Verificar se está em modo edição
            if st.session_state.get(f'editing_{evento["id"]}', False):
                render_form_edicao(evento)
            else:
                render_card_evento(evento)
    else:
        st.info("Nenhum evento cadastrado.")


def render_form_edicao(evento):
    """Renderiza formulário de edição de evento"""
    with st.container():
        st.markdown(f"### ✏️ Editando: {evento['titulo']}")
        
        with st.form(f"form_edit_{evento['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                titulo = st.text_input("Título *", value=evento.get('titulo', ''))
                data_evento = st.date_input(
                    "Data *", 
                    value=datetime.strptime(evento['data_evento'], '%Y-%m-%d').date() if evento.get('data_evento') else datetime.now().date()
                )
                hora_atual = evento.get('hora_evento')
                if hora_atual:
                    try:
                        h, m = hora_atual.split(':')
                        hora_valor = dt_time(int(h), int(m))
                    except:
                        hora_valor = dt_time(9, 0)
                else:
                    hora_valor = dt_time(9, 0)
                hora_evento = st.time_input("Horário", value=hora_valor)
            
            with col2:
                tipo = st.selectbox("Tipo", ["tarefa", "prazo", "audiencia"], 
                                   index=["tarefa", "prazo", "audiencia"].index(evento.get('tipo', 'tarefa')) if evento.get('tipo') in ["tarefa", "prazo", "audiencia"] else 0)
                prioridade = st.selectbox("Prioridade", ["baixa", "media", "alta", "urgente"],
                                         index=["baixa", "media", "alta", "urgente"].index(evento.get('prioridade', 'media')) if evento.get('prioridade') in ["baixa", "media", "alta", "urgente"] else 1)
                status = st.selectbox("Status", ["pendente", "concluido", "cancelado"],
                                     index=["pendente", "concluido", "cancelado"].index(evento.get('status', 'pendente')) if evento.get('status') in ["pendente", "concluido", "cancelado"] else 0)
            
            descricao = st.text_area("Descrição", value=evento.get('descricao', '') or '')
            responsavel = st.text_input("Responsável", value=evento.get('responsavel', '') or '')
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                salvar = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
            with col_btn2:
                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if salvar:
                dados_atualizados = {
                    'titulo': titulo,
                    'data_evento': data_evento.strftime('%Y-%m-%d'),
                    'hora_evento': hora_evento.strftime('%H:%M'),
                    'tipo': tipo,
                    'prioridade': prioridade,
                    'status': status,
                    'descricao': descricao,
                    'responsavel': responsavel
                }
                db.crud_update('agenda', dados_atualizados, 'id = ?', (evento['id'],), f"Evento {evento['id']} atualizado")
                
                # Sincronizar com Google Calendar se o evento tiver ID do Google
                if evento.get('google_calendar_id'):
                    try:
                        username = st.session_state.get('user', 'admin')
                        gc.sincronizar_evento(username, evento['id'], dados_atualizados, operacao='atualizar')
                        st.success("✅ Evento atualizado localmente e no Google Calendar!")
                    except Exception as e:
                        st.warning(f"Evento atualizado localmente, mas houve erro na sincronização com Google: {e}")
                else:
                    st.success("✅ Evento atualizado com sucesso!")
                
                st.session_state[f'editing_{evento["id"]}'] = False
                st.rerun()
            
            if cancelar:
                st.session_state[f'editing_{evento["id"]}'] = False
                st.rerun()
        
        st.markdown("---")


def gerar_link_lembrete_whatsapp(evento, telefone=None):
    """
    Gera link de WhatsApp com mensagem de lembrete do evento.
    
    Args:
        evento: Dict com dados do evento
        telefone: Telefone do destinatário (opcional, busca do processo/cliente se não informado)
    
    Returns:
        str: Link do WhatsApp ou None se não tiver telefone
    """
    # Tentar obter telefone
    if not telefone:
        # Buscar do processo vinculado, se houver
        if evento.get('id_processo'):
            try:
                proc = db.sql_get_query(
                    "SELECT c.telefone FROM processos p JOIN clientes c ON p.id_cliente = c.id WHERE p.id = ?",
                    (evento['id_processo'],)
                )
                if not proc.empty and proc.iloc[0]['telefone']:
                    telefone = proc.iloc[0]['telefone']
            except:
                pass
    
    if not telefone:
        return None
    
    # Calcular dias até o evento
    try:
        data_evento = datetime.strptime(evento['data_evento'], '%Y-%m-%d').date()
        dias_restantes = (data_evento - datetime.now().date()).days
        
        if dias_restantes < 0:
            dias_texto = "já passou"
        elif dias_restantes == 0:
            dias_texto = "é HOJE"
        elif dias_restantes == 1:
            dias_texto = "é AMANHÃ"
        else:
            dias_texto = f"faltam {dias_restantes} dias"
    except:
        dias_texto = ""
    
    # Formatar mensagem
    tipo_nome = {"prazo": "Prazo", "audiencia": "Audiência", "tarefa": "Tarefa"}.get(evento['tipo'], "Compromisso")
    
    mensagem = f"⚠️ *Lembrete - {tipo_nome}*\n\n"
    mensagem += f"📋 {evento['titulo']}\n"
    mensagem += f"📅 Data: {evento['data_evento']}"
    if evento.get('hora_evento'):
        mensagem += f" às {evento['hora_evento']}"
    mensagem += f"\n⏰ {dias_texto.capitalize()}\n"
    
    if evento.get('descricao'):
        mensagem += f"\nℹ️ {evento['descricao'][:100]}"
    
    # Limpar telefone
    telefone_limpo = ut.limpar_numeros(telefone)
    if not telefone_limpo.startswith('55'):
        telefone_limpo = '55' + telefone_limpo
    
    # Gerar link
    mensagem_encoded = urllib.parse.quote(mensagem)
    return f"https://wa.me/{telefone_limpo}?text={mensagem_encoded}"


def render_card_evento(evento):
    """Renderiza card de um evento"""
    # Ícones por tipo
    icones = {"prazo": "⚖️", "audiencia": "👥", "tarefa": "📝"}
    icone = icones.get(evento['tipo'], "📌")
    
    # Cores por prioridade
    cores = {
        "baixa": "#28a745",
        "media": "#ffc107",
        "alta": "#fd7e14",
        "urgente": "#dc3545"
    }
    cor = cores.get(evento.get('prioridade', 'media'), "#6c757d")
    
    # Status
    status_emoji = {"pendente": "🔴", "concluido": "✅", "cancelado": "❌"}
    status_icon = status_emoji.get(evento['status'], "⚪")
    
    # Calcular dias restantes
    try:
        data_evento = datetime.strptime(evento['data_evento'], '%Y-%m-%d').date()
        dias_restantes = (data_evento - datetime.now().date()).days
        if dias_restantes == 0:
            dias_badge = "🔥 HOJE"
        elif dias_restantes == 1:
            dias_badge = "⚡ AMANHÃ"
        elif dias_restantes > 0 and dias_restantes <= 3:
            dias_badge = f"⚠️ {dias_restantes} dias"
        elif dias_restantes > 0:
            dias_badge = f"📆 {dias_restantes} dias"
        else:
            dias_badge = "⏰ Passado"
    except:
        dias_badge = ""
    
    # Estilo do card com borda colorida por prioridade
    st.markdown(f"""
        <style>
        .card-prioridade-{evento['id']} {{
            border-left: 5px solid {cor};
            padding-left: 15px;
            margin-bottom: 10px;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f'<div class="card-prioridade-{evento["id"]}">', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns([4, 2, 1, 1, 1])
        
        with col1:
            # Badge de prioridade colorido
            prioridade = evento.get('prioridade', 'media')
            prioridade_labels = {"baixa": "🟢 Baixa", "media": "🟡 Média", "alta": "🟠 Alta", "urgente": "🔴 Urgente"}
            prioridade_label = prioridade_labels.get(prioridade, "")
            
            st.markdown(f"### {icone} {evento['titulo']}")
            # Incluir horário se disponível
            hora_str = f" às {evento['hora_evento']}" if evento.get('hora_evento') else ""
            st.caption(f"📅 {evento['data_evento']}{hora_str} | {status_icon} {evento['status'].upper()} | {dias_badge} | {prioridade_label}")
            if evento.get('descricao'):
                st.markdown(evento['descricao'], unsafe_allow_html=True)
            if evento.get('responsavel'):
                st.caption(f"👤 Responsável: {evento['responsavel']}")
        
        with col2:
            # Botão WhatsApp (se evento pendente)
            if evento['status'] == 'pendente':
                link_whatsapp = gerar_link_lembrete_whatsapp(evento)
                if link_whatsapp:
                    st.link_button("📱 WhatsApp", link_whatsapp, use_container_width=True)
                else:
                    # Mostrar campo para digitar telefone
                    tel_manual = st.text_input("📱 Tel:", key=f"tel_{evento['id']}", placeholder="11999999999")
                    if tel_manual:
                        link_manual = gerar_link_lembrete_whatsapp(evento, tel_manual)
                        if link_manual:
                            st.link_button("📱 Enviar", link_manual, use_container_width=True)
        
        with col3:
            # Botão editar
            if st.button("✏️", key=f"edit_{evento['id']}", help="Editar evento"):
                st.session_state[f'editing_{evento["id"]}'] = True
                st.rerun()
        
        with col4:
            # Botão concluir com confirmação
            if evento['status'] == 'pendente':
                # Sistema de confirmação
                confirmar_key = f"confirmar_concluir_{evento['id']}"
                if st.session_state.get(confirmar_key, False):
                    if st.button("✔️ Sim", key=f"confirm_yes_{evento['id']}", help="Confirmar"):
                        db.crud_update(
                            'agenda',
                            {'status': 'concluido'},
                            'id = ?',
                            (evento['id'],),
                            f"Evento {evento['id']} concluído"
                        )
                        st.session_state[confirmar_key] = False
                        st.success("Evento concluído!")
                        st.rerun()
                else:
                    if st.button("✅", key=f"complete_{evento['id']}", help="Marcar como concluído"):
                        st.session_state[confirmar_key] = True
                        st.rerun()
        
        with col5:
            # Botão excluir com confirmação
            excluir_key = f"confirmar_excluir_{evento['id']}"
            if st.session_state.get(excluir_key, False):
                if st.button("🗑️ Sim", key=f"delete_yes_{evento['id']}", help="Confirmar exclusão"):
                    # Excluir do Google Calendar se tiver ID
                    if evento.get('google_calendar_id'):
                        try:
                            username = st.session_state.get('user', 'admin')
                            gc.sincronizar_evento(username, evento['id'], evento, operacao='excluir')
                        except:
                            pass  # Continuar mesmo se falhar no Google
                    db.crud_delete('agenda', 'id = ?', (evento['id'],), f"Evento {evento['id']} excluído")
                    st.session_state[excluir_key] = False
                    st.success("Evento excluído!")
                    st.rerun()
            else:
                if st.button("🗑️", key=f"delete_{evento['id']}", help="Excluir evento"):
                    st.session_state[excluir_key] = True
                    st.rerun()
        
        # Botões de cancelar confirmação (se alguma confirmação estiver ativa)
        confirmar_concluir = st.session_state.get(f"confirmar_concluir_{evento['id']}", False)
        confirmar_excluir = st.session_state.get(f"confirmar_excluir_{evento['id']}", False)
        
        if confirmar_concluir or confirmar_excluir:
            if st.button("❌ Cancelar", key=f"cancel_action_{evento['id']}"):
                st.session_state[f"confirmar_concluir_{evento['id']}"] = False
                st.session_state[f"confirmar_excluir_{evento['id']}"] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")


def render_novo_evento():
    """Renderiza formulário de novo evento"""
    st.subheader("➕ Cadastrar Novo Evento")
    
    # Contador para forçar reset do formulário após salvar
    if 'form_reset_counter' not in st.session_state:
        st.session_state['form_reset_counter'] = 0
    
    with st.form(f"form_novo_evento_{st.session_state['form_reset_counter']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo = st.selectbox("Tipo de Evento *", ["prazo", "audiencia", "tarefa"])
            titulo = st.text_input("Título *")
            data_evento = st.date_input("Data do Evento *", value=datetime.now())
            # Horário obrigatório com valor padrão 9:00
            hora_evento = st.time_input("Horário *", value=dt_time(9, 0), help="Horário do compromisso (obrigatório)")
        
        with col2:
            prioridade = st.selectbox("Prioridade", ["baixa", "media", "alta", "urgente"])
            responsavel = st.text_input("Responsável", value=st.session_state.get('user', ''))
            cor = st.color_picker("Cor", value="#FF6B6B")
        
        descricao = st.text_area("Descrição")
        
        # Vincular a processo (opcional)
        processos_df = db.sql_get('processos', 'id, acao, cliente_nome')
        if not processos_df.empty:
            # Criar lista formatada "[ID] Cliente - Ação" para garantir unicidade
            processos_df['label'] = "[ID: " + processos_df['id'].astype(str) + "] " + processos_df['cliente_nome'] + " - " + processos_df['acao']
            processos_opcoes = ["Nenhum"] + processos_df['label'].tolist()
            processo_selecionado = st.selectbox("Vincular a Processo", processos_opcoes)
        else:
            processo_selecionado = "Nenhum"
        
        # Sincronizar com Google Calendar
        sync_google = st.checkbox("Sincronizar com Google Calendar", value=True)
        
        submitted = st.form_submit_button("💾 Salvar Evento", type="primary")
        
        if submitted:
            # Proteção contra clique duplo
            if st.session_state.get('salvando_evento', False):
                st.warning("⚠️ Salvamento em andamento, aguarde...")
                return
            
            if not titulo:
                st.error("O título é obrigatório!")
            else:
                try:
                    st.session_state['salvando_evento'] = True
                    # Preparar dados
                    id_processo = None
                    if processo_selecionado != "Nenhum":
                        proc = processos_df[processos_df['label'] == processo_selecionado]
                        if not proc.empty:
                            id_processo = int(proc.iloc[0]['id'])
                    
                    evento_data = {
                        'tipo': tipo,
                        'titulo': titulo,
                        'descricao': descricao,
                        'data_evento': data_evento.strftime('%Y-%m-%d'),
                        'hora_evento': hora_evento.strftime('%H:%M'),  # Obrigatório
                        'responsavel': responsavel,
                        'id_processo': id_processo,
                        'status': 'pendente',
                        'prioridade': prioridade,
                        'cor': cor
                    }
                    
                    # Salvar no banco
                    evento_id = db.crud_insert('agenda', evento_data, f"Novo evento: {titulo}")
                    
                    # Sincronizar com Google Calendar se solicitado
                    google_event_id = None
                    if sync_google and evento_id:
                        username = st.session_state.get('user', 'admin')
                        try:
                            google_event_id = gc.sincronizar_evento(
                                username, evento_id, evento_data, operacao='criar'
                            )
                            
                            if google_event_id:
                                # Atualizar evento com ID do Google
                                db.crud_update(
                                    'agenda',
                                    {'google_calendar_id': google_event_id},
                                    'id = ?',
                                    (evento_id,),
                                    f"Adicionado ID Google Calendar: {google_event_id}"
                                )
                                st.success(f"✅ Evento criado e sincronizado com Google Calendar!")
                            else:
                                st.warning("Evento criado, mas não foi possível sincronizar com Google Calendar. Verifique se você está autenticado.")
                        except Exception as e:
                            st.warning(f"Evento criado localmente, mas houve erro na sincronização com Google: {e}")
                    else:
                        st.success(f"✅ Evento criado com sucesso!")
                    
                    # Incrementar contador para limpar formulário
                    st.session_state['form_reset_counter'] += 1
                    st.balloons()
                    st.rerun()
                finally:
                    st.session_state['salvando_evento'] = False


def render_config_google():
    """Renderiza configurações do Google Calendar"""
    st.subheader("⚙️ Configurações Google Calendar")
    
    username = st.session_state.get('user', 'admin')
    autenticado = gc.verificar_autenticacao(username)
    
    if autenticado:
        st.success("✅ Você está conectado ao Google Calendar!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"👤 Usuário: **{username}**")
        
        with col2:
            if st.button("🔓 Desconectar", type="secondary"):
                if gc.desconectar_google(username):
                    st.success("Desconectado com sucesso!")
                    st.rerun()
        
        st.markdown("---")
        
        # Importar eventos
        st.subheader("📥 Importar Eventos do Google Calendar")
        st.caption("Importe eventos existentes do Google Calendar para o sistema.")
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio_import = st.date_input("Data Início", value=datetime.now())
        with col2:
            data_fim_import = st.date_input("Data Fim", value=datetime.now() + timedelta(days=90))
        
        if st.button("📥 Importar Eventos"):
            service = gc.autenticar_google(username)
            if service:
                with st.spinner("Importando eventos..."):
                    eventos = gc.importar_eventos_google(
                        service,
                        datetime.combine(data_inicio_import, datetime.min.time()),
                        datetime.combine(data_fim_import, datetime.max.time())
                    )
                    
                    if eventos:
                        st.info(f"Encontrados {len(eventos)} eventos no Google Calendar. Verificando duplicatas...")
                        importados = 0
                        
                        # OTIMIZAÇÃO: Buscar existentes UMA VEZ antes do loop
                        eventos_existentes = db.sql_get('agenda')
                        ids_existentes = set()
                        if not eventos_existentes.empty and 'google_calendar_id' in eventos_existentes.columns:
                            ids_existentes = set(eventos_existentes['google_calendar_id'].dropna().tolist())
                        
                        for evento in eventos:
                            # Verificar se já existe (busca otimizada)
                            if evento['google_calendar_id'] in ids_existentes:
                                continue
                            
                            # Inserir evento
                            db.crud_insert('agenda', evento, f"Importado do Google: {evento['titulo']}")
                            importados += 1
                        
                        if importados > 0:
                            st.success(f"✅ {importados} evento(s) importado(s) com sucesso!")
                        else:
                            st.warning("Todos os eventos encontrados já estão cadastrados no sistema.")
                    else:
                        st.info("Nenhum evento encontrado no período selecionado.")
            else:
                st.error("Erro ao conectar com Google Calendar.")
        
    else:
        st.warning("⚠️ Você não está conectado ao Google Calendar.")
        st.info("""
        **Para conectar:**
        1. Certifique-se de que o arquivo `credentials.json` está na pasta do projeto
        2. Clique no botão abaixo para iniciar a autenticação
        3. Uma janela do navegador será aberta para você autorizar o acesso
        4. Após autorizar, volte para o sistema
        """)
        
        if st.button("🔐 Conectar com Google Calendar", type="primary"):
            if not os.path.exists('credentials.json') and not os.path.exists('service_account.json'):
                st.error("Arquivo `credentials.json` não encontrado. Por favor, adicione o arquivo na pasta do projeto.")
            else:
                with st.spinner("Iniciando autenticação..."):
                    service = gc.autenticar_google(username)
                    if service:
                        st.success("✅ Conectado com sucesso!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Erro na autenticação. Verifique os logs para mais detalhes.")
