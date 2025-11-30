import streamlit as st
import database as db
import utils as ut
from datetime import datetime

def render():
    st.markdown("<h1 style='color: var(--text-main);'>💰 Finanças</h1>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Lançar", "Extrato"])
    
    # --- ABA 1: LANÇAR ---
    with t1:
        render_lancamento()

    # --- ABA 2: EXTRATO ---
    with t2:
        render_extrato()

def render_lancamento():
    dfc = db.sql_get("clientes")
    lista_clientes = ["Avulso"] + dfc['nome'].tolist() if not dfc.empty else ["Avulso"]
    
    with st.container():
        st.markdown("### Novo Lançamento")
        
        c1, c2 = st.columns(2)
        dt = c1.date_input("Vencimento")
        tp = c2.selectbox("Tipo", ["Entrada", "Saída"])
        
        idx_cli = 0
        if 'pre_fill_client' in st.session_state:
            if st.session_state.pre_fill_client in lista_clientes:
                idx_cli = lista_clientes.index(st.session_state.pre_fill_client)
            del st.session_state.pre_fill_client
            
        cl = st.selectbox("Cliente", lista_clientes, index=idx_cli)
        dc = st.text_input("Descrição")
        v = st.number_input("Valor R$", min_value=0.0, step=10.0)
        
        c3, c4 = st.columns(2)
        stt = c3.selectbox("Status", ["Pago", "Pendente"])
        rp = c4.selectbox("Responsável", ["Eduardo", "Sheila"])
        
        if st.button("Lançar Financeiro", type="primary", use_container_width=True):
            if not dc:
                st.toast("Descrição é obrigatória!", icon="⚠️")
                return
                
            descricao_final = f"{cl}-{dc}" if cl != "Avulso" else dc
            
            db.sql_run(
                "INSERT INTO financeiro (data,tipo,categoria,descricao,valor,responsavel,status_pagamento,vencimento) VALUES (?,?,?,?,?,?,?,?)",
                (dt, tp, "Geral", descricao_final, v, rp, stt, dt)
            )
            st.success("Lançamento realizado com sucesso!")

def render_extrato():
    df = db.sql_get("financeiro")
    if df.empty:
        st.info("Nenhum lançamento financeiro.")
        return

    # Filtros rápidos
    col_f1, col_f2 = st.columns(2)
    filtro_tipo = col_f1.multiselect("Filtrar Tipo", df['tipo'].unique())
    filtro_status = col_f2.multiselect("Filtrar Status", df['status_pagamento'].unique())
    
    df_filtered = df.copy()
    if filtro_tipo:
        df_filtered = df_filtered[df_filtered['tipo'].isin(filtro_tipo)]
    if filtro_status:
        df_filtered = df_filtered[df_filtered['status_pagamento'].isin(filtro_status)]

    st.dataframe(
        df_filtered.sort_values(by="data", ascending=False), 
        use_container_width=True,
        hide_index=True
    )
    
    # Botões de Ação
    c_btn1, c_btn2 = st.columns(2)
    
    with c_btn1:
        try:
            st.download_button("📥 Baixar Excel Completo", ut.to_excel(df), "financeiro.xlsx", use_container_width=True)
        except:
            pass
            
    st.divider()
    
    # Gerador de Recibos
    st.markdown("### Gerar Recibo")
    ents = df[df['tipo'] == 'Entrada']
    if not ents.empty:
        ents['lbl'] = ents['id'].astype(str) + " - " + ents['descricao']
        sl = st.selectbox("Selecione a Entrada:", ents['lbl'].tolist())
        
        if sl: 
            dd = df[df['id'] == int(sl.split(" - ")[0])].iloc[0]
            nm = dd['descricao'].split("-")[0] if "-" in dd['descricao'] else "Cliente"
            
            doc = ut.criar_doc("Recibo", {
                'cliente_nome': nm,
                'valor': dd['valor'],
                'descricao': dd['descricao']
            })
            st.download_button("📄 Baixar Recibo DOCX", doc, "recibo.docx", type="secondary", use_container_width=True)
    else:
        st.caption("Sem entradas para gerar recibo.")
