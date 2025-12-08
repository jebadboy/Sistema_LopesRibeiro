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

# --- CONSTANTES ---
FASES_PROCESSUAIS = ["A Ajuizar", "Aguardando Liminar", "Audiência Marcada", "Sentença", "Arquivado", "Em Andamento", "Suspenso"]

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
    st.markdown("#### 🧠 Calculadora de Prazos")
    
    with st.expander("Calculadora de Prazos", expanded=False):
        c1, c2, c3 = st.columns(3)
        dp = c1.date_input("Data da Publicação")
        di = c2.number_input("Dias de Prazo", min_value=1, value=15)
        rg = c3.selectbox("Regra de Contagem", ["Dias Úteis", "Corridos"])
        
        vc = ut.calc_venc(dp, di, rg)
        
        st.info(f"📅 Data Fatal: **{vc.strftime('%d/%m/%Y')}**")
    
    st.divider()
    
    # Busca DataJud
    with st.expander("🔎 Buscar no DataJud (Autopreenchimento)", expanded=True):
        datajud_ui.render_busca_datajud()
    
    st.divider()
    st.markdown("#### Cadastrar Processo")
    
    # --- LÓGICA DE AUTOPREENCHIMENTO DO DATAJUD ---
    defaults = {
        'cliente': None,
        'acao': '',
        'fase': 'A Ajuizar',
        'assunto': '',
        'valor_causa': 0.0,
        'data_distribuicao': None,
        'comarca': '',
        'parte_contraria': None
    }
    
    if 'datajud_importado' in st.session_state:
        dados_dj = st.session_state['datajud_importado']
        defaults['cliente'] = dados_dj.get('cliente')
        defaults['acao'] = dados_dj.get('numero')
        defaults['fase'] = dados_dj.get('fase', 'Em Andamento')
        defaults['assunto'] = f"Classe: {dados_dj.get('classe','')}\nÓrgão: {dados_dj.get('orgao','')}"
        defaults['valor_causa'] = dados_dj.get('valor_causa', 0.0)
        defaults['data_distribuicao'] = dados_dj.get('data_distribuicao')
        defaults['comarca'] = dados_dj.get('comarca', '')
        defaults['parte_contraria'] = dados_dj.get('parte_contraria_sugerida')

    with st.form("novo_processo_form"):
        # Otimização: Buscar apenas id e nome
        df_clientes = db.sql_get_query("SELECT id, nome FROM clientes ORDER BY nome")
        lista_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
        
        # Tentar selecionar o cliente importado
        idx_cli = 0
        
        # 1. Prioridade: Pre-fill de outras telas (ex: CRM)
        if 'pre_fill_client' in st.session_state:
            if st.session_state.pre_fill_client in lista_clientes:
                idx_cli = lista_clientes.index(st.session_state.pre_fill_client)
            del st.session_state.pre_fill_client
        # 2. Prioridade: DataJud
        elif defaults['cliente'] and defaults['cliente'] in lista_clientes:
             idx_cli = lista_clientes.index(defaults['cliente'])
            
        cl = st.selectbox("Cliente", lista_clientes, index=idx_cli)
        ac = st.text_input("Ação / Número do Processo", value=defaults['acao'])
        
        # Campo Assunto
        assunto = st.text_area(
            "📋 Assunto / Do que se trata",
            value=defaults['assunto'],
            placeholder="Ex: Ação de Cobrança, Indenização por Danos Morais, Revisão Contratual...",
            help="Descreva brevemente o objeto da ação",
            height=80
        )
        
        c_fase, c_prazo = st.columns(2)
        # Tentar mapear fase do DataJud para as opções locais
        idx_fase = 0
        if defaults['fase'] in FASES_PROCESSUAIS:
            idx_fase = FASES_PROCESSUAIS.index(defaults['fase'])
        elif defaults['fase'] == 'Baixado': 
            try:
                idx_fase = FASES_PROCESSUAIS.index('Arquivado')
            except:
                idx_fase = 0
            
        fase = c_fase.selectbox("Fase Inicial", FASES_PROCESSUAIS, index=idx_fase)
        
        # Se 'vc' (da calculadora) for muito no passado ou default, user ajusta.
        pz = c_prazo.date_input("Prazo Fatal", value=vc)
        
        # Buscar responsáveis do banco se tabela de usuarios existir, senão hardcoded
        # lista_res = ["Eduardo", "Sheila"] # Fallback
        # Tentar buscar usuarios admin/adv
        try:
            df_users = db.sql_get_query("SELECT nome FROM usuarios WHERE ativo=1")
            if not df_users.empty:
                lista_res = df_users['nome'].tolist()
            else:
                lista_res = ["Eduardo", "Sheila"]
        except:
             lista_res = ["Eduardo", "Sheila"]

        resp = st.selectbox("Responsável", lista_res)
        
        # Campos extras (Valor Causa / Data Importados)
        st.markdown("#### 💰 Detalhes (Opcional)")
        col_v1, col_v2 = st.columns(2)
        v_causa = col_v1.number_input("Valor da Causa (R$)", value=float(defaults['valor_causa']), step=100.0, min_value=0.0, format="%.2f")
        d_dist = col_v2.date_input("Data Distribuição", value=defaults['data_distribuicao'] if defaults['data_distribuicao'] else None)
        comarca_input = st.text_input("Comarca", value=defaults['comarca'])
        
        st.markdown("---")
        st.markdown("#### ⚖️ Parte Contrária (Opcional)")
        
        pre_marca_parte = True if defaults['parte_contraria'] else False
        cadastrar_parte = st.checkbox("Cadastrar parte contrária (Réu/Autor/Terceiro)", value=pre_marca_parte)
        
        nome_parte = defaults['parte_contraria']['nome'] if defaults['parte_contraria'] else None
        tipo_parte_sug = defaults['parte_contraria']['tipo'] if defaults['parte_contraria'] else None
        cpf_parte = defaults['parte_contraria']['cpf_cnpj'] if defaults['parte_contraria'] else None
        
        # Mapeamento API -> Sistema
        idx_tipo_parte = 0
        if tipo_parte_sug:
            if tipo_parte_sug == 'AUTOR': idx_tipo_parte = 1
            elif tipo_parte_sug == 'REU': idx_tipo_parte = 0
            elif tipo_parte_sug == 'TERCEIRO': idx_tipo_parte = 2
        
        if cadastrar_parte:
            col1, col2 = st.columns(2)
            nome_parte = col1.text_input("Nome da Parte Contrária", value=nome_parte if nome_parte else "")
            tipo_parte = col2.selectbox("Tipo", ["Réu", "Autor", "Terceiro"], index=idx_tipo_parte)
            cpf_parte = st.text_input("CPF/CNPJ (opcional)", value=cpf_parte if cpf_parte else "")
        
        if st.form_submit_button("Salvar Processo", type="primary"):
            if not cl or not ac:
                st.error("Cliente e Ação são obrigatórios.")
            else:
                # Criar pasta no Drive
                link_drive = None
                try:
                    service = gd.autenticar()
                    if service:
                        # Buscar pasta do cliente
                        pasta_cliente = gd.find_folder(service, cl, gd.PASTA_ALVO_ID)
                        
                        if pasta_cliente:
                            # Criar subpasta do processo
                            pasta_processo = gd.create_folder(service, ac, pasta_cliente)
                            
                            if pasta_processo:
                                link_drive = f"https://drive.google.com/drive/folders/{pasta_processo}"
                                st.toast("📂 Pasta criada no Drive!")
                        else:
                            st.warning(f"⚠️ Pasta do cliente '{cl}' não encontrada no Drive. Pasta do processo não criada.")
                    else:
                        st.warning("⚠️ Serviço do Drive não autenticado. Pasta não criada.")
                except Exception as e:
                    st.warning(f"⚠️ Erro ao criar pasta no Drive: {e}")
                    # Não vamos impedir o salvamento do processo por erro no drive

                
                # Salvar processo via crud_insert
                dados_processo = {
                    "cliente_nome": cl,
                    "acao": ac,
                    "assunto": assunto,
                    "proximo_prazo": pz,
                    "responsavel": resp,
                    "status": "Ativo",
                    "fase_processual": fase,
                    "link_drive": link_drive,
                    "valor_causa": v_causa,
                    "data_distribuicao": d_dist,
                    "comarca": comarca_input
                }
                
                # Buscar ID do cliente para FK (opcional mas recomendado)
                if not df_clientes.empty and cl:
                    try:
                        cliente_row = df_clientes[df_clientes['nome'] == cl].iloc[0]
                        dados_processo['id_cliente'] = int(cliente_row['id'])
                    except:
                        pass

                try:
                    processo_id = db.crud_insert("processos", dados_processo)
                    
                    if processo_id:
                        # Salvar parte contrária (se informada)
                        if cadastrar_parte and nome_parte:
                            try:
                                db.sql_run(
                                    "INSERT INTO partes_processo (id_processo, nome, tipo, cpf_cnpj) VALUES (?,?,?,?)",
                                    (processo_id, nome_parte, tipo_parte, cpf_parte)
                                )
                                st.toast(f"✅ Parte contrária cadastrada: {nome_parte}")
                            except Exception as e:
                                st.warning(f"Erro ao cadastrar parte: {e}")
                        
                        # IMPORTAR MOVIMENTAÇÕES DO DATAJUD (SE DISPONÍVEL)
                        qtd_moves = datajud_ui.importar_movimentacoes_datajud(processo_id)
                        if qtd_moves > 0:
                            st.success(f"✅ {qtd_moves} andamentos importados do DataJud!")
                        
                        st.success("✅ Processo salvo com sucesso!")
                        if link_drive:
                            st.info(f"📂 Pasta criada: [Abrir no Drive]({link_drive})")
                        
                        # Limpar cache ou forçar reload se necessário
                        # st.rerun() # Evita loop se o form limpar sozinho, mas as vezes preciso
                    else:
                        st.error("Erro ao salvar processo no banco de dados.")
                        
                except Exception as e:
                    st.error(f"Erro crítico ao salvar: {e}")

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
                        st.caption(f"{row['acao']}")
                        if row.get('assunto'):
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
                        with st.popover("🗑️ Excluir", use_container_width=True):
                            st.write("Tem certeza?")
                            if st.button("Confirmar Exclusão", key=f"del_list_{row['id']}", type="primary", use_container_width=True):
                                db.crud_delete("processos", "id=?", (row['id'],), f"Processo {row['id']} excluído via Lista")
                                st.success("Excluído!")
                                time.sleep(1)
                                st.rerun()

    st.divider()
    
    # --- DETALHES DO PROCESSO SELECIONADO ---
    
    # Seletor Principal para Detalhes (Permite busca também)
    st.markdown("### 📂 Detalhes e Gerenciamento")
    
    df['lbl'] = df['cliente_nome'] + " - " + df['acao']
    
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
        st.caption(f"{row['acao']}")
        
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
            with st.popover("🗑️", use_container_width=True):
                st.caption("Confirmar?")
                if st.button("Sim", key=f"del_kanban_{row['id']}", type="primary"):
                    db.crud_delete("processos", "id=?", (row['id'],), f"Processo {row['id']} excluído via Kanban")
                    st.toast("Processo excluído!")
                    st.rerun()
        
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
        st.markdown(f"**Ação/CNJ:** {processo_row['acao']}")
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
                     res = datajud.atualizar_processo_ia(pid, processo_row['acao'], token)
                     if "erro" in res:
                         st.error(f"Erro: {res['erro']}")
                     else:
                         st.toast(f"✅ Concluído! {res['novos']} novos, {res['analisados']} analisados.")
                         st.rerun()

        # Botão EDITAR
        with st.popover("✏️ Editar"):
             with st.form(f"edit_proc_{pid}"):
                 novo_numero = st.text_input("Ação / Número", value=processo_row.get('acao', ''))
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
                     db.sql_run("UPDATE processos SET acao=?, responsavel=?, valor_causa=?, fase_processual=?, assunto=?, comarca=? WHERE id=?", 
                                (novo_numero, novo_resp, novo_valor, nova_fase_edit, novo_assunto, nova_comarca, pid))
                     st.toast("✅ Processo atualizado!")
                     st.rerun()

        # Botão EXCLUIR PROCESSO
        with st.popover("🗑️ Excluir"):
            st.warning("Tem certeza? Isso apagará o processo e todos os seus vínculos.")
            if st.button("Confirmar Exclusão", type="primary", key=f"del_proc_{pid}"):
                db.crud_delete("processos", "id=?", (pid,), "Processo excluído")
                st.toast("Processo excluído com sucesso!")
                # Limpar seleção
                if 'selected_process_id' in st.session_state:
                    del st.session_state['selected_process_id']
                st.rerun()

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
                                st.code(msg_whats, language=None)
                                
                                # Botão para abrir WhatsApp Web (com mensagem pré-preenchida)
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
            numero_processo = processo_row.get('acao', '')
            eventos = db.sql_get_query("""
                SELECT * FROM agenda 
                WHERE (id_processo = ? OR titulo LIKE ? OR descricao LIKE ?)
                ORDER BY data_evento
            """, (pid, f"%{numero_processo}%", f"%{numero_processo}%"))
            
            if eventos.empty:
                st.info("Nenhum prazo ou audiência vinculado a este processo.")
                st.caption("Para vincular, crie eventos na Agenda mencionando o número do processo.")
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
                            st.markdown(f"{tipo_icon} **{ev['titulo']}**")
                            st.caption(f"📅 {data_fmt} {hora}")
                            if ev.get('descricao'):
                                st.caption(ev['descricao'][:100])
                
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
                'titulo': f"Prazo - {processo_row.get('acao', '')}",
                'descricao': f"Processo: {processo_row.get('cliente_nome', '')}"
            }
            st.success("Vá para a Agenda para completar o cadastro!")

    # --- TAB FINANCEIRO ---
    with t_d3:
        st.info("Atalho para lançamento rápido. Para gestão completa, use o menu Financeiro.")
        if st.button("💰 Lançar Despesa/Honorário", use_container_width=True, key=f"fin_btn_{pid}"):
            st.session_state['financeiro_pre_fill'] = {
                'id_processo': pid,
                'cliente_nome': processo_row['cliente_nome'],
                'descricao': f"Ref. Proc: {processo_row['acao']}"
            }
            st.success("Dados pré-carregados! Vá para o menu Financeiro.")

    # --- TAB LINK PÚBLICO ---
    with t_d4:
        st.markdown("#### 🔗 Link para o Cliente")
        col_tk1, col_tk2 = st.columns([2, 1])
        with col_tk1:
            dias = st.number_input("Dias de Validade", value=30, min_value=1, max_value=365, key=f"dv_{pid}")
        with col_tk2:
            if st.button("Gerar Link", type="primary", key=f"gl_{pid}"):
                token = tm.gerar_token_publico(pid, dias)
                if token:
                    # Ajuste a URL BASE conforme seu ambiente de produção
                    # Tentar detectar URL se possível, ou usar config
                    url_base = "http://localhost:8501" 
                    link = f"{url_base}/?token={token}"
                    st.session_state[f'last_link_{pid}'] = link
                    st.rerun()

        if f'last_link_{pid}' in st.session_state:
            st.success("Link Gerado!")
            st.code(st.session_state[f'last_link_{pid}'])
            st.warning("⚠️ Copie agora. Este link permite acesso de leitura aos andamentos deste processo.")
        
        # Listar ativos
        st.markdown("##### Links Ativos")
        tokens = tm.listar_tokens_processo(pid)
        if tokens:
            for t in tokens:
                c1, c2 = st.columns([3, 1])
                c1.text(f"...{t['token'][-8:]} (Expira: {t['data_expiracao']}) - Acessos: {t['acessos']}")
                if t['ativo']:
                    if c2.button("Revogar", key=f"rv_{t['id']}"):
                        tm.revogar_token_publico(t['token'])
                        st.rerun()
        else:
            st.caption("Nenhum link ativo.")

    # --- TAB ESTRATÉGIA (IA) ---
    with t_d5:
        render_tab_estrategia(pid, processo_row)

def render_tab_estrategia(pid, processo_row):
    st.markdown("#### 🧠 Análise Estratégica do Caso")
    st.caption("Parecer gerado por Inteligência Artificial simulando um Sócio Sênior.")
    
    # Verificar se já existe análise em cache (opcional, mas o cache da IA já cuida disso no backend)
    # Aqui vamos focar na UX
    
    if st.button("🔎 Gerar/Atualizar Parecer Estratégico", type="primary", key=f"btn_strat_{pid}"):
        with st.spinner("Analisando histórico, jurisprudência e estratégia..."):
            # Buscar histórico completo
            hist = db.get_historico(pid)
            # Converter para lista de dicts
            hist_list = hist.to_dict('records') if not hist.empty else []
            
            # Converter row para dict
            proc_dict = processo_row.to_dict()
            
            # Chamar IA
            res = ai.analisar_estrategia_completa(proc_dict, hist_list)
            
            if "erro" in res:
                st.error(f"Erro na análise: {res['erro']}")
            else:
                st.session_state[f'strat_res_{pid}'] = res
                st.success("Análise concluída!")
    
    # Exibir resultado se existir na sessão
    if f'strat_res_{pid}' in st.session_state:
        res = st.session_state[f'strat_res_{pid}']
        
        st.divider()
        
        # 1. Probabilidade de Êxito
        prob = res.get('probabilidade_exito', 'Incerta')
        cor_prob = "gray"
        if "Alta" in prob: cor_prob = "green"
        elif "Média" in prob: cor_prob = "orange"
        elif "Baixa" in prob: cor_prob = "red"
        
        c1, c2 = st.columns([1, 2])
        c1.markdown(f"**Probabilidade de Êxito:**")
        c1.markdown(f"<h3 style='color: {cor_prob};'>{prob}</h3>", unsafe_allow_html=True)
        
        c2.info(f"💡 **Justificativa:** {res.get('justificativa_exito', 'Sem justificativa')}")
        
        # 2. Análise de Fase
        st.markdown(f"**📍 Momento Processual Real:** {res.get('analise_fase', 'Não identificado')}")
        
        col_a, col_b = st.columns(2)
        
        # 3. Próximos Passos
        with col_a:
            st.markdown("##### 👣 Próximos Passos Sugeridos")
            passos = res.get('proximos_passos_sugeridos', [])
            if passos:
                for p in passos:
                    st.markdown(f"- {p}")
            else:
                st.caption("Nenhuma sugestão específica.")
                
        # 4. Riscos
        with col_b:
            st.markdown("##### ⚠️ Pontos de Atenção & Riscos")
            riscos = res.get('riscos_alertas', [])
            if riscos:
                for r in riscos:
                    st.markdown(f"- {r}")
            else:
                st.caption("Nenhum risco crítico detectado.")
        
        st.divider()
        
        # 5. Sugestão Financeira
        st.markdown("##### 💰 Oportunidade Financeira")
        tom = res.get('tom_sugestao', 'Informativo')
        msg_fin = res.get('sugestao_financeira', 'Sem sugestões financeiras.')
        
        if "Urgente" in tom:
            st.warning(f"🔔 **Ação Recomendada:** {msg_fin}")
        else:
            st.info(f"💡 **Dica:** {msg_fin}")
            
        # Botão de Ação Financeira Rápida (Atalho)
        if "honorário" in msg_fin.lower() or "sucumbência" in msg_fin.lower():
            if st.button("Lançar no Financeiro agora", key=f"btn_fin_ai_{pid}"):
                st.session_state['financeiro_pre_fill'] = {
                    'id_processo': pid,
                    'cliente_nome': processo_row['cliente_nome'],
                    'descricao': f"Sugerido por IA: {msg_fin[:30]}..."
                }
                st.session_state.next_nav = "Financeiro"
                st.rerun()

