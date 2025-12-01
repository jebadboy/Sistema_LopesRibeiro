import streamlit as st
import database as db
import utils as ut
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def render():
    st.markdown("<h1 style='color: var(--text-main);'>💰 Gestão Financeira</h1>", unsafe_allow_html=True)
    
    # --- DASHBOARD SUPERIOR (BIG NUMBERS) ---
    render_dashboard_header()
    
    # --- ABAS PRINCIPAIS ---
    t1, t2 = st.tabs(["📝 Lançamentos & Extrato", "📊 Relatórios Gerenciais"])
    
    with t1:
        render_lancamentos_tab()
    
    with t2:
        render_relatorios_tab()

def render_dashboard_header():
    """Renderiza os Big Numbers e Gráfico Resumo no topo."""
    df = db.sql_get("financeiro")
    
    if df.empty:
        st.info("Comece lançando suas receitas e despesas para ver o dashboard.")
        return

    # Converter colunas de data
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['vencimento'] = pd.to_datetime(df['vencimento'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Filtros para o Mês Atual
    df_mes = df[
        (df['vencimento'].dt.month == mes_atual) & 
        (df['vencimento'].dt.year == ano_atual)
    ]
    
    # 1. Saldo do Mês (Realizado)
    entradas_pagas = df_mes[(df_mes['tipo'] == 'Entrada') & (df_mes['status_pagamento'] == 'Pago')]['valor'].sum()
    saidas_pagas = df_mes[(df_mes['tipo'] == 'Saída') & (df_mes['status_pagamento'] == 'Pago')]['valor'].sum()
    saldo_mes = entradas_pagas - saidas_pagas
    
    # 2. Previsão (Tudo do mês, pago ou não)
    entradas_prev = df_mes[df_mes['tipo'] == 'Entrada']['valor'].sum()
    saidas_prev = df_mes[df_mes['tipo'] == 'Saída']['valor'].sum()
    previsao_mes = entradas_prev - saidas_prev
    
    # 3. Inadimplência (Geral - Vencidos e Pendentes)
    inadimplencia = df[
        (df['tipo'] == 'Entrada') & 
        (df['status_pagamento'] == 'Pendente') & 
        (df['vencimento'] < pd.Timestamp(hoje.date()))
    ]['valor'].sum()
    
    # Renderizar Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo do Mês (Caixa)", ut.formatar_moeda(saldo_mes), delta=ut.formatar_moeda(entradas_pagas), delta_color="normal")
    c2.metric("Previsão (Competência)", ut.formatar_moeda(previsao_mes), help="Considera tudo que vence neste mês, pago ou não.")
    c3.metric("Inadimplência Total", ut.formatar_moeda(inadimplencia), delta="-Atrasados", delta_color="inverse")
    
    st.divider()
    
    # Gráfico de Barras (Últimos 6 meses)
    st.markdown("##### 📈 Fluxo de Caixa (Últimos 6 Meses)")
    
    # Preparar dados para o gráfico
    data_limite = hoje - relativedelta(months=5)
    df_chart = df[df['vencimento'] >= pd.Timestamp(data_limite.replace(day=1).date())].copy()
    
    if not df_chart.empty:
        df_chart['mes_ano'] = df_chart['vencimento'].dt.strftime('%Y-%m')
        
        # Agrupar por mês e tipo
        chart_data = df_chart.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack().fillna(0)
        
        # Garantir colunas
        if 'Entrada' not in chart_data.columns: chart_data['Entrada'] = 0
        if 'Saída' not in chart_data.columns: chart_data['Saída'] = 0
        
        st.bar_chart(chart_data, color=["#ff4b4b", "#00cc96"] if 'Saída' in chart_data.columns and chart_data.columns[0] == 'Saída' else ["#00cc96", "#ff4b4b"])

def render_lancamentos_tab():
    c_form, c_extrato = st.columns([1, 2])
    
    with c_form:
        st.markdown("### 🆕 Novo Lançamento")
        with st.container(border=True):
            render_form_lancamento()
            
    with c_extrato:
        st.markdown("### 📋 Extrato de Lançamentos")
        render_extrato_lista()

def render_form_lancamento():
    # Verificar integração
    pre_fill = st.session_state.get('financeiro_pre_fill', {})
    
    with st.form("form_financeiro"):
        tipo = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
        
        # Carregar Clientes
        dfc = db.sql_get("clientes")
        lista_clientes = ["Avulso"] + dfc['nome'].tolist() if not dfc.empty else ["Avulso"]
        
        # Campos Dinâmicos
        categoria = None
        centro_custo = None
        id_cliente = None
        
        # Definir cliente padrão via integração
        idx_cli = 0
        if pre_fill.get('cliente_nome') in lista_clientes:
            idx_cli = lista_clientes.index(pre_fill.get('cliente_nome'))
            
        cliente_nome = "Avulso"
        
        if tipo == "Saída":
            origem = st.radio("Classificação", ["Custo do Escritório", "Adiantamento Cliente/Processo"], horizontal=True)
            if origem == "Custo do Escritório":
                centro_custo = "Escritório"
                cats = ["Aluguel", "Energia/Água", "Internet", "Marketing", "Software", "Pessoal", "Impostos", "Outros"]
                categoria = st.selectbox("Categoria", cats)
            else:
                centro_custo = "Cliente"
                cliente_nome = st.selectbox("Cliente Vinculado", lista_clientes, index=idx_cli)
                categoria = "Reembolso Cliente"
                
        else: # Entrada
            origem_rec = st.radio("Origem", ["Honorários", "Sucumbência", "Reembolso de Despesas", "Outros"], horizontal=True)
            categoria = origem_rec
            if origem_rec in ["Honorários", "Sucumbência", "Reembolso de Despesas"]:
                cliente_nome = st.selectbox("Pagador (Cliente)", lista_clientes, index=idx_cli)
                centro_custo = "Receita Operacional"
            else:
                centro_custo = "Outros"
        
        # Campos Comuns
        desc_val = pre_fill.get('descricao', "")
        descricao = st.text_input("Descrição (Ex: Honorários Divórcio)", value=desc_val)
        valor = st.number_input("Valor Total (R$)", min_value=0.01, step=100.0)
        data_venc = st.date_input("Vencimento Inicial", value=datetime.now())
        
        # Parcelamento (Apenas para Entradas ou Saídas grandes)
        parcelas = 1
        if tipo == "Entrada":
            parcelas = st.number_input("Parcelar em quantas vezes?", min_value=1, max_value=60, value=1)
            if parcelas > 1:
                st.caption(f"Serão gerados {parcelas} lançamentos de {ut.formatar_moeda(valor/parcelas)}")
        
        c1, c2 = st.columns(2)
        status = c1.selectbox("Status", ["Pendente", "Pago"])
        responsavel = c2.selectbox("Responsável", ["Eduardo", "Sheila", "Sistema"])
        
        submitted = st.form_submit_button("💾 Salvar Lançamento", type="primary", use_container_width=True)
        
        if submitted:
            if not descricao:
                st.error("Descrição é obrigatória.")
                return
            
            # Resolver ID Cliente
            if cliente_nome != "Avulso":
                cli_row = dfc[dfc['nome'] == cliente_nome]
                if not cli_row.empty:
                    id_cliente = int(cli_row.iloc[0]['id'])
            
            # Lógica de Parcelamento
            valor_parcela = valor / parcelas
            data_base = data_venc
            
            try:
                for i in range(parcelas):
                    desc_final = f"{descricao} ({i+1}/{parcelas})" if parcelas > 1 else descricao
                    venc_atual = data_base + relativedelta(months=i)
                    
                    dados = {
                        "data": datetime.now().strftime("%Y-%m-%d"),
                        "tipo": tipo,
                        "categoria": categoria,
                        "descricao": desc_final,
                        "valor": round(valor_parcela, 2),
                        "responsavel": responsavel,
                        "status_pagamento": status,
                        "vencimento": venc_atual.strftime("%Y-%m-%d"),
                        "id_cliente": id_cliente,
                        "centro_custo": centro_custo,
                        "recorrente": 0, # Implementar checkbox futuro se necessário
                        "data_pagamento": datetime.now().strftime("%Y-%m-%d") if status == "Pago" else None
                    }
                    
                    db.crud_insert("financeiro", dados, f"Lançamento {tipo}")
                
                st.success(f"{parcelas} lançamento(s) realizado(s) com sucesso!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

def render_extrato_lista():
    df = db.sql_get("financeiro", "vencimento DESC")
    
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
        
    # Filtros
    c1, c2, c3 = st.columns(3)
    f_tipo = c1.multiselect("Tipo", df['tipo'].unique())
    f_cat = c2.multiselect("Categoria", df['categoria'].unique())
    f_status = c3.multiselect("Status", df['status_pagamento'].unique())
    
    if f_tipo: df = df[df['tipo'].isin(f_tipo)]
    if f_cat: df = df[df['categoria'].isin(f_cat)]
    if f_status: df = df[df['status_pagamento'].isin(f_status)]
    
    # Exibição Customizada
    for index, row in df.iterrows():
        cor = "green" if row['tipo'] == "Entrada" else "red"
        icon = "💰" if row['tipo'] == "Entrada" else "💸"
        
        with st.expander(f"{icon} {row['vencimento']} | {row['descricao']} | {ut.formatar_moeda(row['valor'])}"):
            c_det1, c_det2 = st.columns(2)
            
            # Coluna 1: Detalhes
            with c_det1:
                st.write(f"**Categoria:** {row['categoria']}")
                st.write(f"**Centro de Custo:** {row['centro_custo']}")
                st.write(f"**Responsável:** {row['responsavel']}")
                
            # Coluna 2: Ações
            with c_det2:
                novo_status = st.selectbox("Alterar Status", ["Pendente", "Pago"], index=0 if row['status_pagamento']=="Pendente" else 1, key=f"st_{row['id']}")
                
                if novo_status != row['status_pagamento']:
                    db.crud_update("financeiro", 
                                  {"status_pagamento": novo_status, 
                                   "data_pagamento": datetime.now().strftime("%Y-%m-%d") if novo_status == "Pago" else None},
                                  "id = ?", (row['id'],), "Alteração Status Extrato")
                    st.rerun()
                
                if st.button("🗑️ Excluir", key=f"del_{row['id']}"):
                    db.crud_delete("financeiro", "id = ?", (row['id'],), "Exclusão Extrato")
                    st.rerun()

def render_relatorios_tab():
    st.markdown("### 📊 Análise Financeira Detalhada")
    
    df = db.sql_get("financeiro")
    if df.empty:
        st.warning("Sem dados para análise.")
        return
        
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    
    # Filtro de Período
    c1, c2 = st.columns(2)
    ano = c1.selectbox("Ano", sorted(pd.to_datetime(df['vencimento']).dt.year.unique(), reverse=True))
    
    df_ano = df[pd.to_datetime(df['vencimento']).dt.year == ano]
    
    # 1. Despesas por Categoria (Pie Chart)
    st.markdown("#### Despesas por Categoria")
    df_saidas = df_ano[df_ano['tipo'] == 'Saída']
    if not df_saidas.empty:
        cat_sum = df_saidas.groupby('categoria')['valor'].sum()
        st.bar_chart(cat_sum)
    else:
        st.info("Sem despesas neste ano.")
        
    # 2. Receitas por Categoria
    st.markdown("#### Receitas por Origem")
    df_entradas = df_ano[df_ano['tipo'] == 'Entrada']
    if not df_entradas.empty:
        rec_sum = df_entradas.groupby('categoria')['valor'].sum()
        st.bar_chart(rec_sum, color="#00cc96")
    else:
        st.info("Sem receitas neste ano.")
