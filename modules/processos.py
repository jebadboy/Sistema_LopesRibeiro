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

    try:
        st.download_button("📥 Baixar Lista de Processos", ut.to_excel(df), "processos.xlsx")
    except:
        pass
