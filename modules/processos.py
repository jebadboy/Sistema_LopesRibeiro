import streamlit as st
import database as db
import utils as ut
from datetime import datetime

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
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        dp = c1.date_input("Data da Publicação")
        di = c2.number_input("Dias de Prazo", min_value=1, value=15)
        rg = c3.selectbox("Regra de Contagem", ["Dias Úteis", "Corridos"])
        
        vc = ut.calc_venc(dp, di, rg)
        
        st.info(f"📅 Data Fatal: **{vc.strftime('%d/%m/%Y')}**")
    
    st.divider()
    st.markdown("#### Cadastrar Processo")
    
    with st.form("novo_processo_form"):
        df_clientes = db.sql_get("clientes")
        lista_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
        
        idx_cli = 0
        if 'pre_fill_client' in st.session_state:
            if st.session_state.pre_fill_client in lista_clientes:
                idx_cli = lista_clientes.index(st.session_state.pre_fill_client)
            del st.session_state.pre_fill_client
            
        cl = st.selectbox("Cliente", lista_clientes, index=idx_cli)
        ac = st.text_input("Ação / Número do Processo")
        pz = st.date_input("Prazo Fatal", value=vc)
        resp = st.selectbox("Responsável", ["Eduardo", "Sheila"])
        
        if st.form_submit_button("Salvar Processo", type="primary"):
            if not cl or not ac:
                st.error("Cliente e Ação são obrigatórios.")
            else:
                db.sql_run(
                    "INSERT INTO processos (cliente_nome,acao,proximo_prazo,responsavel,status) VALUES (?,?,?,?,?)",
                    (cl, ac, pz, resp, "Ativo")
                )
                st.success("Processo salvo com sucesso!")

def render_gerenciar_processos():
    df = db.sql_get("processos")
    if df.empty:
        st.info("Nenhum processo cadastrado.")
        return

    # Aplicar Farol
    df['Farol'] = df['proximo_prazo'].apply(ut.calcular_farol)
    
    st.dataframe(
        df[['Farol', 'cliente_nome', 'acao', 'proximo_prazo', 'responsavel']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    st.markdown("### 📝 Andamentos")
    
    df['lbl'] = df['cliente_nome'] + " - " + df['acao']
    sel_p = st.selectbox("Selecione o Processo:", df['lbl'].unique())
    
    if sel_p:
        pid = int(df[df['lbl'] == sel_p].iloc[0]['id'])
        
        # Histórico
        hist = db.get_historico(pid)
        if not hist.empty:
            st.table(hist)
        else:
            st.caption("Nenhum andamento registrado.")
            
        # Novo Andamento
        with st.form("novo_andamento"):
            st.markdown("#### Registrar Andamento")
            dt = st.date_input("Data", value=datetime.now())
            ds = st.text_input("Ocorrência")
            
            if st.form_submit_button("Registrar"):
                db.sql_run(
                    "INSERT INTO andamentos (id_processo,data,descricao,responsavel) VALUES (?,?,?,?)",
                    (pid, dt, ds, "Sys")
                )
                st.success("Andamento registrado!")
                st.rerun()

        # ===== LINK PÚBLICO =====
        import token_manager as tm
        
        st.markdown("---")
        st.markdown("### 🔗 Link Público de Consulta")
        
        col_token1, col_token2 = st.columns([2, 1])
        
        with col_token1:
            dias_validade = st.number_input(
                "Validade do link (dias)", 
                min_value=1,
                max_value=365, 
                value=30,
                help="Número de dias até o link expirar",
                key=f"dias_val_{pid}"
            )
        
        with col_token2:
            if st.button("Gerar Link Público", type="primary", use_container_width=True, key=f"gerar_{pid}"):
                token = tm.gerar_token_publico(pid, dias_validade)
                
                if token:
                    url_base = "http://localhost:8501"
                    link_publico = f"{url_base}/public_view?token={token}"
                    
                    st.session_state[f'link_gerado_{pid}'] = link_publico
                    st.session_state[f'token_validade_{pid}'] = dias_validade
                    st.success("Link gerado com sucesso!")
                    st.rerun()
        
        # Exibir link se foi gerado
        if f'link_gerado_{pid}' in st.session_state:
            st.code(st.session_state[f'link_gerado_{pid}'], language=None)
            
            st.info(
                f"📋 Copie este link e envie ao cliente. "
                f"Válido por {st.session_state.get(f'token_validade_{pid}', 30)} dias."
            )
        
        # Listar tokens ativos
        st.markdown("#### Tokens Ativos")
        tokens_list = tm.listar_tokens_processo(pid)
        
        if tokens_list:
            for token_info in tokens_list:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.caption(f"Token: ...{token_info['token'][-10:]}")
                
                with col2:
                    status = "✅ Ativo" if token_info['ativo'] else "❌ Revogado"
                    acessos = token_info['acessos']
                    st.caption(f"{status} | Acessos: {acessos}")
                
                with col3:
                    if token_info['ativo']:
                        if st.button("Revogar", key=f"revoke_{token_info['id']}"):
                            if tm.revogar_token_publico(token_info['token']):
                                st.success("Token revogado!")
                                st.rerun()
        else:
            st.caption("Nenhum token gerado ainda")


    try:
        st.download_button("📥 Baixar Lista de Processos", ut.to_excel(df), "processos.xlsx")
    except:
        pass
