import streamlit as st
import database as db
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📊 Relatórios e Inteligência</h1>", unsafe_allow_html=True)
    
    # Abas Principais
    t1, t2, t3 = st.tabs(["💰 Financeiro", "⚖️ Operacional", "🤝 Comercial"])
    
    # --- ABA 1: FINANCEIRO ---
    with t1:
        render_financeiro()

    # --- ABA 2: OPERACIONAL ---
    with t2:
        render_operacional()

    # --- ABA 3: COMERCIAL ---
    with t3:
        render_comercial()

def render_financeiro():
    st.markdown("### Fluxo de Caixa")
    
    # Filtros
    c1, c2 = st.columns(2)
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
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
        # Calcular Total
        total_inad = df_inad['Valor'].sum()
        st.metric("Total em Atraso", f"R$ {total_inad:,.2f}", delta_color="inverse")
        
        # Gerar Link WhatsApp
        # Formato: https://wa.me/5511999999999?text=Mensagem
        def gerar_link_wpp(row):
            tel = row['WhatsApp']
            if not tel: return None
            tel_limpo = ''.join(filter(str.isdigit, str(tel)))
            msg = f"Olá {row['Cliente']}, verificamos uma pendência referente a {row['Descrição']} vencida em {row['Vencimento']}. Podemos ajudar?"
            return f"https://wa.me/55{tel_limpo}?text={msg}"

        df_inad['Link Cobrança'] = df_inad.apply(gerar_link_wpp, axis=1)
        
        st.dataframe(
            df_inad, 
            use_container_width=True,
            column_config={
                "Link Cobrança": st.column_config.LinkColumn(
                    "Cobrar", display_text="📲 Enviar Zap"
                ),
                "Valor": st.column_config.NumberColumn(
                    "Valor", format="R$ %.2f"
                )
            }
        )
    else:
        st.success("Nenhuma inadimplência detectada! Parabéns.")

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
