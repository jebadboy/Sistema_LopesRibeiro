import streamlit as st
import re
import database as db
import utils as ut
from datetime import datetime
import time
import google_drive as gd
from components.cliente_styles import get_cliente_css

# --- CONSTANTES ---
OPCOES_STATUS = ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"]
OPCOES_TIPO_PESSOA = ["Física", "Jurídica"]
OPCOES_ESTADO_CIVIL = ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"]
OPCOES_PAGAMENTO = ["PIX", "Dinheiro", "Cartão (TON)", "Parcelado Mensal", "% no Êxito", "Entrada + % Êxito"]

def safe_get(series_or_dict, key, default=None):
    """Extrai valor escalar de Series/dict de forma segura"""
    if isinstance(series_or_dict, dict):
        return series_or_dict.get(key, default)
    
    value = series_or_dict.get(key, default)
    # Se retornou uma Series (colunas duplicadas), pega o primeiro
    if hasattr(value, 'iloc'):
        return value.iloc[0] if len(value) > 0 else default
    return value if value is not None else default

def formatar_campo(key, func):
    """Callback genérico para formatar campos."""
    if key in st.session_state:
        valor = st.session_state[key]
        st.session_state[key] = func(valor)

def render():
    st.markdown(get_cliente_css(), unsafe_allow_html=True)
    st.markdown("<h1 style='color: var(--text-main);'>📂 Gestão de Clientes</h1>", unsafe_allow_html=True)

    # Tabs com design limpo
    t1, t2 = st.tabs(["📝 Novo Cadastro", "🔍 Base / Editar / Propostas"])
    
    # --- ABA 1: NOVO CADASTRO ---
    with t1:
        render_novo_cadastro()

    # --- ABA 2: GESTÃO ---
    with t2:
        render_gestao_clientes()

def render_campos_identificacao(prefixo, dados=None, status_args=None):
    """Renderiza campos de identificação (Nome, CPF/CNPJ, Tipo)"""
    dados = dados or {}
    status_args = status_args or {}
    
    # Linha 1: Tipo e Status (se fornecido)
    # Se tiver status, dividimos. Se não, só tipo.
    if status_args:
        c_top1, c_top2 = st.columns([1, 1])
        with c_top1:
             tipo_key = f"{prefixo}_tipo_pessoa"
             tipo_valor = safe_get(dados, 'tipo_pessoa', 'Física')
             tipo_pessoa = st.radio("Tipo de Pessoa", OPCOES_TIPO_PESSOA, 
                                   index=0 if tipo_valor == "Física" else 1,
                                   horizontal=True, key=tipo_key)
        with c_top2:

            st_key = status_args.get('key')
            st_opts = status_args.get('options', [])
            st_idx = status_args.get('index', 0)
            
            # Inicializar session_state
            if st_key and st_key not in st.session_state:
                 # Se o index aponta, temos que achar o valor
                 if 0 <= st_idx < len(st_opts):
                     st.session_state[st_key] = st_opts[st_idx]
            
            st.selectbox("Status / Fase", options=st_opts, key=st_key)
    else:
        tipo_key = f"{prefixo}_tipo_pessoa"
        tipo_valor = safe_get(dados, 'tipo_pessoa', 'Física')
        tipo_pessoa = st.radio("Tipo de Pessoa", OPCOES_TIPO_PESSOA, 
                              index=0 if tipo_valor == "Física" else 1,
                              horizontal=True, key=tipo_key)

    # Linha 2: Nome e Doc
    c1, c2 = st.columns([2, 1])
    c1.text_input("Nome Completo / Razão Social", value=safe_get(dados, 'nome', ''), key=f"{prefixo}_nome")
    
    label_doc = "CPF (Só Números)" if tipo_pessoa == "Física" else "CNPJ (Só Números)"
    doc_key = f"{prefixo}_cpf_cnpj"
    c2.text_input(label_doc, value=safe_get(dados, 'cpf_cnpj', ''), key=doc_key, max_chars=18,
                  on_change=formatar_campo, args=(doc_key, ut.formatar_documento))
    
    return tipo_pessoa

def render_campos_contato(prefixo, dados=None):
    """Renderiza campos de contato e perfil em layout compacto"""
    dados = dados or {}
    
    # Linha 1: Email, Celular, Fixo
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input("E-mail", value=safe_get(dados, 'email', ''), key=f"{prefixo}_email")
    
    tel_key = f"{prefixo}_tel"
    c2.text_input("WhatsApp/Celular", value=safe_get(dados, 'telefone', ''), key=tel_key, max_chars=15,
                   on_change=formatar_campo, args=(tel_key, ut.formatar_celular))
    
    fixo_key = f"{prefixo}_fixo"
    c3.text_input("Fixo", value=safe_get(dados, 'telefone_fixo', ''), key=fixo_key, max_chars=14,
                   on_change=formatar_campo, args=(fixo_key, ut.formatar_celular))

    # Linha 2: Profissão, Estado Civil
    c4, c5 = st.columns([1.5, 1])
    c4.text_input("Profissão / Ramo de Atividade", value=safe_get(dados, 'profissao', ''), key=f"{prefixo}_prof")
    
    opcoes_ec = list(OPCOES_ESTADO_CIVIL)
    valor_ec = safe_get(dados, 'estado_civil', 'Solteiro(a)')
    key_ec = f"{prefixo}_ec"
    
    # Se valor não estiver nas opções padrão, adiciona
    if valor_ec not in opcoes_ec: opcoes_ec.insert(0, valor_ec)
    

    # Inicializar session_state para evitar warning de default value vs session state
    if key_ec not in st.session_state:
        st.session_state[key_ec] = valor_ec

    c5.selectbox("Estado Civil", opcoes_ec, key=key_ec)

def render_campos_pessoais_fisica(prefixo, dados=None):
    """Renderiza campos específicos de Pessoa Física"""
    dados = dados or {}
    
    # Grid de 4 colunas para otimizar espaço vertical
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    
    rg_key = f"{prefixo}_rg"
    c1.text_input("RG", value=safe_get(dados, 'rg', ''), key=rg_key, max_chars=12,
                 on_change=formatar_campo, args=(rg_key, ut.formatar_rg))
    
    c2.text_input("Órgão Emissor", value=safe_get(dados, 'orgao_emissor', ''), key=f"{prefixo}_orgao_emissor")
    c3.text_input("Nacionalidade", value=safe_get(dados, 'nacionalidade', ''), key=f"{prefixo}_nacionalidade")
    
    # Data de Nascimento
    data_valor = None
    data_nasc = safe_get(dados, 'data_nascimento')
    if data_nasc:
        try:
            if isinstance(data_nasc, str):
                data_valor = datetime.strptime(data_nasc, '%Y-%m-%d').date()
            else:
                data_valor = data_nasc
        except:
            pass
            
    from datetime import date
    c4.date_input("Nascimento", value=data_valor, key=f"{prefixo}_data_nascimento", format="DD/MM/YYYY", 
                  min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))

def render_campos_endereco(prefixo, dados=None):
    """Renderiza campos de endereço compactados"""
    dados = dados or {}
    
    # Callback especial para buscar CEP
    def buscar_cep_wrapper():
        cep_val = st.session_state.get(f"{prefixo}_cep")
        if cep_val:
            d = ut.buscar_cep(cep_val)
            if d and "erro" not in d:
                st.session_state[f"{prefixo}_rua"] = d.get('logradouro', '')
                st.session_state[f"{prefixo}_bairro"] = d.get('bairro', '')
                st.session_state[f"{prefixo}_cid"] = d.get('localidade', '')
                st.session_state[f"{prefixo}_uf"] = d.get('uf', '')
            else: 
                st.toast("CEP não encontrado!", icon="❌")

    # Linha 1: CEP + Botão + Logradouro
    c_l1_1, c_l1_2, c_l1_3 = st.columns([1.2, 0.5, 3])
    cep_key = f"{prefixo}_cep"
    c_l1_1.text_input("CEP", value=safe_get(dados, 'cep', ''), key=cep_key, max_chars=9, label_visibility="visible",
                   on_change=formatar_campo, args=(cep_key, ut.formatar_cep))
    c_l1_2.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True) # Espaçador visual
    c_l1_2.button("🔍", key=f"btn_cep_{prefixo}", on_click=buscar_cep_wrapper, help="Buscar CEP")
    
    c_l1_3.text_input("Logradouro", value=safe_get(dados, 'endereco', ''), key=f"{prefixo}_rua")
    
    # Linha 2: Num, Compl, Bairro, Cid, UF
    c_l2_1, c_l2_2, c_l2_3, c_l2_4, c_l2_5 = st.columns([1, 1.5, 2, 2, 0.8])
    c_l2_1.text_input("Número", value=safe_get(dados, 'numero_casa', ''), key=f"{prefixo}_num")
    c_l2_2.text_input("Complemento", value=safe_get(dados, 'complemento', ''), key=f"{prefixo}_comp")
    c_l2_3.text_input("Bairro", value=safe_get(dados, 'bairro', ''), key=f"{prefixo}_bairro")
    c_l2_4.text_input("Cidade", value=safe_get(dados, 'cidade', ''), key=f"{prefixo}_cid")
    c_l2_5.text_input("UF", value=safe_get(dados, 'estado', ''), key=f"{prefixo}_uf")

def render_novo_cadastro():
    # st.markdown("### 📝 Novo Cadastro") # Opcional, já está na aba
    
    # 1. Identificação - Card
    with st.container(border=True):
        st.markdown("**🪪 Identificação**")
        status_opts = {"options": OPCOES_STATUS, "key": "cad_stt", "index": 0}
        tipo_pessoa = render_campos_identificacao("cad", status_args=status_opts)
    
    # 2. Contato e Pessoais - Card
    with st.container(border=True):
        st.markdown("**📞 Contato & Dados**")
        render_campos_contato("cad")
        
        if tipo_pessoa == "Física":
            st.markdown("---")
            render_campos_pessoais_fisica("cad")
        else:
            # Limpar campos ocultos
            st.session_state.setdefault("cad_rg", "")
            st.session_state.setdefault("cad_orgao_emissor", "")
            st.session_state.setdefault("cad_nacionalidade", "")
            st.session_state.setdefault("cad_data_nascimento", None)

    # 3. Endereço - Card
    with st.container(border=True):
         st.markdown("**📍 Endereço**")
         render_campos_endereco("cad")

    # 4. Interno
    with st.container(border=True):
         st.markdown("**📂 Interno**")
         st.text_input("Link Drive", key="cad_drive", help="Link Google Drive")
         st.text_area("Obs", key="cad_obs", height=68)
         st.button("💾 SALVAR CADASTRO", type="primary", on_click=salvar_cliente_callback, use_container_width=True)


def render_gestao_clientes():
    df = db.sql_get("clientes", order_by="nome ASC")
    
    # Prevenir erro de colunas duplicadas que causa "Series is ambiguous"
    if not df.empty:
        df = df.loc[:, ~df.columns.duplicated()]

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
        # Garantir unicidade do índice para evitar Series ambígua
        if hasattr(dd, 'index') and dd.index.duplicated().any():
            dd = dd[~dd.index.duplicated(keep='first')]
        
        # SOLUÇÃO DEFINITIVA: Converter Series para dict para eliminar qualquer ambiguidade
        dd_dict = dd.to_dict()
        render_ficha_cliente(dd_dict)

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
    tipo = safe_get(dd, 'tipo_pessoa', 'Física')
    doc_formatado = ut.formatar_documento(safe_get(dd, 'cpf_cnpj'), tipo)
    
    drive_link_html = ""
    link_drive = safe_get(dd, 'link_drive')
    if link_drive:
        drive_link_html = f"""<a href="{link_drive}" target="_blank" style="text-decoration: none; font-size: 1.2em;">📂 Abrir Pasta no Drive</a>"""

    st.markdown(f"""
    <div class="metric-card" style="border-left-color: var(--primary); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align_items: center;">
            <div class="metric-value">{safe_get(dd, 'nome')}</div>
            <div>{drive_link_html}</div>
        </div>
        <div class="metric-label">Status: {safe_get(dd, 'status_cliente')} | {tipo}: {doc_formatado}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Card de resumo moderno
    render_cliente_card(dd)
    
    # Timeline de histórico
    st.markdown("### 🛤️ Histórico do Cliente")
    render_timeline_avancada(safe_get(dd, 'id'))
    
    st.divider()
    
    # AÇÕES RÁPIDAS
    c_act1, c_act2 = st.columns(2)
    if c_act1.button("➕ Novo Processo", use_container_width=True):
        st.session_state.pre_fill_client = safe_get(dd, 'nome')
        st.session_state.next_nav = "Processos"
        st.rerun()
        
    if c_act2.button("💰 Novo Lançamento", use_container_width=True):
        st.session_state.pre_fill_client = safe_get(dd, 'nome')
        st.session_state.next_nav = "Financeiro"
        st.rerun()
    
    st.divider()
    
    # MODO EDIÇÃO COMPLETA
    with st.expander("✏️ Editar Dados Cadastrais", expanded=False):
        prefixo_edit = f"edit_{safe_get(dd, 'id')}"
        
        # 1. Identificação - Card
        with st.container(border=True):
            st.markdown("**🪪 Identificação**")
            current_status = safe_get(dd, 'status_cliente')
            if hasattr(current_status, 'iloc'): current_status = current_status.iloc[0]
            opcoes_status = OPCOES_STATUS
            idx_status = opcoes_status.index(current_status) if current_status in opcoes_status else 0
            
            status_opts = {"options": opcoes_status, "key": f"{prefixo_edit}_stt", "index": idx_status}
            tipo_pessoa_edit = render_campos_identificacao(prefixo_edit, dd, status_args=status_opts)
        
        # 2. Contato - Card
        with st.container(border=True):
            st.markdown("**📞 Contato & Dados**")
            render_campos_contato(prefixo_edit, dd)
            
            if tipo_pessoa_edit == "Física":
                st.markdown("---")
                render_campos_pessoais_fisica(prefixo_edit, dd)
                
        # 3. Endereço - Card
        with st.container(border=True):
            st.markdown("**📍 Endereço**")
            render_campos_endereco(prefixo_edit, dd)
            
        # 4. Interno e Salvar
        with st.container(border=True):
            st.markdown("**📂 Interno**")
            st.text_input("Link Drive", value=safe_get(dd, 'link_drive', ''), key=f"{prefixo_edit}_drive")
            st.text_area("Observações", value=safe_get(dd, 'obs', ''), key=f"{prefixo_edit}_obs")
            
            if st.button("💾 Salvar Alterações", type="primary", key=f"btn_save_{safe_get(dd, 'id')}"):
                # Recuperar valores e salvar (Lógica similar, apenas recuperando do session_state)
                p = prefixo_edit
                enm = st.session_state.get(f"{p}_nome")
                etipo = st.session_state.get(f"{p}_tipo_pessoa")
                edoc = st.session_state.get(f"{p}_cpf_cnpj")
                estt = st.session_state.get(f"{p}_stt")
                eemail = st.session_state.get(f"{p}_email")
                etel = st.session_state.get(f"{p}_tel")
                efix = st.session_state.get(f"{p}_fixo")
                eprof = st.session_state.get(f"{p}_prof")
                eec = st.session_state.get(f"{p}_ec")
                
                erg = st.session_state.get(f"{p}_rg", "")
                eorgao = st.session_state.get(f"{p}_orgao_emissor", "")
                enac = st.session_state.get(f"{p}_nacionalidade", "")
                edata_nasc = st.session_state.get(f"{p}_data_nascimento")
                
                ecep = st.session_state.get(f"{p}_cep")
                erua = st.session_state.get(f"{p}_rua")
                enum = st.session_state.get(f"{p}_num")
                ecomp = st.session_state.get(f"{p}_comp")
                ebairro = st.session_state.get(f"{p}_bairro")
                ecid = st.session_state.get(f"{p}_cid")
                euf = st.session_state.get(f"{p}_uf")
                
                edrive = st.session_state.get(f"{p}_drive")
                eobs = st.session_state.get(f"{p}_obs")

                data_nasc_str = None
                if edata_nasc:
                    data_nasc_str = edata_nasc.strftime("%Y-%m-%d")
                
                db.sql_run("""
                    UPDATE clientes SET 
                    nome=?, tipo_pessoa=?, cpf_cnpj=?, status_cliente=?, email=?, telefone=?, telefone_fixo=?, 
                    profissao=?, estado_civil=?, cep=?, endereco=?, numero_casa=?, complemento=?, 
                    bairro=?, cidade=?, estado=?, link_drive=?, obs=?, 
                    rg=?, orgao_emissor=?, nacionalidade=?, data_nascimento=?
                    WHERE id=?
                """, (enm, etipo, edoc, estt, eemail, etel, efix, eprof, eec, ecep, erua, enum, ecomp, ebairro, ecid, euf, edrive, eobs, erg, eorgao, enac, data_nasc_str, int(safe_get(dd, 'id'))))
                
                st.success("Dados atualizados com sucesso!")
                st.rerun()

    # MODO PROPOSTA
    with st.expander("💰 Proposta e Negociação", expanded=True):
        c_p1, c_p2 = st.columns(2)
        vp = c_p1.number_input("Valor Total (R$)", value=ut.safe_float(safe_get(dd, 'proposta_valor')))
        ve = c_p2.number_input("Entrada (R$)", value=ut.safe_float(safe_get(dd, 'proposta_entrada')))
        
        c_p3, c_p4 = st.columns(2)
        np_parc = c_p3.number_input("Parcelas", value=ut.safe_int(safe_get(dd, 'proposta_parcelas')))
        
        pg_opts = OPCOES_PAGAMENTO
        pg_val = safe_get(dd, 'proposta_pagamento')
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
        
        ob = st.text_area("Objeto (Descrição)", value=safe_get(dd, 'proposta_objeto', ''), key="txt_objeto")
        
        cb1, cb2 = st.columns(2)
        
        # Botão SALVAR e GERAR
        if cb1.button("💾 Salvar e Atualizar DOC", type="primary"):
            # 1. Salvar no Banco
            data_str = data_pag.strftime('%Y-%m-%d') if data_pag else None
            db.sql_run("UPDATE clientes SET proposta_valor=?, proposta_entrada=?, proposta_parcelas=?, proposta_pagamento=?, proposta_objeto=?, proposta_data_pagamento=? WHERE id=?", 
                       (vp, ve, np_parc, pg, ob, data_str, int(safe_get(dd, 'id'))))
            
            # 2. Gerar Documento Atualizado
            doc_data = {
                'nome': safe_get(dd, 'nome'), 
                'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                'telefone': safe_get(dd, 'telefone'),
                'proposta_valor': vp, 
                'proposta_entrada': ve, 
                'proposta_parcelas': np_parc, 
                'proposta_objeto': ob, 
                'proposta_pagamento': pg,
                'proposta_data_pagamento': data_str
            }
            doc_bytes = ut.criar_doc("Proposta", doc_data)
            st.session_state['doc_proposta_bytes'] = doc_bytes
            st.session_state['doc_proposta_nome'] = f"Prop_{safe_get(dd, 'nome')}.docx"
            
            st.success("Proposta salva e documento atualizado!")
            st.rerun()
            
        with cb2:
            # Botão de Download (Pega do Session State ou Gera do DB)
            # Botão de Download (Pega do Session State ou Gera do DB)
            doc_download = st.session_state.get('doc_proposta_bytes')
            nome_download = st.session_state.get('doc_proposta_nome', f"Prop_{safe_get(dd, 'nome')}.docx")
            
            if not doc_download:
                # Se não tem no state, gera com o que tem no banco (dd)
                doc_data_db = {
                    'nome': safe_get(dd, 'nome'), 
                    'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                    'telefone': safe_get(dd, 'telefone'),
                    'proposta_valor': ut.safe_float(safe_get(dd, 'proposta_valor')), 
                    'proposta_entrada': ut.safe_float(safe_get(dd, 'proposta_entrada')), 
                    'proposta_parcelas': ut.safe_int(safe_get(dd, 'proposta_parcelas')), 
                    'proposta_objeto': safe_get(dd, 'proposta_objeto', ''), 
                    'proposta_pagamento': safe_get(dd, 'proposta_pagamento')
                }
                doc_download = ut.criar_doc("Proposta", doc_data_db)
                st.caption("⚠️ Baixa a versão salva anteriormente.")
            
            st.download_button(
                "📄 Baixar DOC Proposta", 
                doc_download, 
                nome_download, 
                type="secondary"
            )

    # MODO DOCUMENTAÇÃO (Visível para ATIVO e EM NEGOCIAÇÃO)
    if safe_get(dd, 'status_cliente') in ['ATIVO', 'EM NEGOCIAÇÃO']:
        if st.button("✅ Converter em Processo", help="Cria um processo automaticamente com base na proposta"):
             st.session_state.pre_fill_client = safe_get(dd, 'nome')
             st.session_state.next_nav = "Processos"
             st.success("Redirecionando para criação de processo...")
             st.rerun()
             
    # Botão de Exclusão com Segurança
    delete_key = f"del_cli_{safe_get(dd, 'id')}"
    
    if st.button("🗑️ Excluir Cliente", type="primary", use_container_width=True):
        st.session_state[delete_key] = True
        st.rerun()
        
    if st.session_state.get(delete_key, False):
        st.markdown("---")
        with st.container(border=True):
            st.warning("⚠️ **Confirmação de Exclusão**")
            
            # Verificar vínculos
            processos_vinculados = db.sql_get_query("SELECT COUNT(*) as total FROM processos WHERE id_cliente = ?", (safe_get(dd, 'id'),))
            financeiro_vinculado = db.sql_get_query("SELECT COUNT(*) as total FROM financeiro WHERE id_cliente = ?", (safe_get(dd, 'id'),))
            
            total_processos = processos_vinculados.iloc[0]['total'] if not processos_vinculados.empty else 0
            total_financeiro = financeiro_vinculado.iloc[0]['total'] if not financeiro_vinculado.empty else 0
            
            if total_processos > 0 or total_financeiro > 0:
                st.error(f"❌ Não é possível excluir: {total_processos} processos e {total_financeiro} lançamentos vinculados.")
                st.info("Transfira ou apague os vínculos antes de excluir o cliente.")
                if st.button("Ok, entendi"):
                    st.session_state[delete_key] = False
                    st.rerun()
            else:
                st.success("✅ Sem vínculos ativos. Seguro para excluir.")
                nome_confirmacao = st.text_input("Digite o nome do cliente para confirmar:", key=f"inp_del_{safe_get(dd, 'id')}")
                
                c_del1, c_del2 = st.columns(2)
                if c_del1.button("✅ CONFIRMAR", type="primary"):
                    if nome_confirmacao.strip().lower() == safe_get(dd, 'nome').strip().lower():
                        db.sql_run("DELETE FROM clientes WHERE id=?", (int(safe_get(dd, 'id')),))
                        st.success("Cliente excluído com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.session_state.pop("nav_selection", None) # Reset nav se necessário
                        st.rerun()
                    else:
                        st.error("Nome incorreto.")
                
                if c_del2.button("❌ Cancelar"):
                    st.session_state[delete_key] = False
                    st.rerun()

# --- FUNÇÕES AUXILIARES PARA TIMELINE E CARD ---
def registrar_evento_timeline(cliente_id, tipo, titulo, descricao="", icone=""):
    """Registra evento na timeline do cliente"""
    try:
        db.sql_run("""
            INSERT INTO cliente_timeline (cliente_id, tipo_evento, titulo, descricao, icone)
            VALUES (?, ?, ?, ?, ?)
        """, (cliente_id, tipo, titulo, descricao, icone))
    except Exception as e:
        print(f"Erro ao registrar evento timeline: {e}")
def get_cliente_timeline(cliente_id):
    """Busca eventos do cliente ordenados por data"""
    try:
        return db.sql_get_query("""
            SELECT * FROM cliente_timeline 
            WHERE cliente_id = ? 
            ORDER BY data_evento DESC
            LIMIT 50
        """, (cliente_id,))
    except:
        import pandas as pd
        return pd.DataFrame()
def render_timeline_avancada(cliente_id):
    """Renderiza timeline moderna do cliente"""
    eventos = get_cliente_timeline(cliente_id)
    
    if eventos.empty:
        st.info("📝 Nenhum evento registrado ainda")
        return
    
    html = '<div class="cliente-timeline">'
    
    for _, ev in eventos.iterrows():
        try:
            data_obj = datetime.fromisoformat(ev['data_evento'])
            data_fmt = data_obj.strftime('%d/%m/%Y %H:%M')
        except:
            data_fmt = str(ev['data_evento'])[:16]
        
        tipo_evento = ev.get('tipo_evento', 'status')
        dot_class = f"timeline-dot {tipo_evento}"
        icone = ev.get('icone', '●')
        
        html += f"""
        <div class="timeline-event">
            <div class="{dot_class}">{icone}</div>
            <div class="timeline-date">{data_fmt}</div>
            <div class="timeline-title">{ev['titulo']}</div>"""
        
        if ev.get('descricao'):
            html += f'<div class="timeline-desc">{ev["descricao"]}</div>'
        
        html += '</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
def render_cliente_card(dd):
    """Card de resumo visual do cliente"""
    try:
        processos = db.sql_get_query(
            "SELECT COUNT(*) as total FROM processos WHERE cliente_nome = ?", 
            (safe_get(dd, 'nome'),)
        )
        processos_count = processos.iloc[0]['total'] if not processos.empty else 0
    except:
        processos_count = 0
    
    try:
        financeiro = db.sql_get_query("""
            SELECT SUM(valor) as total 
            FROM financeiro 
            WHERE cliente = ? AND status = 'pendente'
        """, (safe_get(dd, 'nome'),))
        pendente_total = financeiro.iloc[0]['total'] if not financeiro.empty and financeiro.iloc[0]['total'] else 0
    except:
        pendente_total = 0
    
    # NOVA FUNCIONALIDADE: Calcular última interação
    ultima_interacao = None
    dias_sem_contato = None
    fonte_interacao = ""
    
    cliente_id = safe_get(dd, 'id')
    cliente_nome = safe_get(dd, 'nome')
    
    # 1. Verificar timeline do cliente
    try:
        timeline = db.sql_get_query("""
            SELECT MAX(data_evento) as ultima FROM cliente_timeline WHERE cliente_id = ?
        """, (cliente_id,))
        if not timeline.empty and timeline.iloc[0]['ultima']:
            ultima_interacao = datetime.fromisoformat(timeline.iloc[0]['ultima'])
            fonte_interacao = "timeline"
    except:
        pass
    
    # 2. Verificar lançamentos financeiros
    try:
        fin = db.sql_get_query("""
            SELECT MAX(data) as ultima FROM financeiro WHERE id_cliente = ?
        """, (cliente_id,))
        if not fin.empty and fin.iloc[0]['ultima']:
            data_fin = datetime.strptime(fin.iloc[0]['ultima'], '%Y-%m-%d')
            if not ultima_interacao or data_fin > ultima_interacao:
                ultima_interacao = data_fin
                fonte_interacao = "financeiro"
    except:
        pass
    
    # 3. Verificar eventos de agenda vinculados a processos do cliente
    try:
        agenda = db.sql_get_query("""
            SELECT MAX(a.data_evento) as ultima 
            FROM agenda a 
            JOIN processos p ON a.id_processo = p.id 
            WHERE p.cliente_nome = ?
        """, (cliente_nome,))
        if not agenda.empty and agenda.iloc[0]['ultima']:
            data_agenda = datetime.strptime(agenda.iloc[0]['ultima'], '%Y-%m-%d')
            if not ultima_interacao or data_agenda > ultima_interacao:
                ultima_interacao = data_agenda
                fonte_interacao = "agenda"
    except:
        pass
    
    # 4. Usar data de cadastro como fallback
    if not ultima_interacao:
        try:
            data_cad = safe_get(dd, 'data_cadastro')
            if data_cad:
                ultima_interacao = datetime.strptime(data_cad, '%Y-%m-%d')
                fonte_interacao = "cadastro"
        except:
            pass
    
    # Calcular dias sem contato
    if ultima_interacao:
        dias_sem_contato = (datetime.now() - ultima_interacao).days
        
        if dias_sem_contato <= 7:
            interacao_badge = f'<span style="color: #28a745; font-weight: bold;">✅ Há {dias_sem_contato} dias</span>'
        elif dias_sem_contato <= 30:
            interacao_badge = f'<span style="color: #ffc107; font-weight: bold;">⚠️ Há {dias_sem_contato} dias</span>'
        elif dias_sem_contato <= 60:
            interacao_badge = f'<span style="color: #fd7e14; font-weight: bold;">🔶 Há {dias_sem_contato} dias</span>'
        else:
            interacao_badge = f'<span style="color: #dc3545; font-weight: bold;">🔴 Há {dias_sem_contato} dias!</span>'
    else:
        interacao_badge = '<span style="color: #6c757d;">❓ Sem registro</span>'
    
    status_icon = "✅" if safe_get(dd, 'status_cliente') == "ATIVO" else "📋" if safe_get(dd, 'status_cliente') == "EM NEGOCIAÇÃO" else "⏹️"
    
    # Gerar link do WhatsApp
    tel_raw = ut.limpar_numeros(str(safe_get(dd, 'telefone', '')))
    if tel_raw:
        link_wpp = f"https://wa.me/55{tel_raw}"
        tel_display = f'<a href="{link_wpp}" target="_blank" style="text-decoration: none; color: inherit;">📞 {safe_get(dd, "telefone")}</a>'
    else:
        tel_display = f"📞 {safe_get(dd, 'telefone', 'N/A')}"
    
    st.markdown(f"""
    <div class="cliente-card">
        <h2>{status_icon} {safe_get(dd, 'nome')}</h2>
        <p>{tel_display} | 📧 {safe_get(dd, 'email', 'N/A')}</p>
        <p>📍 {safe_get(dd, 'cidade', 'N/A')}, {safe_get(dd, 'estado', 'N/A')}</p>
        <hr>
        <div class="cliente-metrics">
            <div class="metric-item">📊 Processos: {processos_count}</div>
            <div class="metric-item">💰 Pendente: R$ {pendente_total:.2f}</div>
            <div class="metric-item">🕐 Última interação: {interacao_badge}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Alerta visual se muito tempo sem contato
    if dias_sem_contato and dias_sem_contato > 30:
        st.warning(f"⏰ **Atenção:** Sem contato há {dias_sem_contato} dias. Considere entrar em contato com o cliente!")

# --- CALLBACKS ---
# --- CALLBACKS ---
# buscar_cep_callback não é mais usado diretamente como estava
# Foi substituído pelo wrapper dentro de render_campos_endereco para suportar múltiplos prefixos
# Mas mantemos aqui se ainda for necessário para algum legado, ou podemos remover.
# Para manter compatibilidade caso algo externo chame, deixamos, mas modificamos para ser genérico se possível.
# def buscar_cep_callback():
#     # DEPRECATED: Removido na refatoração. A lógica agora reside em render_campos_endereco.
#     pass

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

    # Validação de E-mail
    email = st.session_state.cad_email
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.toast("E-mail inválido!", icon="❌")
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
        # Preparar data de nascimento
        data_nasc = None
        if st.session_state.get('cad_data_nascimento'):
            data_nasc = st.session_state.cad_data_nascimento.strftime("%Y-%m-%d")
        
        # --- CRIAR PASTA NO GOOGLE DRIVE AUTOMATICAMENTE ---
        drive_link = st.session_state.get('cad_drive', '')  # Link manual, se fornecido
        
        if not drive_link:  # Se não forneceu link manual, criar pasta automaticamente
            try:
                service = gd.autenticar()
                if service:
                    # Criar pasta com nome do cliente dentro da pasta alvo
                    folder_id = gd.create_folder(service, nome, gd.PASTA_ALVO_ID)
                    if folder_id:
                        # Gerar link da pasta
                        drive_link = f"https://drive.google.com/drive/folders/{folder_id}"
                        st.toast(f"✅ Pasta criada no Drive: {nome}", icon="📂")
                    else:
                        st.warning("⚠️ Não foi possível criar pasta no Drive (continuando sem link)")
                else:
                    st.warning("⚠️ Google Drive não autenticado (continuando sem link)")
            except Exception as e:
                st.warning(f"⚠️ Erro ao criar pasta no Drive: {e} (continuando sem link)")
        
        db.sql_run('''INSERT INTO clientes (
            nome, tipo_pessoa, cpf_cnpj, email, telefone, telefone_fixo, profissao, estado_civil, 
            cep, endereco, numero_casa, complemento, bairro, cidade, estado, obs, 
            status_cliente, link_drive, data_cadastro, rg, orgao_emissor, nacionalidade, data_nascimento
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (
            nome, tipo_pessoa, cpf_cnpj, st.session_state.cad_email, st.session_state.cad_tel, 
            st.session_state.cad_fixo, st.session_state.cad_prof, st.session_state.cad_ec, 
            st.session_state.cad_cep, st.session_state.cad_rua, st.session_state.cad_num, 
            st.session_state.cad_comp, st.session_state.cad_bairro, st.session_state.cad_cid, 
            st.session_state.cad_uf, st.session_state.cad_obs, st.session_state.cad_stt, 
            drive_link, datetime.now().strftime("%Y-%m-%d"),
            st.session_state.get('cad_rg', ''), st.session_state.get('cad_orgao_emissor', ''),
            st.session_state.get('cad_nacionalidade', ''), data_nasc
        ))
        st.toast(f"Cliente {nome} Salvo!", icon="✅")
        limpar_campos_cadastro()
    except Exception as e: 
        st.toast(f"Erro: {e}", icon="❌")

def limpar_campos_cadastro():
    campos = ['cad_nome', 'cad_cpf_cnpj', 'cad_email', 'cad_tel', 'cad_fixo', 'cad_prof', 'cad_ec', 'cad_cep', 'cad_rua', 'cad_num', 'cad_comp', 'cad_bairro', 'cad_cid', 'cad_uf', 'cad_obs', 'cad_drive', 'cad_rg', 'cad_orgao_emissor', 'cad_nacionalidade']
    for campo in campos:
        if campo in st.session_state:
            st.session_state[campo] = ""
    # Limpar campo de data também
    if 'cad_data_nascimento' in st.session_state:
        del st.session_state['cad_data_nascimento']
