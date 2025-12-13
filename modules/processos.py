import streamlit as st
import database as db
import utils as ut
from datetime import datetime
import datajud_ui  # Busca DataJud
import datajud # Backend DataJud
import google_drive as gd  # Drive
import token_manager as tm
import pandas as pd
import time
import ai_gemini as ai
import permissions  # Sistema de permissões

# --- CONSTANTES ---
FASES_PROCESSUAIS = ["Distribuído", "A Ajuizar", "Aguardando Liminar", "Audiência Marcada", "Sentença", "Arquivado", "Em Andamento", "Suspenso"]

# Lista de comarcas prioritárias (RJ)
COMARCAS_RJ = ["Maricá", "Niterói", "São Gonçalo", "Itaboraí", "Saquarema", "Rio de Janeiro (Capital)", "Araruama", "Cabo Frio", "Outra"]

def render():
    st.markdown("<h1 style='color: var(--text-main);'>⚖️ Processos</h1>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Novo (+Calc)", "Gerenciar"])
    
    # --- ABA 1: NOVO PROCESSO ---
    with t1:
        render_novo_processo()

    # --- ABA 2: GERENCIAR ---
    with t2:
        render_gerenciar_processos()

def render_novo_processo():
    """Formulário unificado de cadastro de processo com integração DataJud"""
    
    # ==================== INICIALIZAÇÃO DO SESSION_STATE ====================
    if 'form_numero_cnj' not in st.session_state:
        st.session_state.form_numero_cnj = ''
    if 'form_classe' not in st.session_state:
        st.session_state.form_classe = ''
    if 'form_orgao' not in st.session_state:
        st.session_state.form_orgao = ''
    if 'form_comarca' not in st.session_state:
        st.session_state.form_comarca = ''
    if 'form_valor_causa' not in st.session_state:
        st.session_state.form_valor_causa = 0.0
    if 'form_data_dist' not in st.session_state:
        st.session_state.form_data_dist = None
    if 'form_cliente_idx' not in st.session_state:
        st.session_state.form_cliente_idx = 0
    if 'form_fase_idx' not in st.session_state:
        st.session_state.form_fase_idx = 0
    if 'form_movimentos' not in st.session_state:
        st.session_state.form_movimentos = []
    if 'datajud_sucesso' not in st.session_state:
        st.session_state.datajud_sucesso = False
    
    # ==================== CALCULADORA DE PRAZOS ====================
    st.markdown("#### 🧠 Calculadora de Prazos")
    vc = ut.calc_venc(datetime.now().date(), 15, "Dias Úteis")
    
    with st.expander("Calculadora de Prazos", expanded=False):
        c1, c2, c3 = st.columns(3)
        dp = c1.date_input("Data da Publicação")
        di = c2.number_input("Dias de Prazo", min_value=1, value=15)
        rg = c3.selectbox("Regra de Contagem", ["Dias Úteis", "Corridos"])
        vc = ut.calc_venc(dp, di, rg)
        st.info(f"📅 Data Fatal: **{vc.strftime('%d/%m/%Y')}**")
    
    st.divider()
    
    # ==================== BUSCA DATAJUD (FORA DO FORM) ====================
    st.markdown("#### 🔎 Buscar no DataJud (Autopreenchimento)")
    
    col_busca, col_btn = st.columns([4, 1])
    numero_busca = col_busca.text_input(
        "Número do Processo (CNJ)",
        placeholder="0000000-00.0000.0.00.0000",
        help="Digite o número completo (20 dígitos) e clique em Buscar",
        key="input_busca_cnj"
    )
    
    col_btn.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
    if col_btn.button("🔍 Buscar", type="primary", use_container_width=True):
        if numero_busca and numero_busca.strip():
            valido, erro = datajud.validar_numero_cnj(numero_busca)
            if not valido:
                st.error(f"❌ {erro}")
            else:
                tribunal, _ = datajud.identificar_tribunal(numero_busca)
                if tribunal:
                    with st.spinner(f"🔍 Consultando {tribunal}..."):
                        token = db.get_config('datajud_token', '')
                        dados_processo, erro = datajud.consultar_processo(numero_busca, token)
                    
                    if erro:
                        st.error(erro)
                    else:
                        dados = datajud.parsear_dados(dados_processo)
                        
                        # AUTO-FILL: Preencher session_state com dados do DataJud
                        st.session_state.form_numero_cnj = dados.get('numero', numero_busca)
                        st.session_state.form_classe = dados.get('classe', '')
                        st.session_state.form_orgao = dados.get('orgao_julgador', '')
                        st.session_state.form_comarca = dados.get('comarca', '')
                        st.session_state.form_valor_causa = float(dados.get('valor_causa', 0) or 0)
                        st.session_state.form_movimentos = dados.get('movimentos', [])
                        st.session_state.datajud_sucesso = True
                        
                        # Tentar converter data
                        data_aj = dados.get('data_ajuizamento', '')
                        if data_aj:
                            try:
                                if 'T' in data_aj:
                                    st.session_state.form_data_dist = datetime.fromisoformat(data_aj.replace('Z', '')).date()
                                else:
                                    st.session_state.form_data_dist = datetime.strptime(data_aj[:10], '%Y-%m-%d').date()
                            except:
                                st.session_state.form_data_dist = None
                        
                        # Mapear fase
                        fase_map = datajud.mapear_fase_processual(dados.get('classe', ''))
                        if fase_map in FASES_PROCESSUAIS:
                            st.session_state.form_fase_idx = FASES_PROCESSUAIS.index(fase_map)
                        
                        st.success(f"✅ Processo encontrado! Dados preenchidos automaticamente.")
                        st.rerun()
                else:
                    st.error("❌ Tribunal não suportado.")
        else:
            st.warning("Digite o número do processo para buscar.")
    
    # Mostrar resumo se dados foram importados
    if st.session_state.datajud_sucesso and st.session_state.form_numero_cnj:
        with st.container(border=True):
            st.markdown(f"📋 **Dados importados do DataJud:**")
            col1, col2 = st.columns(2)
            col1.caption(f"**Número:** {st.session_state.form_numero_cnj}")
            col1.caption(f"**Classe:** {st.session_state.form_classe}")
            col2.caption(f"**Órgão:** {st.session_state.form_orgao}")
            col2.caption(f"**Comarca:** {st.session_state.form_comarca}")
            if st.session_state.form_movimentos:
                st.caption(f"📄 {len(st.session_state.form_movimentos)} movimentações encontradas")
    
    st.divider()
    
    # ==================== FORMULÁRIO DE CADASTRO ====================
    st.markdown("#### 📝 Cadastrar Processo")
    
    # Buscar clientes
    df_clientes = db.sql_get_query("SELECT id, nome FROM clientes ORDER BY nome")
    lista_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
    
    if not lista_clientes:
        st.warning("⚠️ Nenhum cliente cadastrado no sistema.")
        if st.button("➕ Cadastrar Cliente Primeiro", type="primary"):
            st.session_state.next_nav = "Clientes (CRM)"
            st.rerun()
        return
    
    # Pre-fill client se veio de outra tela
    if 'pre_fill_client' in st.session_state:
        if st.session_state.pre_fill_client in lista_clientes:
            st.session_state.form_cliente_idx = lista_clientes.index(st.session_state.pre_fill_client)
        del st.session_state.pre_fill_client
    
    with st.form("form_cadastro_processo", clear_on_submit=False):
        # Cliente
        cliente = st.selectbox("👤 Cliente", lista_clientes, index=st.session_state.form_cliente_idx)
        
        # Número CNJ (auto-preenchido)
        numero_cnj = st.text_input(
            "📋 Número do Processo (CNJ)", 
            value=st.session_state.form_numero_cnj,
            help="Formato: 0000000-00.0000.0.00.0000 (20 dígitos)"
        )
        
        # Classe/Tipo de Ação (auto-preenchido)
        classe_acao = st.text_input(
            "⚖️ Classe / Tipo de Ação",
            value=st.session_state.form_classe,
            placeholder="Ex: Procedimento Comum Cível, Execução de Título, etc"
        )
        
        # Assunto (combina classe + órgão)
        assunto_default = ""
        if st.session_state.form_classe or st.session_state.form_orgao:
            assunto_default = f"Classe: {st.session_state.form_classe}\nÓrgão: {st.session_state.form_orgao}"
        
        assunto = st.text_area(
            "📄 Assunto / Detalhes",
            value=assunto_default,
            height=80,
            help="Descreva do que se trata o processo"
        )
        
        # Fase Processual
        fase = st.selectbox("📊 Fase Processual", FASES_PROCESSUAIS, index=st.session_state.form_fase_idx)
        
        # --- PRAZO FATAL (OPCIONAL) ---
        tem_prazo = st.checkbox("📅 Há prazo fatal definido?", value=False, help="Marque se houver prazo a cumprir")
        prazo_fatal = None
        if tem_prazo:
            prazo_fatal = st.date_input("📅 Prazo Fatal", value=vc, help="Data limite para cumprimento")
        
        # Responsável
        try:
            df_users = db.sql_get_query("SELECT nome FROM usuarios WHERE ativo=1")
            lista_resp = df_users['nome'].tolist() if not df_users.empty else ["Eduardo", "Sheila"]
        except:
            lista_resp = ["Eduardo", "Sheila"]
        responsavel = st.selectbox("👨‍💼 Responsável", lista_resp)
        
        # Detalhes opcionais
        st.markdown("---")
        st.markdown("**💰 Detalhes (Opcional)**")
        col_v1, col_v2 = st.columns(2)
        valor_causa = col_v1.number_input("Valor da Causa (R$)", value=st.session_state.form_valor_causa, min_value=0.0, step=100.0)
        data_dist = col_v2.date_input("Data Distribuição", value=st.session_state.form_data_dist)
        
        # --- COMARCA (DROPDOWN INTELIGENTE) ---
        st.markdown("**📍 Comarca**")
        
        # Tentar mapear valor do DataJud para a lista
        comarca_datajud = st.session_state.form_comarca.strip().title() if st.session_state.form_comarca else ""
        
        # Verificar se comarca do DataJud está na lista prioritária
        comarca_idx = 0  # Default: Maricá
        comarca_outra = ""
        if comarca_datajud:
            # Tentar match exato ou parcial
            comarca_encontrada = False
            for i, c in enumerate(COMARCAS_RJ[:-1]):  # Excluir "Outra" do match
                if comarca_datajud.lower() in c.lower() or c.lower() in comarca_datajud.lower():
                    comarca_idx = i
                    comarca_encontrada = True
                    break
            
            if not comarca_encontrada:
                # Não está na lista, selecionar "Outra" e preencher campo
                comarca_idx = len(COMARCAS_RJ) - 1  # Index de "Outra"
                comarca_outra = comarca_datajud
        
        comarca_sel = st.selectbox("Comarca", COMARCAS_RJ, index=comarca_idx, help="Comarcas prioritárias da região. Selecione 'Outra' para digitar.")
        
        # Campo de texto livre se "Outra" for selecionada
        if comarca_sel == "Outra":
            comarca = st.text_input("📝 Digite a Comarca:", value=comarca_outra, placeholder="Ex: Petrópolis, Teresópolis...")
        else:
            comarca = comarca_sel
        
        # Parte contrária
        st.markdown("---")
        st.markdown("**⚖️ Parte Contrária (Opcional)**")
        cadastrar_parte = st.checkbox("Cadastrar parte contrária")
        nome_parte = ""
        tipo_parte = "Réu"
        cpf_parte = ""
        if cadastrar_parte:
            col_p1, col_p2 = st.columns(2)
            nome_parte = col_p1.text_input("Nome da Parte")
            tipo_parte = col_p2.selectbox("Tipo", ["Réu", "Autor", "Terceiro"])
            cpf_parte = st.text_input("CPF/CNPJ (opcional)")
        
        # ==================== BOTÃO SALVAR ====================
        submitted = st.form_submit_button("💾 Salvar Processo", type="primary", use_container_width=True)
        
        if submitted:
            # Proteção contra clique duplo
            if st.session_state.get('salvando_processo', False):
                st.warning("⚠️ Salvamento em andamento, aguarde...")
            elif not cliente:
                st.error("❌ Selecione um cliente.")
            elif not numero_cnj:
                st.error("❌ Digite o número do processo (CNJ).")
            elif not responsavel:
                st.error("❌ Selecione um responsável.")
            else:
                # Marcar que está salvando para evitar duplicação
                st.session_state['salvando_processo'] = True
                
                # Criar pasta no Drive (estrutura correta: Clientes/NomeCliente/NumeroProcesso)
                link_drive = None
                try:
                    service = gd.autenticar()
                    if service:
                        # 1. Encontrar pasta "Clientes"
                        pasta_clientes = gd.find_folder(service, "Clientes", gd.PASTA_ALVO_ID)
                        if pasta_clientes:
                            # 2. Encontrar pasta do cliente dentro de "Clientes"
                            pasta_cliente = gd.find_folder(service, cliente, pasta_clientes)
                            if pasta_cliente:
                                # 3. Criar pasta do processo dentro da pasta do cliente
                                pasta_processo = gd.create_folder(service, numero_cnj, pasta_cliente)
                                if pasta_processo:
                                    link_drive = f"https://drive.google.com/drive/folders/{pasta_processo}"
                                    st.toast("📂 Pasta do processo criada no Drive!")
                            else:
                                st.warning("⚠️ Pasta do cliente não encontrada no Drive")
                        else:
                            st.warning("⚠️ Pasta 'Clientes' não encontrada no Drive")
                except Exception as e:
                    st.warning(f"⚠️ Erro no Drive: {e}")
                
                # Preparar dados - MAPEAMENTO CORRETO
                dados_processo = {
                    "numero": numero_cnj,
                    "cliente_nome": cliente,
                    "acao": classe_acao,
                    "assunto": assunto,
                    "proximo_prazo": prazo_fatal,
                    "responsavel": responsavel,
                    "status": "Ativo",
                    "fase_processual": fase,
                    "link_drive": link_drive,
                    "valor_causa": valor_causa,
                    "data_distribuicao": data_dist,
                    "comarca": comarca
                }
                
                # FK do cliente
                if not df_clientes.empty:
                    try:
                        cliente_row = df_clientes[df_clientes['nome'] == cliente].iloc[0]
                        dados_processo['id_cliente'] = int(cliente_row['id'])
                    except:
                        pass
                
                # Salvar
                try:
                    processo_id = db.crud_insert("processos", dados_processo)
                    
                    if processo_id:
                        # Parte contrária
                        if cadastrar_parte and nome_parte:
                            try:
                                db.sql_run(
                                    "INSERT INTO partes_processo (id_processo, nome, tipo, cpf_cnpj) VALUES (?,?,?,?)",
                                    (processo_id, nome_parte, tipo_parte, cpf_parte)
                                )
                            except:
                                pass
                        
                        # Importar movimentações
                        if st.session_state.form_movimentos:
                            count = 0
                            for mov in st.session_state.form_movimentos:
                                try:
                                    data_mov = mov.get('data', '')[:10] if mov.get('data') else None
                                    if data_mov:
                                        desc = mov.get('descricao', 'Movimentação')
                                        compl = mov.get('complemento', '')
                                        if compl:
                                            desc += f" - {compl}"
                                        db.sql_run(
                                            "INSERT INTO andamentos (id_processo, data, descricao, responsavel) VALUES (?,?,?,?)",
                                            (processo_id, data_mov, desc, "DataJud")
                                        )
                                        count += 1
                                except:
                                    pass
                            if count > 0:
                                st.toast(f"📄 {count} movimentações importadas!")
                        
                        st.success("✅ Processo salvo com sucesso!")
                        if link_drive:
                            st.info(f"📂 [Abrir pasta no Drive]({link_drive})")
                        
                        # ==================== RESET COMPLETO ====================
                        for key in ['form_numero_cnj', 'form_classe', 'form_orgao', 'form_comarca', 
                                   'form_valor_causa', 'form_data_dist', 'form_cliente_idx', 
                                   'form_fase_idx', 'form_movimentos', 'datajud_sucesso',
                                   'datajud_importado', 'input_busca_cnj', 'salvando_processo']:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar processo.")
                        st.session_state['salvando_processo'] = False
                        
                except Exception as e:
                    st.error(f"❌ Erro crítico: {e}")
                    st.session_state['salvando_processo'] = False



def render_gerenciar_processos():
    # Carregar dados
    df = db.sql_get("processos")
    if df.empty:
        st.info("Nenhum processo cadastrado.")
        return

    # --- FILTROS ---
    with st.expander("🔍 Filtros e Visualização", expanded=True):
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        
        termo_busca = col_f1.text_input("Buscar (Cliente, Ação...)", placeholder="Digite para filtrar...")
        responsavel_filtro = col_f2.selectbox("Responsável", ["Todos"] + list(df['responsavel'].unique()) if 'responsavel' in df.columns else ["Todos"])
        
        # Toggle Visualização
        view_mode = col_f3.radio("Visualização", ["Lista / Cards", "Kanban"], horizontal=True, index=0, help="Lista é melhor para Mobile")

    # Aplicar Filtros
    df_filtered = df.copy()
    if termo_busca:
        termo = termo_busca.lower()
        df_filtered = df_filtered[
            df_filtered['cliente_nome'].str.lower().str.contains(termo, na=False) |
            df_filtered['numero'].astype(str).str.lower().str.contains(termo, na=False) |
            df_filtered['acao'].str.lower().str.contains(termo, na=False) |
            df_filtered['assunto'].str.lower().str.contains(termo, na=False)
        ]
    
    if responsavel_filtro != "Todos":
        df_filtered = df_filtered[df_filtered['responsavel'] == responsavel_filtro]
        
    # --- PAGINAÇÃO (Performance Mobile) ---
    total_items = len(df_filtered)
    ITEMS_PER_PAGE = 10 if view_mode == "Lista / Cards" else 50 # Kanban precisa de mais itens para ser útil
    
    if total_items > ITEMS_PER_PAGE:
        total_pages = (total_items - 1) // ITEMS_PER_PAGE + 1
        col_pag1, col_pag2 = st.columns([4, 1])
        with col_pag2:
            page = st.number_input(f"Página (Total {total_pages})", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        
        # Slice do dataframe para exibição
        df_display = df_filtered.iloc[start_idx:end_idx]
        st.caption(f"Mostrando {start_idx+1}-{min(end_idx, total_items)} de {total_items} processos.")
    else:
        df_display = df_filtered

    st.divider()

    # --- VISUALIZAÇÃO KANBAN (PC) ---
    if view_mode == "Kanban":
        st.markdown("### 📋 Quadro de Processos")
        
        # Check if we have data to show
        if df_filtered.empty:
            st.info("Nenhum processo encontrado com os filtros atuais.")
        else:
            # Usar constante filtrada para evitar colunas vazias demais se quiser, mas melhor mostrar todas
            cols = st.columns(len(FASES_PROCESSUAIS))
            
            # Garantir que fase_processual não seja nula
            df_filtered['fase_processual'] = df_filtered['fase_processual'].fillna("Em Andamento")
            
            for i, fase in enumerate(FASES_PROCESSUAIS):
                with cols[i]:
                    st.markdown(f"**{fase}**")
                    df_fase = df_display[df_display['fase_processual'] == fase]
                    st.caption(f"{len(df_fase)} itens")
                    
                    for idx, row in df_fase.iterrows():
                        render_process_card_kanban(row, FASES_PROCESSUAIS)

    # --- VISUALIZAÇÃO LISTA / CARDS (MOBILE FRIENDLY) ---
    else:
        st.markdown("### 📱 Lista de Processos (v2)")
        
        if df_display.empty:
            st.info("Nenhum processo encontrado.")
        else:
            for idx, row in df_display.iterrows():
                with st.container(border=True):
                    # Layout de Card Mobile
                    cta, ctb = st.columns([3, 1])
                    with cta:
                        st.markdown(f"**{row['cliente_nome']}**")
                        st.caption(f"📋 {row['numero'] if row.get('numero') else row['acao']}")
                        assunto_val = row.get('assunto') if pd.notna(row.get('assunto')) else None
                        if assunto_val:
                            st.text(f"{row['assunto'][:60]}...")
                            
                    with ctb:
                        farol = ut.calcular_farol(row['proximo_prazo'])
                        try:
                            data_prazo = datetime.strptime(row['proximo_prazo'], '%Y-%m-%d').strftime('%d/%m') if row['proximo_prazo'] else "-"
                        except (ValueError, TypeError):
                            data_prazo = "-"
                        st.markdown(f"**{farol}** {data_prazo}")
                        st.caption(f"{row.get('fase_processual', '-')}")
                    
                    # Botão para expandir/detalhes rápido (opcional, ou apenas ir para detalhes abaixo)
                    # Botões de Ação
                    # Botões de Ação - Layout Horizontal Robusto
                    st.divider()
                    col_det, col_del = st.columns(2)
                    
                    with col_det:
                         if st.button("👁️ Detalhes", key=f"btn_det_{row['id']}", use_container_width=True):
                             st.session_state['selected_process_id'] = row['id']
                             st.rerun()
                             
                    with col_del:
                        # Validação de permissão
                        if permissions.can_delete_processo():
                            with st.popover("🗑️ Excluir", use_container_width=True):
                                st.write("Tem certeza?")
                                if st.button("Confirmar Exclusão", key=f"del_list_{row['id']}", type="primary", use_container_width=True):
                                    db.crud_delete("processos", "id=?", (row['id'],), f"Processo {row['id']} excluído via Lista")
                                    st.success("Excluído!")
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.caption("🔒 Apenas advogados")

    st.divider()
    
    # --- DETALHES DO PROCESSO SELECIONADO ---
    
    # Seletor Principal para Detalhes (Permite busca também)
    st.markdown("### 📂 Detalhes e Gerenciamento")
    
    df['lbl'] = df['cliente_nome'] + " - " + df['numero'].fillna(df['acao'])
    
    # Tenta pré-selecionar se veio do clique no card
    idx_sel = 0
    if 'selected_process_id' in st.session_state:
        try:
            lbl_sel = df[df['id'] == st.session_state['selected_process_id']].iloc[0]['lbl']
            if lbl_sel in df['lbl'].values:
                idx_sel = list(df['lbl'].values).index(lbl_sel)
        except:
            pass
            
    sel_p = st.selectbox("Selecione o Processo para Editar/Visualizar:", df['lbl'].unique(), index=idx_sel)
    
    if sel_p:
        pid = int(df[df['lbl'] == sel_p].iloc[0]['id'])
        render_processo_detalhes(pid, df)

def render_process_card_kanban(row, fases):
    """Renderiza um card simples para o Kanban."""
    with st.container(border=True):
        st.markdown(f"**{row['cliente_nome']}**")
        st.caption(f"📋 {row['numero'] if row.get('numero') else row['acao']}")
        
        # Farol
        farol = ut.calcular_farol(row['proximo_prazo'])
        try:
            data_fmt = datetime.strptime(row['proximo_prazo'], '%Y-%m-%d').strftime('%d/%m') if row['proximo_prazo'] else "?"
        except (ValueError, TypeError):
            data_fmt = "?"
        st.caption(f"{farol} {data_fmt}")
        
        # Mover
        current_fase = row['fase_processual']
        try:
            curr_idx = fases.index(current_fase)
        except:
            curr_idx = 0
            
        # Ações: Mover e Excluir
        c_move, c_del = st.columns([4, 1])
        with c_move:
            nova_fase = st.selectbox(
                "Mover:", 
                fases, 
                index=curr_idx, 
                key=f"mv_{row['id']}", 
                label_visibility="collapsed"
            )
        
        with c_del:
            # Validação de permissão
            if permissions.can_delete_processo():
                with st.popover("🗑️", use_container_width=True):
                    st.caption("Confirmar?")
                    if st.button("Sim", key=f"del_kanban_{row['id']}", type="primary"):
                        db.crud_delete("processos", "id=?", (row['id'],), f"Processo {row['id']} excluído via Kanban")
                        st.toast("Processo excluído!")
                        st.rerun()
            else:
                st.caption("🔒")
        
        if nova_fase != current_fase:
            db.sql_run("UPDATE processos SET fase_processual=? WHERE id=?", (nova_fase, row['id']))
            st.toast(f"Processo movido para {nova_fase}")
            st.rerun()

def render_processo_detalhes(pid, df_all):
    processo_row = df_all[df_all['id'] == pid].iloc[0]
    
    # --- CABEÇALHO E AÇÕES ---
    c_info, c_action = st.columns([3, 1])
    
    with c_info:
        st.markdown(f"**Cliente:** {processo_row['cliente_nome']}")
        numero_proc = processo_row.get('numero') or processo_row.get('acao', '')
        st.markdown(f"**Nº Processo:** {numero_proc}")
        if processo_row.get('acao'):
            st.caption(f"**Ação:** {processo_row['acao']}")
        if processo_row.get('comarca'):
            st.markdown(f"**Comarca:** {processo_row['comarca']}")
    
    with c_action:
        # Botão ATUALIZAR E ANALISAR (IA)
        if st.button("🤖 Atualizar e Analisar", type="primary", use_container_width=True):
             with st.spinner("Consultando Tribunal e Inteligência Artificial..."):
                 token = db.get_config('datajud_token')
                 if not token:
                     st.error("Configure o Token DataJud em Administração.")
                 else:
                     # Usar 'numero' se existir, senão fallback para 'acao'
                     numero_cnj = processo_row.get('numero') or processo_row.get('acao', '')
                     res = datajud.atualizar_processo_ia(pid, numero_cnj, token)
                     if "erro" in res:
                         st.error(f"Erro: {res['erro']}")
                     else:
                         st.toast(f"✅ Concluído! {res['novos']} novos, {res['analisados']} analisados.")
                         st.rerun()

        # Botão EDITAR
        with st.popover("✏️ Editar"):
             with st.form(f"edit_proc_{pid}"):
                 # Campo número CNJ
                 numero_atual = processo_row.get('numero') or processo_row.get('acao', '')
                 novo_numero = st.text_input("Número do Processo (CNJ)", value=numero_atual,
                                            help="Formato: 0000000-00.0000.0.00.0000")
                 nova_acao = st.text_input("Tipo de Ação", value=processo_row.get('acao', ''),
                                          help="Ex: Procedimento Comum Cível, Execução, etc")
                 novo_resp = st.text_input("Responsável", value=processo_row.get('responsavel', ''))
                 
                 val_atual = processo_row.get('valor_causa', 0.0)
                 if pd.isna(val_atual): val_atual = 0.0
                 
                 # Editar Comarca
                 nova_comarca = st.text_input("Comarca", value=processo_row.get('comarca', ''))
                 
                 novo_valor = st.number_input("Valor da Causa (R$)", value=float(val_atual), step=100.0)
                 
                 idx_fase = 0
                 if processo_row.get('fase_processual') in FASES_PROCESSUAIS:
                     idx_fase = FASES_PROCESSUAIS.index(processo_row.get('fase_processual'))
                     
                 nova_fase_edit = st.selectbox("Fase", FASES_PROCESSUAIS, index=idx_fase)
                 novo_assunto = st.text_area("Assunto", value=processo_row.get('assunto', ''))
                 
                 if st.form_submit_button("Salvar Alterações"):
                     db.sql_run("UPDATE processos SET numero=?, acao=?, responsavel=?, valor_causa=?, fase_processual=?, assunto=?, comarca=? WHERE id=?", 
                                (novo_numero, nova_acao, novo_resp, novo_valor, nova_fase_edit, novo_assunto, nova_comarca, pid))
                     st.toast("✅ Processo atualizado!")
                     st.rerun()

        # [EXCLUSÃO MOVIDA PARA O FINAL DA FUNÇÃO - DENTRO DE EXPANDER]

    # Botão para abrir pasta no Drive
    if 'link_drive' in processo_row and processo_row['link_drive']:
        st.markdown(f"📂 **Drive**: [Acessar Pasta no Google Drive]({processo_row['link_drive']})")
    
    # --- SINALIZAÇÃO DE INADIMPLÊNCIA ---
    try:
        id_cliente = processo_row.get('id_cliente')
        if id_cliente:
            hoje = datetime.now().strftime('%Y-%m-%d')
            inadim = db.sql_get_query("""
                SELECT COUNT(*) as qtd, SUM(valor) as total FROM financeiro 
                WHERE id_cliente = ? AND tipo = 'Entrada' AND status_pagamento = 'Pendente' 
                AND vencimento < ?
            """, (int(id_cliente), hoje))
            
            if not inadim.empty and inadim.iloc[0]['qtd'] > 0:
                qtd = int(inadim.iloc[0]['qtd'])
                total = inadim.iloc[0]['total'] or 0
                st.error(f"⚠️ **Cliente Inadimplente!** {qtd} parcela(s) vencida(s) - Total: R$ {total:,.2f}")
    except:
        pass
    
    t_d1, t_d2, t_d3, t_d4, t_d5 = st.tabs(["Timeline", "📅 Agenda", "Financeiro", "Link Público", "🧠 Estratégia (IA)"])
    
    # --- TAB TIMELINE ---
    with t_d1:
        st.caption("📌 Histórico de andamentos")
        
        hist = db.get_historico(pid)
        if not hist.empty:
            import json
            for idx, item in hist.iterrows():
                # Ícone baseado na urgência e gatilho financeiro
                icon = "🚨" if item.get('urgente') else "📄"
                if item.get('tipo') == 'DataJud': icon = "⚖️" if not item.get('urgente') else "🔥"
                
                # Verificar se tem gatilho financeiro na análise
                try:
                    analise_temp = json.loads(item.get('analise_ia', '{}')) if item.get('analise_ia') else {}
                    if analise_temp.get('gatilho_financeiro'):
                        icon = "💰"  # Dinheiro na mesa!
                except:
                    pass
                
                data_show = ut.formatar_data(item['data'])
                
                with st.expander(f"{icon} {data_show} - {item['descricao'][:80]}..."):
                    st.caption(f"Descrição completa: {item['descricao']}")
                    st.caption(f"Responsável: {item['responsavel'] or 'Sistema'}")
                    
                    # Exibir análise da IA se existir
                    if item.get('analise_ia'):
                        try:
                            analise = json.loads(item['analise_ia'])
                            
                            # Resumo técnico
                            st.info(f"🤖 **Análise IA:** {analise.get('resumo', 'Sem resumo')}")
                            
                            # Ação requerida
                            if analise.get('acao_requerida'):
                                st.error("⚠️ **Ação Requerida!** (Detectado pela IA)")
                            
                            # --- NOVOS CAMPOS DE ESTRATÉGIA ---
                            
                            # 1. Evolução Processual (Contexto)
                            if analise.get('evolucao_processual'):
                                st.markdown(f"**📉 Evolução:** {analise['evolucao_processual']}")
                                
                            # 2. Próxima Fase (Previsão)
                            if analise.get('proxima_fase'):
                                st.markdown(f"**🔮 Próxima Fase Provável:** {analise['proxima_fase']}")
                                
                            # 3. Recomendação do Advogado (Ação ou Espera)
                            if analise.get('recomendacao_advogado'):
                                rec = analise['recomendacao_advogado'].upper()
                                color_rec = "red" if "PETICIONAR" in rec or "CONTATAR" in rec else "green"
                                st.markdown(f"**💡 Recomendação:** <span style='color:{color_rec}; font-weight:bold'>{rec}</span>", unsafe_allow_html=True)
                            
                            st.divider()

                            # 💰 GATILHO FINANCEIRO
                            if analise.get('gatilho_financeiro'):
                                st.success(f"💰 **Oportunidade Financeira Detectada!** Tipo: {analise.get('tipo_gatilho', 'N/A')}")
                                if analise.get('sugestao_financeira'):
                                    st.warning(f"📊 **Sugestão:** {analise['sugestao_financeira']}")
                            
                            # 📱 MENSAGEM WHATSAPP
                            if analise.get('mensagem_cliente'):
                                st.markdown("---")
                                st.markdown("**📱 Mensagem pronta para WhatsApp:**")
                                
                                msg_whats = analise['mensagem_cliente']
                                # Substituindo st.code por st.text_area para permitir quebra de linha (visualização completa)
                                st.text_area(
                                    "Texto da Mensagem",
                                    value=msg_whats,
                                    height=150,
                                    label_visibility="collapsed",
                                    help="Copie o texto desta mensagem para enviar"
                                )
                                
                                # Botão para abrir WhatsApp Web
                                import urllib.parse
                                msg_encoded = urllib.parse.quote(msg_whats)
                                whats_link = f"https://wa.me/?text={msg_encoded}"
                                
                                st.markdown(f"""
                                <a href="{whats_link}" target="_blank" style="text-decoration: none;">
                                    <button style="
                                        background: linear-gradient(135deg, #25D366, #128C7E);
                                        color: white;
                                        border: none;
                                        padding: 10px 20px;
                                        border-radius: 8px;
                                        cursor: pointer;
                                        font-weight: bold;
                                        width: 100%;
                                        margin-top: 8px;
                                    ">
                                        📲 Enviar via WhatsApp Web
                                    </button>
                                </a>
                                """, unsafe_allow_html=True)
                                
                        except:
                            st.text(f"IA: {item['analise_ia']}")
                    else:
                        # --- ANÁLISE MANUAL (Botão) ---
                        if st.button("🔍 Analisar este Doc", key=f"btn_analisar_{item['id']}"):
                            with st.spinner("🤖 Lendo documento e analisando estratégia..."):
                                # Preparar contexto
                                p_num = processo_row.get('numero') or processo_row.get('acao', '')
                                p_acao = processo_row.get('acao', '')
                                contexto = f"Processo: {p_num} - Ação: {p_acao}"
                                nome_cliente = processo_row.get('cliente_nome', '')
                                
                                # Chamar IA
                                analise_manual = ai.analisar_andamento(item['descricao'], contexto, nome_cliente)
                                
                                # Salvar no Banco
                                analise_json_manual = json.dumps(analise_manual, ensure_ascii=False)
                                urgente_manual = 1 if analise_manual.get('urgente') else 0
                                
                                db.sql_run(
                                    "UPDATE andamentos SET analise_ia=?, urgente=? WHERE id=?", 
                                    (analise_json_manual, urgente_manual, item['id'])
                                )
                                
                                st.success("Análise concluída!")
                                time.sleep(0.5)
                                st.rerun()
        else:
            st.info("Nenhum andamento registrado.")
            
        with st.form(f"novo_andamento_{pid}"):
            st.markdown("#### Registrar Andamento")
            col_and1, col_and2 = st.columns([2, 1])
            with col_and1:
                dt = st.date_input("Data", value=datetime.now())
            with col_and2:

                # Tentar pegar fase atual ou default
                fase_atual = processo_row.get('fase_processual', 'Em Andamento')
                
                nova_fase_and = st.selectbox(
                    "Atualizar Fase?",
                    ["Manter atual"] + FASES_PROCESSUAIS,
                    help="Opcionalmente altere a fase do processo"
                )
            
            ds = st.text_area("Descrição da Ocorrência", height=80)
            
            if st.form_submit_button("Registrar Andamento", type="primary"):
                db.sql_run(
                    "INSERT INTO andamentos (id_processo,data,descricao,responsavel) VALUES (?,?,?,?)",
                    (pid, dt, ds, "Sys")
                )
                
                if nova_fase_and != "Manter atual":
                    db.sql_run("UPDATE processos SET fase_processual=? WHERE id=?", (nova_fase_and, pid))
                    st.toast(f"✅ Fase alterada para: {nova_fase_and}")
                
                st.success("Andamento registrado!")
                st.rerun()

    # --- TAB AGENDA ---
    with t_d2:
        st.caption("📅 Prazos e audiências vinculados a este processo")
        
        # Buscar eventos da agenda vinculados ao processo
        try:
            # FIX: Usar NÚMERO do processo (CNJ) para busca, e também buscar por ID
            numero_cnj = processo_row.get('numero', '')
            termo_busca = numero_cnj if numero_cnj else processo_row.get('acao', '')
            
            eventos = db.sql_get_query("""
                SELECT * FROM agenda 
                WHERE id_processo = ? 
                   OR descricao LIKE ? 
                   OR titulo LIKE ?
                ORDER BY data_evento
            """, (pid, f"%{termo_busca}%", f"%{termo_busca}%"))
            
            if eventos.empty:
                st.info("Nenhum prazo ou audiência vinculado a este processo.")
                st.caption(f"Dica: Crie eventos mencionando o número **{numero_cnj}** ou use o botão abaixo.")
            else:
                # Separar futuros e passados
                hoje = datetime.now().strftime('%Y-%m-%d')
                eventos_futuros = eventos[eventos['data_evento'] >= hoje]
                eventos_passados = eventos[eventos['data_evento'] < hoje]
                
                # Métricas
                col1, col2 = st.columns(2)
                col1.metric("📅 Próximos Eventos", len(eventos_futuros))
                col2.metric("✅ Eventos Passados", len(eventos_passados))
                
                st.divider()
                
                # Próximos eventos
                if not eventos_futuros.empty:
                    st.markdown("##### 📍 Próximos")
                    for idx, ev in eventos_futuros.iterrows():
                        tipo_icon = "⚖️" if ev.get('tipo') == 'audiencia' else "⏰"
                        data_fmt = datetime.strptime(ev['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')
                        hora = ev.get('hora', '')
                        
                        with st.container(border=True):
                            c_ev1, c_ev2 = st.columns([4, 1])
                            with c_ev1:
                                st.markdown(f"{tipo_icon} **{ev['titulo']}**")
                                st.caption(f"📅 {data_fmt} {hora}")
                                if ev.get('descricao'):
                                    st.caption(ev['descricao'])
                            with c_ev2:
                                if st.button("✏️", key=f"edit_ag_{ev['id']}"):
                                    st.toast("Edição na aba Agenda")
                
                # Eventos passados (colapsado)
                if not eventos_passados.empty:
                    with st.expander(f"📜 Histórico ({len(eventos_passados)} eventos)"):
                        for idx, ev in eventos_passados.iterrows():
                            data_fmt = datetime.strptime(ev['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')
                            st.caption(f"✓ {data_fmt} - {ev['titulo']}")
        except Exception as e:
            st.warning(f"Erro ao carregar agenda: {e}")
        
        # Botão para criar novo evento
        st.divider()
        if st.button("➕ Criar Prazo/Audiência", key=f"new_ag_{pid}"):
            st.session_state['agenda_pre_fill'] = {
                'id_processo': pid,
                'titulo': f"Prazo - {processo_row.get('numero') or processo_row.get('acao', '')}",
                'descricao': f"Processo: {processo_row.get('cliente_nome', '')}"
            }
            st.success("Vá para a Agenda para completar o cadastro!")

    # --- TAB FINANCEIRO ---
    with t_d3:
        st.caption("💰 Receitas e Despesas vinculadas")
        
        # 1. Listar Lançamentos Existentes
        try:
            fin_proc = db.sql_get_query("""
                SELECT * FROM financeiro 
                WHERE id_processo = ? 
                ORDER BY vencimento DESC
            """, (pid,))
            
            if not fin_proc.empty:
                # Métricas Rápidas
                total_entrada = fin_proc[fin_proc['tipo'] == 'Entrada']['valor'].sum()
                total_saida = fin_proc[fin_proc['tipo'] == 'Saída']['valor'].sum()
                saldo_proc = total_entrada - total_saida
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", ut.formatar_moeda(total_entrada))
                c2.metric("Despesas", ut.formatar_moeda(total_saida))
                c3.metric("Saldo do Processo", ut.formatar_moeda(saldo_proc), delta_color="normal")
                
                st.divider()
                
                # Lista Simples
                for idx, lan in fin_proc.iterrows():
                    icon = "💰" if lan['tipo'] == "Entrada" else "💸"
                    cor_valor = "green" if lan['tipo'] == "Entrada" else "red"
                    try:
                        venc_fmt = datetime.strptime(lan['vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        venc_fmt = lan['vencimento']
                        
                    with st.container(border=True):
                        cl1, cl2, cl3 = st.columns([3, 1, 1])
                        with cl1:
                            st.markdown(f"**{icon} {lan['descricao']}**")
                            st.caption(f"{lan['categoria']} | Status: {lan['status_pagamento']}")
                        with cl2:
                            st.markdown(f"**{venc_fmt}**")
                        with cl3:
                            st.markdown(f":{cor_valor}[**R$ {lan['valor']:,.2f}**]")
            else:
                st.info("Nenhum lançamento financeiro vinculado a este processo.")
                
        except Exception as e:
            st.error(f"Erro ao carregar financeiro: {e}")
            
        st.divider()
        st.markdown("##### 🆕 Novo Lançamento")
        if st.button("💰 Lançar Despesa/Honorário", use_container_width=True, key=f"fin_btn_{pid}"):
            st.session_state['financeiro_pre_fill'] = {
                'id_processo': pid,
                'cliente_nome': processo_row['cliente_nome'],
                'descricao': f"Ref. Proc: {processo_row.get('numero') or processo_row.get('acao', '')}"
            }
            st.success("Dados pré-carregados! Vá para o menu Financeiro.")

    # --- TAB LINK PÚBLICO ---
    with t_d4:
        st.markdown("#### 🔗 Link para o Cliente")
        
        # Buscar telefone do cliente para WhatsApp
        cliente_telefone = None
        try:
            cliente_info = db.sql_get_query("SELECT telefone FROM clientes WHERE nome = ?", (processo_row['cliente_nome'],))
            if not cliente_info.empty:
                cliente_telefone = cliente_info.iloc[0].get('telefone', '')
        except:
            pass
        
        col_tk1, col_tk2 = st.columns([2, 1])
        with col_tk1:
            dias = st.number_input("Dias de Validade", value=30, min_value=1, max_value=365, key=f"dv_{pid}")
        with col_tk2:
            if st.button("Gerar Link", type="primary", key=f"gl_{pid}"):
                token = tm.gerar_token_publico(pid, dias)
                if token:
                    url_base = db.get_config('url_sistema', 'http://localhost:8501')
                    link = f"{url_base}/?token={token}"
                    st.session_state[f'last_link_{pid}'] = link
                    st.rerun()

        # Mostrar link gerado com opções de compartilhamento
        if f'last_link_{pid}' in st.session_state:
            link = st.session_state[f'last_link_{pid}']
            st.success("✅ Link Gerado!")
            st.code(link)
            
            # Botões de compartilhamento
            col_copy, col_whats = st.columns(2)
            with col_copy:
                st.warning("⚠️ Copie agora. Este link permite acesso de leitura aos andamentos.")
            
            with col_whats:
                # Mensagem para WhatsApp
                numero_proc = processo_row.get('numero') or processo_row.get('acao', '')
                mensagem = f"Olá! Segue o link para acompanhar seu processo:\n\n📋 *Nº {numero_proc}*\n\n🔗 {link}\n\n_Link gerado pelo escritório Lopes & Ribeiro_"
                mensagem_encoded = mensagem.replace(" ", "%20").replace("\n", "%0A").replace("*", "").replace("_", "")
                
                # Se tiver telefone, pré-preencher
                if cliente_telefone:
                    telefone_limpo = ''.join(filter(str.isdigit, cliente_telefone))
                    if not telefone_limpo.startswith('55'):
                        telefone_limpo = '55' + telefone_limpo
                    whatsapp_url = f"https://wa.me/{telefone_limpo}?text={mensagem_encoded}"
                else:
                    whatsapp_url = f"https://wa.me/?text={mensagem_encoded}"
                
                st.markdown(f"""
                    <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: #25D366;
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            border-radius: 8px;
                            cursor: pointer;
                            width: 100%;
                            font-size: 14px;
                        ">
                            📱 Enviar via WhatsApp
                        </button>
                    </a>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Listar links ativos (apenas ativos)
        st.markdown("##### 📋 Links Ativos")
        tokens = tm.listar_tokens_processo(pid)
        tokens_ativos = [t for t in tokens if t.get('ativo')]
        
        if tokens_ativos:
            for t in tokens_ativos:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    
                    # Info do token
                    try:
                        data_exp = t['data_expiracao'][:10]
                        data_fmt = datetime.strptime(data_exp, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        data_fmt = t['data_expiracao'][:10]
                    
                    c1.caption(f"🔑 Token: ...{t['token'][-10:]}")
                    c1.caption(f"📅 Expira: {data_fmt} | 👁️ Acessos: {t['acessos']}")
                    
                    # Botão WhatsApp para reenviar
                    with c2:
                        url_base = db.get_config('url_sistema', 'http://localhost:8501')
                        link_token = f"{url_base}/?token={t['token']}"
                        numero_proc = processo_row.get('numero') or processo_row.get('acao', '')
                        msg = f"Olá! Segue o link para acompanhar seu processo:\n\n📋 Nº {numero_proc}\n\n🔗 {link_token}"
                        msg_enc = msg.replace(" ", "%20").replace("\n", "%0A")
                        
                        if cliente_telefone:
                            tel_limpo = '55' + ''.join(filter(str.isdigit, cliente_telefone))
                            wa_url = f"https://wa.me/{tel_limpo}?text={msg_enc}"
                        else:
                            wa_url = f"https://wa.me/?text={msg_enc}"
                        
                        st.link_button("📱 ReEnviar", wa_url, use_container_width=True)
                    
                    # Botão Excluir
                    with c3:
                        if st.button("🗑️ Excluir", key=f"del_tk_{t['id']}", type="secondary"):
                            tm.excluir_token_publico(t['token'])
                            st.toast("✅ Link excluído!")
                            if f'last_link_{pid}' in st.session_state:
                                del st.session_state[f'last_link_{pid}']
                            st.rerun()
        else:
            st.info("Nenhum link ativo para este processo.")

    # --- TAB ESTRATÉGIA (IA) ---
    with t_d5:
        render_tab_estrategia(pid, processo_row)
    
    # ==================== ZONA DE PERIGO - EXCLUSÃO (MOBILE FRIENDLY) ====================
    st.markdown("---")
    with st.expander("🔴 Zona de Perigo / Excluir Processo", expanded=False):
        st.markdown("""
        **Atenção:** A exclusão do processo é uma ação **irreversível**.
        
        Serão removidos permanentemente:
        - ⚖️ O processo e seus dados
        - 📄 Todos os andamentos registrados
        - 💰 Vínculos financeiros
        - 📅 Eventos de agenda vinculados
        """)
        
        if st.button("🗑️ Excluir este Processo", type="primary", key=f"btn_excluir_processo_{pid}"):
            st.session_state[f'abrir_dialog_exclusao_{pid}'] = True
            st.rerun()
    
    # Dialog de confirmação (abre como modal)
    @st.dialog("⚠️ Confirmar Exclusão")
    def dialog_confirmar_exclusao(proc_id, proc_numero):
        st.markdown("### Tem certeza?")
        st.error("Esta ação é **irreversível** e apagará todos os vínculos (andamentos, financeiro, agenda).", icon="🚨")
        st.markdown(f"**Processo:** {proc_numero}")
        
        col1, col2 = st.columns(2)
        if col1.button("💥 Sim, Excluir Definitivamente", type="primary", use_container_width=True):
            db.crud_delete("processos", "id=?", (proc_id,), f"Processo {proc_id} excluído")
            st.success("✅ Processo excluído com sucesso!")
            if 'selected_process_id' in st.session_state:
                del st.session_state['selected_process_id']
            if f'abrir_dialog_exclusao_{proc_id}' in st.session_state:
                del st.session_state[f'abrir_dialog_exclusao_{proc_id}']
            time.sleep(1)
            st.rerun()
        
        if col2.button("❌ Cancelar", use_container_width=True):
            if f'abrir_dialog_exclusao_{proc_id}' in st.session_state:
                del st.session_state[f'abrir_dialog_exclusao_{proc_id}']
            st.rerun()
    
    # Verificar se deve abrir o dialog
    if st.session_state.get(f'abrir_dialog_exclusao_{pid}', False):
        numero_proc = processo_row.get('numero') or processo_row.get('acao', 'N/A')
        dialog_confirmar_exclusao(pid, numero_proc)

def render_tab_estrategia(pid, processo_row):
    st.markdown("#### 🧠 Análise Estratégica Completa")
    st.caption("Parecer consolidado (estratégia, riscos, financeiro e mensagem ao cliente)")
    
    # Verificar se já existe análise em cache na sessão
    cache_key = f'analise_completa_{pid}'
    
    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        if st.button("🔎 Carregar Análise", type="primary", key=f"btn_load_{pid}"):
            with st.spinner("Carregando análise (usando cache se disponível)..."):
                hist = db.get_historico(pid)
                hist_list = hist.to_dict('records') if not hist.empty else []
                proc_dict = processo_row.to_dict()
                
                # Chamar nova função consolidada (usa cache automaticamente)
                res = ai.analisar_processo_completo(pid, proc_dict, hist_list, force_refresh=False)
                
                if "erro" in res:
                    if res.get('erro') == "quota_exceeded":
                        st.warning("⏳ **Limite de requisições atingido.**")
                        st.info("Aguarde 1 minuto e tente novamente.")
                    else:
                        st.error(f"Erro: {res['erro']}")
                else:
                    st.session_state[cache_key] = res
                    if res.get('from_cache'):
                        st.success(f"✅ Análise carregada do cache ({res.get('cache_age_hours', 0)}h atrás)")
                    else:
                        st.success("✅ Nova análise gerada e salva no cache!")
    
    with col_btn2:
        if st.button("🔄 Forçar Nova Análise", key=f"btn_force_{pid}"):
            with st.spinner("Gerando nova análise (ignora cache)..."):
                hist = db.get_historico(pid)
                hist_list = hist.to_dict('records') if not hist.empty else []
                proc_dict = processo_row.to_dict()
                
                # Forçar nova análise
                res = ai.analisar_processo_completo(pid, proc_dict, hist_list, force_refresh=True)
                
                if "erro" in res:
                    if res.get('erro') == "quota_exceeded":
                        st.warning("⏳ Limite atingido. Aguarde 1 minuto.")
                    else:
                        st.error(f"Erro: {res['erro']}")
                else:
                    st.session_state[cache_key] = res
                    st.success("✅ Nova análise gerada!")
    
    # Exibir resultado se existir
    if cache_key in st.session_state:
        res = st.session_state[cache_key]
        
        st.divider()
        
        # Indicador de Cache
        if res.get('from_cache'):
            st.caption(f"📦 Cache: Análise de {res.get('cache_age_hours', 0)}h atrás")
        
        # RESUMO EXECUTIVO
        if res.get('resumo_executivo'):
            st.info(f"📋 **Resumo:** {res['resumo_executivo']}")
        
        # 1. Probabilidade de Êxito
        prob = res.get('probabilidade_exito', 'Incerta')
        cor_prob = "gray"
        if "Alta" in str(prob): cor_prob = "green"
        elif "Média" in str(prob): cor_prob = "orange"
        elif "Baixa" in str(prob): cor_prob = "red"
        
        c1, c2 = st.columns([1, 2])
        c1.markdown("**Probabilidade de Êxito:**")
        c1.markdown(f"<h3 style='color: {cor_prob};'>{prob}</h3>", unsafe_allow_html=True)
        c2.info(f"💡 {res.get('justificativa_exito', 'Sem justificativa')}")
        
        # 2. Fase Processual
        st.markdown(f"**📍 Fase Real:** {res.get('analise_fase', 'Não identificado')}")
        
        col_a, col_b = st.columns(2)
        
        # 3. Próximos Passos
        with col_a:
            st.markdown("##### 👣 Próximos Passos")
            passos = res.get('proximos_passos') or res.get('proximos_passos_sugeridos', [])
            if passos:
                for p in passos:
                    st.markdown(f"- {p}")
            else:
                st.caption("Nenhuma sugestão específica.")
                
        # 4. Riscos
        with col_b:
            st.markdown("##### ⚠️ Riscos")
            riscos = res.get('riscos') or res.get('riscos_alertas', [])
            if riscos:
                for r in riscos:
                    st.markdown(f"- {r}")
            else:
                st.caption("Nenhum risco detectado.")
        
        st.divider()
        
        # 5. Oportunidade Financeira
        if res.get('oportunidade_financeira'):
            st.markdown("##### 💰 Oportunidade Financeira")
            tipo_op = res.get('tipo_oportunidade', 'nenhum')
            sug_fin = res.get('sugestao_financeira', '')
            st.warning(f"🔔 **{tipo_op.upper()}:** {sug_fin}")
        
        # 6. Mensagem para Cliente (WhatsApp-ready)
        if res.get('mensagem_cliente'):
            st.markdown("##### 📱 Mensagem para o Cliente")
            msg_cliente = res['mensagem_cliente']
            st.text_area("Copie e envie:", value=msg_cliente, height=80, key=f"msg_{pid}")
            
            # Botão WhatsApp
            tel_cliente = processo_row.get('cliente_telefone', '')
            if not tel_cliente:
                try:
                    cli_info = db.sql_get_query("SELECT telefone FROM clientes WHERE nome=?", (processo_row['cliente_nome'],))
                    if not cli_info.empty:
                        tel_cliente = cli_info.iloc[0].get('telefone', '')
                except:
                    pass
            
            msg_enc = msg_cliente.replace(" ", "%20").replace("\n", "%0A")
            if tel_cliente:
                tel_limpo = '55' + ''.join(filter(str.isdigit, str(tel_cliente)))
                wa_url = f"https://wa.me/{tel_limpo}?text={msg_enc}"
            else:
                wa_url = f"https://wa.me/?text={msg_enc}"
            
            st.link_button("📱 Enviar via WhatsApp", wa_url)
        
        # Tom da análise - indicador visual
        tom = res.get('tom', 'Informativo')
        urgencia = res.get('urgencia', 3)
        sug_fin = res.get('sugestao_financeira', '')
        
        if urgencia >= 4 or 'Urgente' in str(tom):
            if sug_fin:
                st.warning(f"🔔 **Ação Recomendada:** {sug_fin}")
        elif sug_fin and not res.get('oportunidade_financeira'):
            st.info(f"💡 **Dica:** {sug_fin}")
            
        # Botão de Ação Financeira Rápida (Atalho)
        if sug_fin and ("honorário" in sug_fin.lower() or "sucumbência" in sug_fin.lower()):
            if st.button("💰 Lançar no Financeiro agora", key=f"btn_fin_ai_{pid}"):
                st.session_state['financeiro_pre_fill'] = {
                    'id_processo': pid,
                    'cliente_nome': processo_row['cliente_nome'],
                    'descricao': f"Sugerido por IA: {sug_fin[:50]}..."
                }
                st.session_state.next_nav = "Financeiro"
                st.rerun()

