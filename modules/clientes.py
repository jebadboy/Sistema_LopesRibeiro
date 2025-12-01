import streamlit as st
import database as db
import utils as ut
from datetime import datetime

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📂 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    # Tabs com design limpo
    t1, t2 = st.tabs(["📝 Novo Cadastro", "🔍 Base / Editar / Propostas"])
    
    # --- ABA 1: NOVO CADASTRO ---
    with t1:
        render_novo_cadastro()

    # --- ABA 2: GESTÃO ---
    with t2:
        render_gestao_clientes()

def render_novo_cadastro():
    st.markdown("### 🪪 Identificação")
    
    # Container com estilo card
    with st.container():
        # Seletor de Tipo de Pessoa
        tipo_pessoa = st.radio("Tipo de Pessoa", ["Física", "Jurídica"], horizontal=True, key="cad_tipo_pessoa")
        
        c1, c2, c3 = st.columns([3, 2, 1.5])
        c1.text_input("Nome Completo / Razão Social", key="cad_nome")
        
        label_doc = "CPF (Só Números)" if tipo_pessoa == "Física" else "CNPJ (Só Números)"
        c2.text_input(label_doc, key="cad_cpf_cnpj")
        
        c3.selectbox("Fase", ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"], key="cad_stt")
        
        c4, c5, c6 = st.columns(3)
        c4.text_input("E-mail", key="cad_email")
        c5.text_input("WhatsApp", key="cad_tel")
        c6.text_input("Fixo", key="cad_fixo")
        
        c7, c8 = st.columns(2)
        c7.text_input("Profissão / Ramo de Atividade", key="cad_prof")
        
        opcoes_ec = ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"]
        if tipo_pessoa == "Jurídica":
            opcoes_ec = ["N/A"]
            
        c8.selectbox("Estado Civil", opcoes_ec, key="cad_ec")

    st.markdown("### 📍 Endereço")
    with st.container():
        cc1, cc2 = st.columns([3, 1])
        cc1.text_input("CEP", key="cad_cep")
        cc2.button("🔍 Buscar CEP", on_click=buscar_cep_callback, use_container_width=True)
        
        st.text_input("Logradouro", key="cad_rua")
        e1, e2 = st.columns(2)
        e1.text_input("Número", key="cad_num")
        e2.text_input("Complemento", key="cad_comp")
        e3, e4, e5 = st.columns(3)
        e3.text_input("Bairro", key="cad_bairro")
        e4.text_input("Cidade", key="cad_cid")
        e5.text_input("UF", key="cad_uf")

    st.markdown("### 📂 Interno")
    with st.container():
        st.text_input("Link Drive", key="cad_drive", help="Cole o link da pasta do cliente no Google Drive")
        st.text_area("Obs", key="cad_obs")
        
        st.button("💾 SALVAR CLIENTE", type="primary", on_click=salvar_cliente_callback, use_container_width=True)

def render_gestao_clientes():
    df = db.sql_get("clientes", ordem="nome ASC")
    if df.empty:
        st.info("Nenhum cliente cadastrado.")
        return

    pesq = st.text_input("🔍 Buscar Cliente (Nome, CPF ou CNPJ):")
    if pesq:
        df = df[df['nome'].str.contains(pesq, case=False) | df['cpf_cnpj'].str.contains(pesq)]
    
    # Preparar DataFrame para visualização
    df_vis = df.copy()
    
    # Formatação segura de documentos
    df_vis['Documento'] = df_vis.apply(lambda x: ut.formatar_documento(x['cpf_cnpj']), axis=1)
    
    df_vis['Celular'] = df_vis['telefone'].apply(ut.formatar_celular)
    df_vis['Status'] = df_vis['status_cliente']
    
    # Adicionar coluna de link para o Drive
    df_vis['Drive'] = df_vis['link_drive'].astype(str).str.strip()
    # Converter vazios/nan para None para não gerar links quebrados
    df_vis.loc[df_vis['Drive'].isin(['', 'nan', 'None']), 'Drive'] = None

    opcoes = ["Selecione para Abrir..."] + df['nome'].tolist()
    sel = st.selectbox("Ficha do Cliente:", opcoes)
    
    if sel != "Selecione para Abrir...":
        dd = df[df['nome'] == sel].iloc[0]
        render_ficha_cliente(dd)
    
    st.markdown("### Base de Clientes")
    
    # Configuração das colunas para o Dataframe
    st.dataframe(
        df_vis[['nome', 'Documento', 'Celular', 'Status', 'Drive']], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Drive": st.column_config.LinkColumn(
                "Drive",
                help="Clique para abrir a pasta do Drive",
                display_text="📂 Abrir"
            )
        }
    )
    
    # Hack para tornar o ícone clicável na tabela (se o Streamlit suportar LinkColumn corretamente com dados do DF)
    # Caso contrário, o usuário pode copiar o link da ficha.

def render_ficha_cliente(dd):
    # Card de Cabeçalho
    tipo = dd.get('tipo_pessoa', 'Física')
    doc_formatado = ut.formatar_documento(dd['cpf_cnpj'], tipo)
    
    drive_link_html = ""
    if dd['link_drive']:
        drive_link_html = f"""<a href="{dd['link_drive']}" target="_blank" style="text-decoration: none; font-size: 1.2em;">📂 Abrir Pasta no Drive</a>"""

    st.markdown(f"""
    <div class="metric-card" style="border-left-color: var(--primary); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align_items: center;">
            <div class="metric-value">{dd['nome']}</div>
            <div>{drive_link_html}</div>
        </div>
        <div class="metric-label">Status: {dd['status_cliente']} | {tipo}: {doc_formatado}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # AÇÕES RÁPIDAS
    c_act1, c_act2 = st.columns(2)
    if c_act1.button("➕ Novo Processo", use_container_width=True):
        st.session_state.pre_fill_client = dd['nome']
        st.session_state.nav_selection = "Processos"
        st.rerun()
        
    if c_act2.button("💰 Novo Lançamento", use_container_width=True):
        st.session_state.pre_fill_client = dd['nome']
        st.session_state.nav_selection = "Financeiro"
        st.rerun()
    
    st.divider()
    
    # MODO EDIÇÃO COMPLETA
    with st.expander("✏️ Editar Dados Cadastrais", expanded=False):
        with st.form("edit_form"):
            c_e1, c_e2 = st.columns([3, 1])
            enm = c_e1.text_input("Nome / Razão Social", value=dd['nome'])
            etipo = c_e2.selectbox("Tipo", ["Física", "Jurídica"], index=0 if tipo == "Física" else 1)
            
            c_e3, c_e4 = st.columns(2)
            edoc = c_e3.text_input("CPF / CNPJ", value=dd['cpf_cnpj'])
            estt = c_e4.selectbox("Status", ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"], 
                              index=["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"].index(dd['status_cliente']))
            
            c_e5, c_e6, c_e7 = st.columns(3)
            eemail = c_e5.text_input("E-mail", value=dd['email'])
            etel = c_e6.text_input("Celular", value=dd['telefone'])
            efix = c_e7.text_input("Fixo", value=dd['telefone_fixo'])
            
            c_e8, c_e9 = st.columns(2)
            eprof = c_e8.text_input("Profissão / Ramo", value=dd['profissao'])
            eec = c_e9.text_input("Estado Civil", value=dd['estado_civil'])
            
            st.markdown("---")
            st.markdown("**Endereço**")
            
            ecep = st.text_input("CEP", value=dd['cep'])
            erua = st.text_input("Logradouro", value=dd['endereco'])
            
            c_end1, c_end2 = st.columns(2)
            enum = c_end1.text_input("Número", value=dd['numero_casa'])
            ecomp = c_end2.text_input("Complemento", value=dd['complemento'])
            
            c_end3, c_end4, c_end5 = st.columns(3)
            ebairro = c_end3.text_input("Bairro", value=dd['bairro'])
            ecid = c_end4.text_input("Cidade", value=dd['cidade'])
            euf = c_end5.text_input("UF", value=dd['estado'])
            
            st.markdown("---")
            edrive = st.text_input("Link Drive", value=dd['link_drive'])
            eobs = st.text_area("Observações", value=dd['obs'])
            
            if st.form_submit_button("Salvar Alterações", type="primary"):
                db.sql_run("""
                    UPDATE clientes SET 
                    nome=?, tipo_pessoa=?, cpf_cnpj=?, status_cliente=?, email=?, telefone=?, telefone_fixo=?, 
                    profissao=?, estado_civil=?, cep=?, endereco=?, numero_casa=?, complemento=?, 
                    bairro=?, cidade=?, estado=?, link_drive=?, obs=? 
                    WHERE id=?
                """, (enm, etipo, edoc, estt, eemail, etel, efix, eprof, eec, ecep, erua, enum, ecomp, ebairro, ecid, euf, edrive, eobs, int(dd['id'])))
                st.success("Dados atualizados com sucesso!")
                st.rerun()

    # MODO PROPOSTA
    with st.expander("💰 Proposta e Negociação", expanded=True):
        c_p1, c_p2 = st.columns(2)
        vp = c_p1.number_input("Valor Total (R$)", value=ut.safe_float(dd['proposta_valor']))
        ve = c_p2.number_input("Entrada (R$)", value=ut.safe_float(dd['proposta_entrada']))
        
        c_p3, c_p4 = st.columns(2)
        np_parc = c_p3.number_input("Parcelas", value=ut.safe_int(dd['proposta_parcelas']))
        
        pg_opts = ["PIX", "Dinheiro", "Cartão (TON)", "Parcelado Mensal", "% no Êxito", "Entrada + % Êxito"]
        pg_val = dd['proposta_pagamento']
        idx_pg = pg_opts.index(pg_val) if pg_val in pg_opts else 0
        pg = c_p4.selectbox("Pagamento", pg_opts, index=idx_pg)
        
        # Data de Pagamento (se parcelado)
        data_pag = None
        if pg == "Parcelado Mensal":
            val_data = dd.get('proposta_data_pagamento')
            if val_data:
                try:
                    val_data = datetime.strptime(val_data, '%Y-%m-%d').date()
                except:
                    val_data = datetime.now().date()
            else:
                val_data = datetime.now().date()
            data_pag = st.date_input("Vencimento 1ª Parcela", value=val_data, format="DD/MM/YYYY")
        
        ob = st.text_area("Objeto (Descrição)", value=dd['proposta_objeto'] if dd['proposta_objeto'] else "", key="txt_objeto")
        
        cb1, cb2 = st.columns(2)
        
        # Botão SALVAR e GERAR
        if cb1.button("💾 Salvar e Atualizar DOC", type="primary"):
            # 1. Salvar no Banco
            data_str = data_pag.strftime('%Y-%m-%d') if data_pag else None
            db.sql_run("UPDATE clientes SET proposta_valor=?, proposta_entrada=?, proposta_parcelas=?, proposta_pagamento=?, proposta_objeto=?, proposta_data_pagamento=? WHERE id=?", 
                       (vp, ve, np_parc, pg, ob, data_str, int(dd['id'])))
            
            # 2. Gerar Documento Atualizado
            doc_data = {
                'nome': dd['nome'], 
                'cpf_cnpj': dd['cpf_cnpj'],
                'telefone': dd['telefone'],
                'proposta_valor': vp, 
                'proposta_entrada': ve, 
                'proposta_parcelas': np_parc, 
                'proposta_objeto': ob, 
                'proposta_pagamento': pg,
                'proposta_data_pagamento': data_str
            }
            doc_bytes = ut.criar_doc("Proposta", doc_data)
            st.session_state['doc_proposta_bytes'] = doc_bytes
            st.session_state['doc_proposta_nome'] = f"Prop_{dd['nome']}.docx"
            
            st.success("Proposta salva e documento atualizado!")
            st.rerun()
            
        with cb2:
            # Botão de Download (Pega do Session State ou Gera do DB)
            # Botão de Download (Pega do Session State ou Gera do DB)
            doc_download = st.session_state.get('doc_proposta_bytes')
            nome_download = st.session_state.get('doc_proposta_nome', f"Prop_{dd['nome']}.docx")
            
            if not doc_download:
                # Se não tem no state, gera com o que tem no banco (dd)
                doc_data_db = {
                    'nome': dd['nome'], 
                    'cpf_cnpj': dd['cpf_cnpj'],
                    'telefone': dd['telefone'],
                    'proposta_valor': ut.safe_float(dd['proposta_valor']), 
                    'proposta_entrada': ut.safe_float(dd['proposta_entrada']), 
                    'proposta_parcelas': ut.safe_int(dd['proposta_parcelas']), 
                    'proposta_objeto': dd['proposta_objeto'] if dd['proposta_objeto'] else "", 
                    'proposta_pagamento': dd['proposta_pagamento']
                }
                doc_download = ut.criar_doc("Proposta", doc_data_db)
                st.caption("⚠️ Baixa a versão salva anteriormente.")
            
            st.download_button(
                "📄 Baixar DOC Proposta", 
                doc_download, 
                nome_download, 
                type="secondary"
            )

    # MODO DOCS FINAIS
    if dd['status_cliente'] == 'ATIVO':
        st.markdown("### 🖨️ Documentos Finais")
        
        with st.container(border=True):
            st.markdown("#### 📄 Procuração e Hipossuficiência")
            
            # --- PROCURAÇÃO ---
            with st.expander("Procuração", expanded=True):
                c_proc1, c_proc2 = st.columns([1, 2])
                
                # Opções
                pod_esp = c_proc1.checkbox("Incluir Poderes Especiais", value=True, help="Receber, dar quitação, transigir, etc.")
                
                # Botão Gerar
                if c_proc1.button("📄 Gerar Procuração (DOC)", key="btn_gerar_proc"):
                    dados_proc = dd.copy()
                    # Adicionar endereço completo se faltar
                    doc_bytes = ut.criar_doc("Procuracao", dados_proc, opcoes={'poderes_especiais': pod_esp})
                    st.download_button(
                        label="⬇️ Baixar Procuração",
                        data=doc_bytes,
                        file_name=f"Procuracao_{dd['nome']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="down_proc"
                    )
                
                # Link Drive
                link_proc_atual = dd.get('link_procuracao', '')
                novo_link_proc = c_proc2.text_input("Link Google Drive (Procuração)", value=link_proc_atual if link_proc_atual else "")
                
                c_act1, c_act2 = c_proc2.columns(2)
                if c_act1.button("Salvar Link Procuração"):
                    db.crud_update('clientes', {'link_procuracao': novo_link_proc}, 'id=?', (dd['id'],), 'Atualizar Link Procuração')
                    st.success("Link salvo!")
                    st.rerun()
                
                if link_proc_atual:
                    c_act2.link_button("📂 Abrir no Drive", link_proc_atual)

            # --- HIPOSSUFICIÊNCIA ---
            with st.expander("Declaração de Hipossuficiência", expanded=True):
                c_hip1, c_hip2 = st.columns([1, 2])
                
                # Botão Gerar
                if c_hip1.button("📄 Gerar Declaração (DOC)", key="btn_gerar_hipo"):
                    doc_bytes = ut.criar_doc("Hipossuficiencia", dd)
                    st.download_button(
                        label="⬇️ Baixar Declaração",
                        data=doc_bytes,
                        file_name=f"Hipossuficiencia_{dd['nome']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="down_hipo"
                    )
                
                # Link Drive
                link_hipo_atual = dd.get('link_hipossuficiencia', '')
                novo_link_hipo = c_hip2.text_input("Link Google Drive (Hipossuficiência)", value=link_hipo_atual if link_hipo_atual else "")
                
                c_act3, c_act4 = c_hip2.columns(2)
                if c_act3.button("Salvar Link Hipo"):
                    db.crud_update('clientes', {'link_hipossuficiencia': novo_link_hipo}, 'id=?', (dd['id'],), 'Atualizar Link Hipo')
                    st.success("Link salvo!")
                    st.rerun()
                
                if link_hipo_atual:
                    c_act4.link_button("📂 Abrir no Drive", link_hipo_atual)
            
            st.divider()
            
            d1, d2, d3 = st.columns(3)
            
            # Procuração com Opções
            with d1: 
                doc_proc = ut.criar_doc("Procuracao", dd, opcoes={'poderes_especiais': pod_esp})
                st.download_button("📄 Baixar Procuração", doc_proc, f"Procuracao_{dd['nome']}.docx", use_container_width=True)
            
            # Hipossuficiência
            with d2: 
                if just_grat:
                    doc_hipo = ut.criar_doc("Hipossuficiencia", dd)
                    st.download_button("📄 Baixar Hipossuf.", doc_hipo, f"Hipo_{dd['nome']}.docx", use_container_width=True)
                else:
                    st.caption("Hipossuficiência não selecionada")
            
            # Contrato
            with d3: 
                doc_cont = ut.criar_doc("Contrato", dd)
                st.download_button("📄 Baixar Contrato", doc_cont, f"Contrato_{dd['nome']}.docx", use_container_width=True)

    # HISTÓRICO FINANCEIRO
    with st.expander("💰 Histórico Financeiro"):
        df_fin = db.sql_get("financeiro")
        if not df_fin.empty:
            df_cli_fin = df_fin[df_fin['id_cliente'] == dd['id']].copy()
            if not df_cli_fin.empty:
                st.dataframe(
                    df_cli_fin[['data', 'tipo', 'descricao', 'valor', 'status_pagamento']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "valor": st.column_config.NumberColumn(format="R$ %.2f")
                    }
                )
                
                total_pago = df_cli_fin[(df_cli_fin['tipo'] == 'Entrada') & (df_cli_fin['status_pagamento'] == 'Pago')]['valor'].sum()
                st.metric("Total Pago pelo Cliente", f"R$ {total_pago:,.2f}")
            else:
                st.info("Nenhum lançamento financeiro vinculado a este cliente.")
        else:
            st.info("Nenhum lançamento financeiro no sistema.")

    st.divider()
    
    # Integração Comercial -> Processo
    if dd['status_cliente'] in ['ATIVO', 'EM NEGOCIAÇÃO']:
        if st.button("✅ Converter em Processo", help="Cria um processo automaticamente com base na proposta"):
             st.session_state.pre_fill_client = dd['nome']
             st.session_state.nav_selection = "Processos"
             st.success("Redirecionando para criação de processo...")
             st.rerun()
             
    if st.button("🗑️ Excluir Cliente", type="primary"):
        db.sql_run("DELETE FROM clientes WHERE id=?", (int(dd['id']),))
        st.success("Cliente excluído.")
        st.rerun()

# --- CALLBACKS ---
def buscar_cep_callback():
    if st.session_state.cad_cep:
        d = ut.buscar_cep(st.session_state.cad_cep)
        if d and "erro" not in d:
            st.session_state.cad_rua = d.get('logradouro', '')
            st.session_state.cad_bairro = d.get('bairro', '')
            st.session_state.cad_cid = d.get('localidade', '')
            st.session_state.cad_uf = d.get('uf', '')
        else: 
            st.toast("CEP não encontrado!", icon="❌")

def salvar_cliente_callback():
    nome = st.session_state.cad_nome
    cpf_cnpj = ut.limpar_numeros(st.session_state.cad_cpf_cnpj)
    tipo_pessoa = st.session_state.cad_tipo_pessoa
    
    if not nome or not cpf_cnpj: 
        st.toast("Nome e Documento obrigatórios!", icon="⚠️")
        return
    
    if db.cpf_existe(cpf_cnpj): 
        st.toast("Documento já cadastrado!", icon="❌")
        return
    
    # Validação de CPF ou CNPJ
    valido = False
    if tipo_pessoa == "Física":
        valido = ut.validar_cpf_matematico(cpf_cnpj)
    else:
        valido = ut.validar_cnpj(cpf_cnpj)
        
    if not valido: 
        st.toast(f"{tipo_pessoa} Inválido!", icon="❌")
        return

    try:
        db.sql_run('''INSERT INTO clientes (
            nome, tipo_pessoa, cpf_cnpj, email, telefone, telefone_fixo, profissao, estado_civil, 
            cep, endereco, numero_casa, complemento, bairro, cidade, estado, obs, 
            status_cliente, link_drive, data_cadastro
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (
            nome, tipo_pessoa, cpf_cnpj, st.session_state.cad_email, st.session_state.cad_tel, 
            st.session_state.cad_fixo, st.session_state.cad_prof, st.session_state.cad_ec, 
            st.session_state.cad_cep, st.session_state.cad_rua, st.session_state.cad_num, 
            st.session_state.cad_comp, st.session_state.cad_bairro, st.session_state.cad_cid, 
            st.session_state.cad_uf, st.session_state.cad_obs, st.session_state.cad_stt, 
            st.session_state.cad_drive, datetime.now().strftime("%Y-%m-%d")
        ))
        st.toast(f"Cliente {nome} Salvo!", icon="✅")
        limpar_campos_cadastro()
    except Exception as e: 
        st.toast(f"Erro: {e}", icon="❌")

def limpar_campos_cadastro():
    campos = ['cad_nome', 'cad_cpf_cnpj', 'cad_email', 'cad_tel', 'cad_fixo', 'cad_prof', 'cad_ec', 'cad_cep', 'cad_rua', 'cad_num', 'cad_comp', 'cad_bairro', 'cad_cid', 'cad_uf', 'cad_obs', 'cad_drive']
    for campo in campos:
        if campo in st.session_state:
            st.session_state[campo] = ""
