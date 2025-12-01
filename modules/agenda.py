"""
Módulo de Agenda - Gerenciamento de prazos, audiências e tarefas
Com integração ao Google Calendar
"""

import streamlit as st
import database as db
import google_calendar as gc
from datetime import datetime, timedelta
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
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "prazo", "audiencia", "tarefa"])
    with col2:
        filtro_status = st.selectbox("Status", ["Todos", "pendente", "concluido", "cancelado"])
    with col3:
        filtro_periodo = st.selectbox("Período", ["Próximos 7 dias", "Próximos 30 dias", "Todos"])
    
    # Buscar eventos
    eventos_df = db.get_agenda_eventos()
    
    if not eventos_df.empty:
        # Aplicar filtros
        if filtro_tipo != "Todos":
            eventos_df = eventos_df[eventos_df['tipo'] == filtro_tipo]
        
        if filtro_status != "Todos":
            eventos_df = eventos_df[eventos_df['status'] == filtro_status]
        
        if filtro_periodo == "Próximos 7 dias":
            data_limite = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            eventos_df = eventos_df[eventos_df['data_evento'] <= data_limite]
        elif filtro_periodo == "Próximos 30 dias":
            data_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            eventos_df = eventos_df[eventos_df['data_evento'] <= data_limite]
        
        # Ordenar por data
        eventos_df = eventos_df.sort_values('data_evento')
        
        # Exibir eventos
        st.info(f"Total: {len(eventos_df)} evento(s)")
        
        for idx, evento in eventos_df.iterrows():
            render_card_evento(evento)
    else:
        st.info("Nenhum evento cadastrado.")


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
    
    with st.container():
        col1, col2, col3 = st.columns([6, 2, 2])
        
        with col1:
            st.markdown(f"### {icone} {evento['titulo']}")
            st.caption(f"📅 {evento['data_evento']} | {status_icon} {evento['status'].upper()}")
            if evento.get('descricao'):
                st.text(evento['descricao'])
            if evento.get('responsavel'):
                st.caption(f"👤 Responsável: {evento['responsavel']}")
        
        with col2:
            # Botão editar
            if st.button("✏️ Editar", key=f"edit_{evento['id']}"):
                st.session_state[f'editing_{evento["id"]}'] = True
                st.rerun()
        
        with col3:
            # Botão concluir
            if evento['status'] == 'pendente':
                if st.button("✅ Concluir", key=f"complete_{evento['id']}"):
                    db.crud_update(
                        'agenda',
                        {'status': 'concluido'},
                        'id = ?',
                        (evento['id'],),
                        f"Evento {evento['id']} concluído"
                    )
                    st.success("Evento marcado como concluído!")
                    st.rerun()
        
        st.markdown("---")


def render_novo_evento():
    """Renderiza formulário de novo evento"""
    st.subheader("➕ Cadastrar Novo Evento")
    
    with st.form("form_novo_evento"):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo = st.selectbox("Tipo de Evento *", ["prazo", "audiencia", "tarefa"])
            titulo = st.text_input("Título *")
            data_evento = st.date_input("Data do Evento *", value=datetime.now())
        
        with col2:
            prioridade = st.selectbox("Prioridade", ["baixa", "media", "alta", "urgente"])
            responsavel = st.text_input("Responsável", value=st.session_state.get('user', ''))
            cor = st.color_picker("Cor", value="#FF6B6B")
        
        descricao = st.text_area("Descrição")
        
        # Vincular a processo (opcional)
        processos_df = db.sql_get('processos', 'numero_processo')
        if not processos_df.empty:
            processos_opcoes = ["Nenhum"] + processos_df['numero_processo'].tolist()
            processo_selecionado = st.selectbox("Vincular a Processo", processos_opcoes)
        else:
            processo_selecionado = "Nenhum"
        
        # Sincronizar com Google Calendar
        sync_google = st.checkbox("Sincronizar com Google Calendar", value=True)
        
        submitted = st.form_submit_button("💾 Salvar Evento", type="primary")
        
        if submitted:
            if not titulo:
                st.error("O título é obrigatório!")
            else:
                # Preparar dados
                id_processo = None
                if processo_selecionado != "Nenhum":
                    proc = processos_df[processos_df['numero_processo'] == processo_selecionado]
                    if not proc.empty:
                        id_processo = int(proc.iloc[0]['id'])
                
                evento_data = {
                    'tipo': tipo,
                    'titulo': titulo,
                    'descricao': descricao,
                    'data_evento': data_evento.strftime('%Y-%m-%d'),
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
                else:
                    st.success(f"✅ Evento criado com sucesso!")
                
                st.balloons()
                st.rerun()


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
                        importados = 0
                        for evento in eventos:
                            # Verificar se já existe
                            eventos_existentes = db.sql_get('agenda')
                            if not eventos_existentes.empty:
                                existe = eventos_existentes[
                                    eventos_existentes['google_calendar_id'] == evento['google_calendar_id']
                                ]
                                if not existe.empty:
                                    continue
                            
                            # Inserir evento
                            db.crud_insert('agenda', evento, f"Importado do Google: {evento['titulo']}")
                            importados += 1
                        
                        st.success(f"✅ {importados} evento(s) importado(s) com sucesso!")
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
            with st.spinner("Iniciando autenticação..."):
                service = gc.autenticar_google(username)
                if service:
                    st.success("✅ Conectado com sucesso!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Erro na autenticação. Verifique se o arquivo credentials.json está presente.")
