import streamlit as st
import database as db
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📊 Relatórios e Inteligência</h1>", unsafe_allow_html=True)
    
    # Abas Principais
    # Abas Principais
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["💰 Financeiro", "📈 DRE Gerencial", "💎 Rentabilidade", "⚖️ Operacional", "🤝 Comercial", "💸 Comissões", "💾 Exportação & Backup"])
    
    # --- ABA 1: FINANCEIRO ---
    with t1:
        render_financeiro()

    # --- ABA 2: DRE GERENCIAL ---
    with t2:
        render_dre()

    # --- ABA 3: RENTABILIDADE ---
    with t3:
        render_rentabilidade()

    # --- ABA 4: OPERACIONAL ---
    with t4:
        render_operacional()

    # --- ABA 5: COMERCIAL ---
    with t5:
        render_comercial()

    # --- ABA 6: COMISSÕES ---
    with t6:
        render_comissoes()

    # --- ABA 7: EXPORTAÇÃO & BACKUP ---
    with t7:
        render_exportacao_backup()

def render_financeiro():
    st.markdown("### Fluxo de Caixa")
    
    # Dados
    df = db.sql_get("financeiro")
    if df.empty:
        st.info("Sem dados financeiros para exibir.")
        return

    df['data'] = pd.to_datetime(df['data'])
    df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
    
    # KPI Cards
    entradas = df[(df['tipo']=='Entrada') & (df['status_pagamento']=='Pago')]['valor'].sum()
    saidas = df[(df['tipo']=='Saída') & (df['status_pagamento']=='Pago')]['valor'].sum()
    saldo = entradas - saidas
    receber = df[(df['tipo']=='Entrada') & (df['status_pagamento']=='Pendente')]['valor'].sum()
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Entradas (Total)", f"R$ {entradas:,.2f}")
    k2.metric("Saídas (Total)", f"R$ {saidas:,.2f}")
    k3.metric("Saldo Realizado", f"R$ {saldo:,.2f}", delta_color="normal")
    k4.metric("A Receber", f"R$ {receber:,.2f}")
    
    st.divider()
    
    # Gráfico de Fluxo de Caixa Mensal
    fluxo_mensal = df[df['status_pagamento']=='Pago'].groupby(['mes_ano', 'tipo'])['valor'].sum().reset_index()
    
    fig = px.bar(fluxo_mensal, x='mes_ano', y='valor', color='tipo', barmode='group',
                 title="Entradas vs Saídas (Mensal)",
                 color_discrete_map={'Entrada': '#10b981', 'Saída': '#ef4444'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Inadimplência
    st.markdown("### ⚠️ Controle de Inadimplência")
    df_inad = db.relatorio_inadimplencia()
    
    if not df_inad.empty:
        total_inad = df_inad['Valor'].sum() if 'Valor' in df_inad.columns else df_inad['valor'].sum()
        st.metric("Total em Atraso", f"R$ {total_inad:,.2f}", delta_color="inverse")
        
        st.dataframe(
            df_inad, 
            use_container_width=True,
            column_config={
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
            }
        )
    else:
        st.success("Nenhuma inadimplência detectada! Parabéns.")

def render_dre():
    st.markdown("### Demonstrativo de Resultado (Gerencial)")
    
    # Filtro de Data
    col_d1, col_d2 = st.columns(2)
    hoje = datetime.now()
    inicio_mes = hoje.replace(day=1)
    
    data_inicio = col_d1.date_input("Data Início", inicio_mes)
    data_fim = col_d2.date_input("Data Fim", hoje)
    
    if data_inicio > data_fim:
        st.error("Data de início não pode ser maior que data fim.")
        return

    df_dre = db.get_dre_data(data_inicio, data_fim)
    
    if df_dre.empty:
        st.warning(f"Sem dados financeiros finalizados para o período selecionado.")
        return
        
    # Estrutura do DRE
    receita_bruta = df_dre[df_dre['tipo'] == 'Entrada']['total'].sum()
    
    # Despesas Variáveis (Impostos, Comissões)
    desp_var = df_dre[(df_dre['tipo'] == 'Saída') & (df_dre['categoria'].isin(['Impostos', 'Comissão Parceria']))]['total'].sum()
    
    margem_contrib = receita_bruta - desp_var
    
    # Despesas Fixas (Todas as outras saídas)
    desp_fixa = df_dre[(df_dre['tipo'] == 'Saída') & (~df_dre['categoria'].isin(['Impostos', 'Comissão Parceria']))]['total'].sum()
    
    lucro_liquido = margem_contrib - desp_fixa
    
    # Visualização em Cascata
    fig = px.waterfall(
        orientation = "v",
        measure = ["relative", "relative", "total", "relative", "total"],
        x = ["Receita Bruta", "Despesas Variáveis", "Margem Contribuição", "Despesas Fixas", "Lucro Líquido"],
        textposition = "outside",
        y = [receita_bruta, -desp_var, margem_contrib, -desp_fixa, lucro_liquido],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    )
    fig.update_layout(title=f"DRE Cascata ({data_inicio} a {data_fim})")
    st.plotly_chart(fig, use_container_width=True)
    
    
    # Gráfico de Despesas por Categoria
    despesas_cat = df_dre[df_dre['tipo'] == 'Saída']
    if not despesas_cat.empty:
        fig_pizza = px.pie(
            despesas_cat, 
            values='total', 
            names='categoria', 
            title="Distribuição de Despesas",
            hole=0.4
        )
        st.plotly_chart(fig_pizza, use_container_width=True)
    
    # Tabela Detalhada com Exportação
    st.markdown("#### Detalhamento por Categoria")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        st.dataframe(df_dre.sort_values(by='total', ascending=False), use_container_width=True, column_config={"total": st.column_config.NumberColumn(format="R$ %.2f")})
    
    with c2:
        # Exportação Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_dre.to_excel(writer, sheet_name='DRE', index=False)
            
        st.download_button(
            label="📥 Baixar Excel",
            data=buffer.getvalue(),
            file_name=f"DRE_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.ms-excel"
        )

def render_rentabilidade():
    st.markdown("### Rentabilidade por Cliente")
    
    # Filtro de Data
    col_d1, col_d2 = st.columns(2)
    hoje = datetime.now()
    inicio_ano = hoje.replace(month=1, day=1)
    
    data_inicio = col_d1.date_input("Início", inicio_ano, key="rent_ini")
    data_fim = col_d2.date_input("Fim", hoje, key="rent_fim")
    
    df_rent = db.get_rentabilidade_clientes(data_inicio, data_fim)
    
    if df_rent.empty:
        st.info("Sem dados suficientes para cálculo de rentabilidade neste período.")
        return
        
    # Top 5 Clientes Mais Rentáveis
    top5 = df_rent.head(5)
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        fig = px.bar(top5, x='cliente', y='lucro', title="Top 5 Clientes (Lucro)", text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.markdown("**Resumo Geral**")
        st.metric("Lucro Total Clientes", f"R$ {df_rent['lucro'].sum():,.2f}")
        st.metric("Margem Média", f"{df_rent['margem'].mean():.1f}%")
        
        # Exportação Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_rent.to_excel(writer, sheet_name='Rentabilidade', index=False)
            
        st.download_button(
            label="📥 Baixar Relatório",
            data=buffer.getvalue(),
            file_name=f"Rentabilidade_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.ms-excel"
        )

    st.dataframe(
        df_rent,
        use_container_width=True,
        column_config={
            "receita": st.column_config.NumberColumn(format="R$ %.2f"),
            "despesa": st.column_config.NumberColumn(format="R$ %.2f"),
            "lucro": st.column_config.NumberColumn(format="R$ %.2f"),
            "margem": st.column_config.ProgressColumn("Margem %", format="%.1f%%", min_value=-100, max_value=100)
        }
    )

def render_operacional():
    st.markdown("### Produtividade e Prazos")
    
    df_proc = db.sql_get("processos")
    if df_proc.empty:
        st.info("Sem processos cadastrados.")
        return
        
    # Gráfico de Processos por Responsável
    contagem = df_proc['responsavel'].value_counts().reset_index()
    contagem.columns = ['Responsável', 'Qtd Processos']
    
    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(contagem, values='Qtd Processos', names='Responsável', title="Distribuição de Processos")
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.markdown("**Próximos Prazos Fatais**")
        hoje = datetime.now().date()
        df_proc['proximo_prazo'] = pd.to_datetime(df_proc['proximo_prazo']).dt.date
        
        # Filtrar prazos futuros próximos
        prazos = df_proc[(df_proc['proximo_prazo'] >= hoje) & (df_proc['proximo_prazo'] <= hoje + timedelta(days=15))]
        if not prazos.empty:
            st.dataframe(prazos[['cliente_nome', 'acao', 'proximo_prazo', 'responsavel']], use_container_width=True)
        else:
            st.success("Sem prazos fatais para os próximos 15 dias.")

def render_comercial():
    st.markdown("### Funil de Vendas")
    
    df_cli = db.sql_get("clientes")
    if df_cli.empty:
        st.info("Sem clientes cadastrados.")
        return
        
    # Conversão de Status
    status_counts = df_cli['status_cliente'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    
    fig_funil = px.funnel(status_counts, x='Quantidade', y='Status', title="Funil de Conversão de Clientes")
    st.plotly_chart(fig_funil, use_container_width=True)
    
    st.markdown("### Propostas em Aberto")
    # Filtrar clientes em negociação com proposta
    propostas = df_cli[(df_cli['status_cliente'] == 'EM NEGOCIAÇÃO') & (df_cli['proposta_valor'] > 0)]
    
    if not propostas.empty:
        total_propostas = propostas['proposta_valor'].sum()
        st.metric("Total em Negociação", f"R$ {total_propostas:,.2f}")
        st.dataframe(propostas[['nome', 'proposta_valor', 'proposta_objeto', 'telefone']], use_container_width=True)
    else:
        st.info("Nenhuma proposta ativa em negociação.")

def render_comissoes():
    st.markdown("### Relatório de Comissões e Parcerias")
    
    # Query para buscar comissões (categoria = 'Repasse de Parceria' ou 'Comissão Parceria')
    # Ajuste conforme categorias usadas no sistema
    query = """
        SELECT 
            f.id,
            f.data as data_pagamento,
            f.valor,
            f.descricao,
            f.status_pagamento,
            p.nome as parceiro_nome,
            proc.numero as processo_numero,
            proc.acao as processo_acao,
            c.nome as cliente_nome
        FROM financeiro f
        LEFT JOIN parceiros p ON f.id_parceiro = p.id
        LEFT JOIN processos proc ON f.id_processo = proc.id
        LEFT JOIN clientes c ON f.id_cliente = c.id
        WHERE f.categoria IN ('Repasse de Parceria', 'Comissão Parceria')
        ORDER BY f.data DESC
    """
    
    try:
        df = db.sql_get_query(query)
    except Exception as e:
        st.error(f"Erro ao buscar comissões: {e}")
        return

    if df.empty:
        st.info("Nenhum registro de comissão/repasse encontrado.")
        return

    # Filtros
    c1, c2 = st.columns(2)
    parceiros_lista = df['parceiro_nome'].unique().tolist()
    # Tratar None
    parceiros_lista = [p for p in parceiros_lista if p]
    
    sel_parceiro = c1.multiselect("Filtrar por Parceiro", parceiros_lista)
    status_filtro = c2.multiselect("Status", df['status_pagamento'].unique())
    
    if sel_parceiro:
        df = df[df['parceiro_nome'].isin(sel_parceiro)]
    if status_filtro:
        df = df[df['status_pagamento'].isin(status_filtro)]
        
    # Métricas
    total_pago = df[df['status_pagamento'] == 'Pago']['valor'].sum()
    total_pendente = df[df['status_pagamento'] == 'Pendente']['valor'].sum()
    
    m1, m2 = st.columns(2)
    m1.metric("Total Pago", f"R$ {total_pago:,.2f}")
    m2.metric("Pendente", f"R$ {total_pendente:,.2f}")
    
    st.dataframe(
        df[['data_pagamento', 'parceiro_nome', 'valor', 'status_pagamento', 'descricao', 'cliente_nome']],
        use_container_width=True,
        column_config={
            "valor": st.column_config.NumberColumn(format="R$ %.2f")
        }
    )

def render_exportacao_backup():
    st.markdown("### 📤 Exportação de Dados")
    st.caption("Baixe os dados completos do sistema em formato Excel.")
    
    tabelas = {
        "Clientes": "clientes",
        "Processos": "processos",
        "Financeiro": "financeiro",
        "Agenda": "agenda",
        "Parceiros": "parceiros"
    }
    
    cols = st.columns(len(tabelas))
    
    for i, (label, table) in enumerate(tabelas.items()):
        with cols[i]:
            df = db.sql_get(table)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name=label, index=False)
                
            st.download_button(
                label=f"📥 {label}",
                data=buffer.getvalue(),
                file_name=f"{label}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
            
    st.divider()
    st.markdown("### 🛡️ Backup Completo do Sistema")
    st.caption("Gera um arquivo SQL contendo toda a estrutura e dados do banco de dados.")
    
    if st.button("📦 Gerar Backup Completo (SQL)"):
        try:
            # Dump do SQLite
            conn = db.get_connection()
            with io.StringIO() as f:
                for line in conn.iterdump():
                    f.write('%s\n' % line)
                sql_dump = f.getvalue()
                
            st.download_button(
                label="⬇️ Baixar Backup SQL",
                data=sql_dump,
                file_name=f"Backup_LopesRibeiro_{datetime.now().strftime('%Y%m%d_%H%M')}.sql",
                mime="application/sql"
            )
            st.success("Backup gerado com sucesso!")
            
        except Exception as e:
            st.error(f"Erro ao gerar backup: {e}")
