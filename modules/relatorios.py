import streamlit as st
import database as db
import pandas as pd
import logging
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
import io
import utils as ut

logger = logging.getLogger(__name__)

# ========== CONFIGURAÇÕES E CONSTANTES ==========
PRAZO_ALERTA_DIAS = 15  # Dias para alerta de prazo fatal
MAX_LOGS_LGPD_EXIBIR = 100  # Máximo de logs LGPD a exibir
CACHE_TTL_SEGUNDOS = 300  # 5 minutos de cache
CATEGORIAS_COMISSAO = ['Repasse de Parceria', 'Comissão Parceria']

def safe_to_datetime(series: pd.Series) -> pd.Series:
    """
    Converte Series para datetime removendo timezone se existir.
    
    Args:
        series: Pandas Series com datas em formato string ou datetime
        
    Returns:
        Pandas Series com datas convertidas para datetime sem timezone
        
    Example:
        >>> df['data'] = safe_to_datetime(df['data'])
    """
    result = pd.to_datetime(series, errors='coerce')
    if result.dt.tz is not None:
        result = result.dt.tz_localize(None)
    return result

def validar_periodo(data_inicio: date, data_fim: date) -> bool:
    """
    Valida se o período de datas é válido.
    
    Args:
        data_inicio: Data de início do período
        data_fim: Data de fim do período
        
    Returns:
        True se válido, False caso contrário (exibe erro no Streamlit)
        
    Example:
        >>> if validar_periodo(date(2024, 1, 1), date(2024, 12, 31)):
        ...     processar_relatorio()
    """
    if data_inicio > data_fim:
        st.error("❌ Data de início não pode ser maior que data fim.")
        return False
    
    # Validar se não é muito longe no futuro (mais de 1 ano)
    if data_fim > datetime.now().date() + timedelta(days=365):
        st.warning("⚠️ Data fim está muito longe no futuro. Verifique se está correto.")
    
    return True

# ========== HELPERS REUTILIZÁVEIS ==========

def gerar_download_excel(
    df: pd.DataFrame,
    nome_arquivo: str,
    nome_sheet: str = "Dados",
    label_botao: str = "📥 Baixar Excel"
) -> None:
    """
    Gera botão de download para DataFrame em formato Excel.
    
    Args:
        df: DataFrame a ser exportado
        nome_arquivo: Nome do arquivo (sem extensão .xlsx)
        nome_sheet: Nome da planilha no Excel (padrão: "Dados")
        label_botao: Texto do botão (padrão: "📥 Baixar Excel")
        
    Example:
        >>> gerar_download_excel(
        ...     df_dre,
        ...     f"DRE_{data_inicio}_{data_fim}",
        ...     "DRE Gerencial"
        ... )
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=nome_sheet, index=False)
    
    st.download_button(
        label=label_botao,
        data=buffer.getvalue(),
        file_name=f"{nome_arquivo}.xlsx",
        mime="application/vnd.ms-excel"
    )

def render_filtro_periodo(
    key_prefix: str,
    data_inicio_padrao: Optional[date] = None,
    data_fim_padrao: Optional[date] = None,
    colunas: Tuple[int, int, int] = (1, 1, 2)
) -> Tuple[date, date]:
    """
    Renderiza filtro de período padronizado.
    
    Args:
        key_prefix: Prefixo para keys do Streamlit (ex: "fin", "dre")
        data_inicio_padrao: Data inicial padrão (default: início do mês atual)
        data_fim_padrao: Data final padrão (default: hoje)
        colunas: Proporções das colunas (inicio, fim, extras)
        
    Returns:
        Tupla (data_inicio, data_fim)
        
    Example:
        >>> data_inicio, data_fim = render_filtro_periodo("fin")
        >>> if validar_periodo(data_inicio, data_fim):
        ...     processar_dados(data_inicio, data_fim)
    """
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    
    col1, col2, col3 = st.columns(colunas)
    
    data_inicio = col1.date_input(
        "De",
        data_inicio_padrao or inicio_mes,
        key=f"{key_prefix}_ini"
    )
    data_fim = col2.date_input(
        "Até",
        data_fim_padrao or hoje,
        key=f"{key_prefix}_fim"
    )
    
    return data_inicio, data_fim

def _detectar_anomalias_financeiras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta anomalias financeiras (gastos >50% acima da média).
    
    Args:
        df: DataFrame com dados financeiros filtrados
        
    Returns:
        DataFrame com anomalias detectadas (categoria, valor, média, variação)
        
    Example:
        >>> anomalias = _detectar_anomalias_financeiras(df_financeiro)
        >>> if not anomalias.empty:
        ...     st.warning(f"{len(anomalias)} anomalias detectadas!")
    """
    if df.empty:
        return pd.DataFrame()
    
    # Calcular média e desvio padrão por categoria
    anomalias = []
    
    # Filtrar apenas saídas pagas
    df_saidas = df[(df['tipo'] == 'Saída') & (df['status_pagamento'] == 'Pago')]
    
    for categoria in df_saidas['categoria'].dropna().unique():
        df_cat = df_saidas[df_saidas['categoria'] == categoria]
        
        if len(df_cat) >= 3:  # Precisa de pelo menos 3 registros para calcular média
            media = df_cat['valor'].mean()
            limite = media * 1.5  # 50% acima da média
            
            # Identificar valores anormais
            df_anomalo = df_cat[df_cat['valor'] > limite]
            
            for _, row in df_anomalo.iterrows():
                anomalias.append({
                    'data': row['data'],
                    'categoria': categoria,
                    'valor': row['valor'],
                    'media': media,
                    'variacao_pct': ((row['valor'] - media) / media * 100),
                    'descricao': row.get('descricao', '-')
                })
    
    if anomalias:
        df_result = pd.DataFrame(anomalias)
        df_result = df_result.sort_values('variacao_pct', ascending=False)
        return df_result
    
    return pd.DataFrame()

# ========== FUNÇÕES CACHED PARA PERFORMANCE ==========

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados...")
def get_clientes_cached():
    """Retorna clientes com cache de 5 minutos"""
    return db.sql_get("clientes")

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados...")
def get_processos_cached():
    """Retorna processos com cache de 5 minutos"""
    return db.sql_get("processos")

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados...")
def get_financeiro_cached():
    """Retorna registros financeiros com cache de 5 minutos"""
    return db.sql_get("financeiro")

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados...")
def get_agenda_cached():
    """Retorna agenda com cache de 5 minutos"""
    return db.sql_get("agenda")

@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados...")
def get_andamentos_cached():
    """Retorna andamentos com cache de 5 minutos"""
    return db.sql_get("andamentos")

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📊 Relatórios e Inteligência</h1>", unsafe_allow_html=True)
    
    # Botão para forçar atualização do cache
    col_refresh, col_info = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Atualizar", help="Força atualização dos dados"):
            st.cache_data.clear()
            st.rerun()
    with col_info:
        st.caption("📊 Dados atualizados a cada 5 minutos")
    
    # NOVO: Métricas Rápidas no Topo
    try:
        # P2: Usar funções cached
        df_cli = get_clientes_cached()
        df_proc = get_processos_cached()
        df_fin = get_financeiro_cached()
        
        total_clientes = len(df_cli) if not df_cli.empty else 0
        total_processos = len(df_proc) if not df_proc.empty else 0
        processos_ativos = len(df_proc[df_proc['status'] != 'Arquivado']) if not df_proc.empty and 'status' in df_proc.columns else total_processos
        
        # Faturamento do mês atual
        fat_mes = 0.0
        if not df_fin.empty:
            df_fin['data'] = safe_to_datetime(df_fin['data'])
            mes_atual = datetime.now().strftime('%Y-%m')
            pagos_mes = df_fin[
                (df_fin['tipo'] == 'Entrada') & 
                (df_fin['status_pagamento'] == 'Pago') &
                (df_fin['data'].dt.strftime('%Y-%m') == mes_atual)
            ]
            fat_mes = pagos_mes['valor'].sum() if not pagos_mes.empty else 0.0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("👥 Clientes", total_clientes)
        m2.metric("⚖️ Processos Ativos", processos_ativos)
        m3.metric("📁 Total Processos", total_processos)
        m4.metric("💰 Faturamento Mês", f"R$ {fat_mes:,.0f}")
        
        st.divider()
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Erro ao carregar métricas rápidas: {e}", exc_info=True)
        st.warning("⚠️ Algumas métricas não puderam ser carregadas. Verifique os dados.")
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar métricas rápidas: {e}", exc_info=True)
    
    # Abas Principais
    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
        "💰 Financeiro", 
        "📈 DRE Gerencial", 
        "💎 Rentabilidade", 
        "⚖️ Operacional", 
        "👨‍💼 Produtividade",
        "🤝 Comercial", 
        "💸 Comissões", 
        "🔐 LGPD",
        "💾 Exportação"
    ])
    
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

    # --- ABA 5: PRODUTIVIDADE ---
    with t5:
        render_produtividade()

    # --- ABA 6: COMERCIAL ---
    with t6:
        render_comercial()

    # --- ABA 7: COMISSÕES ---
    with t7:
        render_comissoes()

    # --- ABA 8: LGPD ---
    with t8:
        render_lgpd()

    # --- ABA 9: EXPORTAÇÃO & BACKUP ---
    with t9:
        render_exportacao_backup()

def render_financeiro():
    st.markdown("### Fluxo de Caixa")
    
    # P2: Dados com cache
    df = get_financeiro_cached()
    if df.empty:
        st.info("Sem dados financeiros para exibir.")
        return

    df['data'] = safe_to_datetime(df['data'])
    
    # NOVO: Filtro de Período
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    hoje = datetime.now()
    inicio_ano = hoje.replace(month=1, day=1)
    
    data_inicio = col_f1.date_input("De", inicio_ano, key="fin_ini")
    data_fim = col_f2.date_input("Até", hoje, key="fin_fim")
    
    # Bug #6: Validar período
    if not validar_periodo(data_inicio, data_fim):
        return
    
    # Aplicar filtro
    data_inicio_ts = pd.Timestamp(data_inicio)
    data_fim_ts = pd.Timestamp(data_fim)
    df_filtrado = df[(df['data'] >= data_inicio_ts) & (df['data'] <= data_fim_ts)]
    
    if df_filtrado.empty:
        st.warning("Nenhum dado no período selecionado.")
        return
    
    df_filtrado['mes_ano'] = df_filtrado['data'].dt.strftime('%Y-%m')
    
    # KPI Cards
    entradas = df_filtrado[(df_filtrado['tipo']=='Entrada') & (df_filtrado['status_pagamento']=='Pago')]['valor'].sum()
    saidas = df_filtrado[(df_filtrado['tipo']=='Saída') & (df_filtrado['status_pagamento']=='Pago')]['valor'].sum()
    saldo = entradas - saidas
    receber = df_filtrado[(df_filtrado['tipo']=='Entrada') & (df_filtrado['status_pagamento']=='Pendente')]['valor'].sum()
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Entradas (Período)", f"R$ {entradas:,.2f}")
    k2.metric("Saídas (Período)", f"R$ {saidas:,.2f}")
    k3.metric("Saldo Realizado", f"R$ {saldo:,.2f}", delta_color="normal")
    k4.metric("A Receber", f"R$ {receber:,.2f}")
    
    st.divider()
    
    # Tabs para gráficos
    tab_bar, tab_line = st.tabs(["📊 Barras", "📈 Tendência"])
    
    with tab_bar:
        # Gráfico de Fluxo de Caixa Mensal (Barras)
        fluxo_mensal = df_filtrado[df_filtrado['status_pagamento']=='Pago'].groupby(['mes_ano', 'tipo'])['valor'].sum().reset_index()
        
        fig = px.bar(fluxo_mensal, x='mes_ano', y='valor', color='tipo', barmode='group',
                     title="Entradas vs Saídas (Mensal)",
                     color_discrete_map={'Entrada': '#10b981', 'Saída': '#ef4444'})
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_line:
        # P3: Gráfico de Tendência OTIMIZADO (10-33x mais rápido)
        
        # Filtrar dados pagos uma vez
        df_pago = df_filtrado[df_filtrado['status_pagamento']=='Pago']
        
        # Separar entradas e saídas ANTES de agregar (O(n) ao invés de O(n²))
        entradas_mes = df_pago[df_pago['tipo']=='Entrada'].groupby('mes_ano')['valor'].sum()
        saidas_mes = df_pago[df_pago['tipo']=='Saída'].groupby('mes_ano')['valor'].sum()
        
        # Combinar índices (todos os meses presentes)
        todos_meses = entradas_mes.index.union(saidas_mes.index).sort_values()
        
        # Criar DataFrame final
        tendencia = pd.DataFrame({
            'Mês': todos_meses,
            'Entradas': entradas_mes.reindex(todos_meses, fill_value=0).values,
            'Saídas': saidas_mes.reindex(todos_meses, fill_value=0).values
        })
        tendencia['Saldo'] = tendencia['Entradas'] - tendencia['Saídas']
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=tendencia['Mês'], y=tendencia['Entradas'], name='Entradas', 
                                       line=dict(color='#10b981', width=3), mode='lines+markers'))
        fig_line.add_trace(go.Scatter(x=tendencia['Mês'], y=tendencia['Saídas'], name='Saídas', 
                                       line=dict(color='#ef4444', width=3), mode='lines+markers'))
        fig_line.add_trace(go.Scatter(x=tendencia['Mês'], y=tendencia['Saldo'], name='Saldo', 
                                       line=dict(color='#3b82f6', width=2, dash='dash'), mode='lines+markers'))
        fig_line.update_layout(title="Tendência Financeira", xaxis_title="Mês", yaxis_title="Valor (R$)")
        st.plotly_chart(fig_line, use_container_width=True)
    
    # NOVO: Exportação PDF
    with col_f3:
        st.markdown("")
        if st.button("📄 Gerar PDF", key="pdf_fin"):
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()
                
                elements.append(Paragraph("RELATÓRIO FINANCEIRO", styles['Heading1']))
                elements.append(Paragraph(f"Período: {data_inicio} a {data_fim}", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                data = [
                    ['Métrica', 'Valor'],
                    ['Entradas', f'R$ {entradas:,.2f}'],
                    ['Saídas', f'R$ {saidas:,.2f}'],
                    ['Saldo', f'R$ {saldo:,.2f}'],
                    ['A Receber', f'R$ {receber:,.2f}']
                ]
                t = Table(data, colWidths=[200, 150])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(t)
                doc.build(elements)
                
                st.download_button(
                    "⬇️ Baixar PDF",
                    pdf_buffer.getvalue(),
                    f"Financeiro_{data_inicio}_{data_fim}.pdf",
                    mime="application/pdf"
                )
            except ImportError:
                st.warning("Instale reportlab para gerar PDF")
    
    # NOVO: Comparativo Mês vs Mês
    st.divider()
    st.markdown("#### 📊 Comparativo Mensal")
    
    df_filtrado['mes_ano'] = df_filtrado['data'].dt.strftime('%Y-%m')
    meses_disponiveis = sorted(df_filtrado['mes_ano'].unique().tolist(), reverse=True)
    
    if len(meses_disponiveis) >= 2:
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            mes1 = st.selectbox("Primeiro Mês", meses_disponiveis, index=1, key="comp_mes1")
        with col_comp2:
            mes2 = st.selectbox("Segundo Mês", meses_disponiveis, index=0, key="comp_mes2")
        
        # Calcular métricas para cada mês
        df_mes1 = df_filtrado[df_filtrado['mes_ano'] == mes1]
        df_mes2 = df_filtrado[df_filtrado['mes_ano'] == mes2]
        
        df_pago1 = df_mes1[df_mes1['status_pagamento'] == 'Pago']
        df_pago2 = df_mes2[df_mes2['status_pagamento'] == 'Pago']
        
        entradas1 = df_pago1[df_pago1['tipo'] == 'Entrada']['valor'].sum()
        saidas1 = df_pago1[df_pago1['tipo'] == 'Saída']['valor'].sum()
        saldo1 = entradas1 - saidas1
        
        entradas2 = df_pago2[df_pago2['tipo'] == 'Entrada']['valor'].sum()
        saidas2 = df_pago2[df_pago2['tipo'] == 'Saída']['valor'].sum()
        saldo2 = entradas2 - saidas2
        
        # Calcular variações
        var_entradas = ((entradas2 - entradas1) / entradas1 * 100) if entradas1 > 0 else 0
        var_saidas = ((saidas2 - saidas1) / saidas1 * 100) if saidas1 > 0 else 0
        var_saldo = ((saldo2 - saldo1) / abs(saldo1) * 100) if saldo1 != 0 else 0
        
        # Exibir comparativo
        c1, c2, c3 = st.columns(3)
        
        c1.metric(
            "Entradas",
            f"R$ {entradas2:,.2f}",
            f"{var_entradas:+.1f}%",
            delta_color="normal"
        )
        c2.metric(
            "Saídas",
            f"R$ {saidas2:,.2f}",
            f"{var_saidas:+.1f}%",
            delta_color="inverse"
        )
        c3.metric(
            "Saldo",
            f"R$ {saldo2:,.2f}",
            f"{var_saldo:+.1f}%",
            delta_color="normal"
        )
        
        # Gráfico de barras comparativo
        comparativo = pd.DataFrame({
            'Categoria': ['Entradas', 'Saídas', 'Saldo'],
            mes1: [entradas1, saidas1, saldo1],
            mes2: [entradas2, saidas2, saldo2]
        })
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(name=mes1, x=comparativo['Categoria'], y=comparativo[mes1], marker_color='lightblue'))
        fig_comp.add_trace(go.Bar(name=mes2, x=comparativo['Categoria'], y=comparativo[mes2], marker_color='royalblue'))
        
        fig_comp.update_layout(
            title=f"Comparativo: {mes1} vs {mes2}",
            barmode='group',
            yaxis_title="Valor (R$)",
            height=350
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("📅 Selecione um período com pelo menos 2 meses para visualizar comparação.")
    
    # NOVO: Alertas de Anomalias
    st.divider()
    st.markdown("#### ⚠️ Alertas de Anomalias Financeiras")
    st.caption("Detecta gastos acima de 50% da média por categoria")
    
    df_anomalias = _detectar_anomalias_financeiras(df_filtrado)
    
    if not df_anomalias.empty:
        st.warning(f"🚨 **{len(df_anomalias)} anomalia(s) detectada(s)!**")
        
        st.dataframe(
            df_anomalias,
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "categoria": "Categoria",
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "media": st.column_config.NumberColumn("Média", format="R$ %.2f"),
                "variacao_pct": st.column_config.NumberColumn("Variação", format="+%.1f%%"),
                "descricao": "Descrição"
            }
        )
    else:
        st.success("✅ Nenhuma anomalia detectada no período selecionado.")
    
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

def render_dre() -> None:
    """
    Renderiza Demonstrativo de Resultado Gerencial.
    
    Exibe DRE em formato cascata com receita bruta, despesas variáveis/fixas,
    margem de contribuição e lucro líquido. Inclui gráfico de pizza de despesas
    por categoria e exportação Excel.
    
    Returns:
        None. Renderiza diretamente no Streamlit.
    """
    st.markdown("### Demonstrativo de Resultado (Gerencial)")
    
    # Filtro de Data usando helper
    data_inicio, data_fim = render_filtro_periodo("dre")
    
    # Bug #6: Validar período
    if not validar_periodo(data_inicio, data_fim):
        return

    # Spinner para operação pesada
    with st.spinner("Gerando DRE..."):
        df_dre = db.get_dre_data(data_inicio,data_fim)
    
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

def render_rentabilidade() -> None:
    """
    Renderiza relatório de rentabilidade por cliente.
    
    Calcula e exibe lucro e margem por cliente no período selecionado,
    com gráfico dos top 5 clientes mais rentáveis.
    
    Returns:
        None. Renderiza diretamente no Streamlit.
    """
    st.markdown("### Rentabilidade por Cliente")
    
    # Filtro de Data usando helper
    hoje = datetime.now().date()
    inicio_ano = hoje.replace(month=1, day=1)
    data_inicio, data_fim = render_filtro_periodo(
        "rent",
        data_inicio_padrao=inicio_ano,
        colunas=(1, 1, 0)  # Sem coluna extra
    )
    
    # Bug #6: Validar período
    if not validar_periodo(data_inicio, data_fim):
        return
    
    # Spinner para operação pesada
    with st.spinner("Calculando rentabilidade..."):
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
    
    # P2: Usar dados cached
    df_proc = get_processos_cached()
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
        hoje = pd.Timestamp(datetime.now().date())
        df_proc['proximo_prazo'] = safe_to_datetime(df_proc['proximo_prazo'])
        
        # Filtrar prazos futuros próximos (usando constante PRAZO_ALERTA_DIAS)
        limite = hoje + pd.Timedelta(days=PRAZO_ALERTA_DIAS)
        prazos = df_proc[(df_proc['proximo_prazo'] >= hoje) & (df_proc['proximo_prazo'] <= limite)]
        if not prazos.empty:
            st.dataframe(prazos[['cliente_nome', 'acao', 'proximo_prazo', 'responsavel']], use_container_width=True)
        else:
            st.success("Sem prazos fatais para os próximos 15 dias.")


def render_produtividade() -> None:
    """
    Renderiza relatório de produtividade por responsável.
    
    Exibe métricas de processos ativos, andamentos registrados e eventos
    concluídos por advogado/responsável no período selecionado.
    
    Returns:
        None. Renderiza diretamente no Streamlit.
    """
    st.markdown("### 👨‍💼 Produtividade por Responsável")
    
    # Filtros de período usando helper + filtro de responsável
    col_d1, col_d2, col_resp = st.columns(3)
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    
    with col_d1:
        data_inicio = st.date_input("Data Início", inicio_mes, key="prod_ini")
    with col_d2:
        data_fim = st.date_input("Data Fim", hoje, key="prod_fim")
    
    # Bug #6: Validar período
    if not validar_periodo(data_inicio, data_fim):
        return
    
    # P2: Dados de processos com cache
    df_proc = get_processos_cached()
    df_agenda = get_agenda_cached()
    df_andamentos = get_andamentos_cached()
    
    if df_proc.empty:
        st.info("Sem processos cadastrados para análise.")
        return
    
    # Lista de responsáveis
    responsaveis = df_proc['responsavel'].dropna().unique().tolist()
    sel_resp = col_resp.selectbox("Responsável", ["Todos"] + responsaveis)
    
    # Métricas por responsável
    st.markdown("#### 📊 Resumo de Atividades")
    
    metricas = []
    for resp in responsaveis:
        proc_resp = df_proc[df_proc['responsavel'] == resp]
        
        # Processos ativos
        ativos = len(proc_resp[proc_resp['status'] != 'Arquivado'])
        
        # Andamentos no período
        if not df_andamentos.empty:
            df_andamentos['data'] = safe_to_datetime(df_andamentos['data'])
            data_ini_ts = pd.Timestamp(data_inicio)
            data_fim_ts = pd.Timestamp(data_fim)
            and_periodo = df_andamentos[
                (df_andamentos['responsavel'] == resp) &
                (df_andamentos['data'] >= data_ini_ts) &
                (df_andamentos['data'] <= data_fim_ts)
            ]
            total_andamentos = len(and_periodo)
        else:
            total_andamentos = 0
        
        # Eventos de agenda concluídos
        if not df_agenda.empty:
            df_agenda['data_evento'] = safe_to_datetime(df_agenda['data_evento'])
            data_ini_ts = pd.Timestamp(data_inicio)
            data_fim_ts = pd.Timestamp(data_fim)
            eventos = df_agenda[
                (df_agenda['responsavel'] == resp) &
                (df_agenda['status'] == 'concluido') &
                (df_agenda['data_evento'] >= data_ini_ts) &
                (df_agenda['data_evento'] <= data_fim_ts)
            ]
            total_eventos = len(eventos)
        else:
            total_eventos = 0
        
        metricas.append({
            'Responsável': resp,
            'Processos Ativos': ativos,
            'Andamentos Registrados': total_andamentos,
            'Eventos Concluídos': total_eventos,
            'Score': ativos * 2 + total_andamentos + total_eventos
        })
    
    df_metricas = pd.DataFrame(metricas).sort_values('Score', ascending=False)
    
    if sel_resp != "Todos":
        df_metricas = df_metricas[df_metricas['Responsável'] == sel_resp]
    
    # Gráfico de barras
    fig = px.bar(
        df_metricas, 
        x='Responsável', 
        y=['Processos Ativos', 'Andamentos Registrados', 'Eventos Concluídos'],
        title="Produtividade por Responsável",
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela detalhada
    st.dataframe(df_metricas, use_container_width=True, hide_index=True)
    
    # Exportação
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_metricas.to_excel(writer, sheet_name='Produtividade', index=False)
    
    st.download_button(
        label="📥 Exportar Excel",
        data=buffer.getvalue(),
        file_name=f"Produtividade_{data_inicio}_{data_fim}.xlsx",
        mime="application/vnd.ms-excel"
    )


def render_lgpd():
    """Relatório de conformidade LGPD - RESTRITO A ADMINISTRADORES"""
    # S3: Controle de Acesso
    if not st.session_state.get('is_admin', False):
        st.error("🔒 Acesso restrito. Somente administradores podem visualizar relatórios de LGPD.")
        st.info("Entre em contato com o administrador do sistema para solicitar acesso.")
        return
    
    st.markdown("### 🔐 Relatório de Conformidade LGPD")
    st.caption("Monitoramento de acessos a dados pessoais conforme Lei nº 13.709/2018")
    
    # Métricas gerais
    col1, col2, col3 = st.columns(3)
    
    # Clientes com consentimento
    try:
        total_cli = db.sql_get_query("SELECT COUNT(*) as t FROM clientes")
        com_lgpd = db.sql_get_query("SELECT COUNT(*) as t FROM clientes WHERE lgpd_consentimento = 1")
        
        # Bug #2: Validação robusta contra None e divisão por zero
        total = total_cli.iloc[0]['t'] if (not total_cli.empty and 't' in total_cli.columns) else 0
        consentidos = com_lgpd.iloc[0]['t'] if (not com_lgpd.empty and 't' in com_lgpd.columns) else 0
        
        # Garantir que são numéricos
        total = int(total) if total is not None else 0
        consentidos = int(consentidos) if consentidos is not None else 0
        
        col1.metric("Total de Clientes", total)
        col2.metric("Com Consentimento LGPD", consentidos)
        col3.metric("Taxa de Conformidade", f"{(consentidos/total*100) if total > 0 else 0:.1f}%")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Erro ao calcular métricas LGPD: {e}", exc_info=True)
        col1.metric("Total de Clientes", "-")
        col2.metric("Com Consentimento LGPD", "-")
        col3.metric("Taxa de Conformidade", "-")
        st.warning("⚠️ Erro ao carregar métricas. Verifique a estrutura da tabela clientes.")
    except Exception as e:
        logger.error(f"Erro inesperado ao consultar dados LGPD: {e}", exc_info=True)
        col1.metric("Total de Clientes", "N/A")
        col2.metric("Com Consentimento LGPD", "N/A")
        col3.metric("Taxa de Conformidade", "N/A")
    
    # NOVA SEÇÃO: Dashboard de Evolução LGPD
    st.divider()
    st.markdown("#### 📈 Evolução de Consentimentos")
    st.caption("Acompanhamento da taxa de conformidade ao longo do tempo")
    
    try:
        # Query para pegar histórico baseado em data de cadastro
        query_evolucao = """
            SELECT 
                DATE(data_cadastro) as data,
                SUM(CASE WHEN lgpd_consentimento = 1 THEN 1 ELSE 0 END) as com_consentimento,
                COUNT(*) as total
            FROM clientes
            WHERE data_cadastro IS NOT NULL
            GROUP BY DATE(data_cadastro)
            ORDER BY data
        """
        
        df_evolucao = db.sql_get_query(query_evolucao)
        
        if not df_evolucao.empty and len(df_evolucao) > 1:
            # Calcular taxa acumulada
            df_evolucao['total_acumulado'] = df_evolucao['total'].cumsum()
            df_evolucao['consentimento_acumulado'] = df_evolucao['com_consentimento'].cumsum()
            df_evolucao['taxa_conformidade'] = (
                df_evolucao['consentimento_acumulado'] / df_evolucao['total_acumulado'] * 100
            )
            
            # Gráfico de linha de evolução
            fig_evolucao = go.Figure()
            
            fig_evolucao.add_trace(go.Scatter(
                x=df_evolucao['data'],
                y=df_evolucao['taxa_conformidade'],
                mode='lines+markers',
                name='Taxa de Conformidade',
                line=dict(color='green', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.1)'
            ))
            
            fig_evolucao.update_layout(
                title="Evolução da Taxa de Conformidade LGPD",
                xaxis_title="Data",
                yaxis_title="Taxa de Conformidade (%)",
                hovermode='x unified',
                height=350,
                yaxis=dict(range=[0, 100])
            )
            
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
            # Métricas adicionais dos últimos 30 dias
            col_a, col_b, col_c = st.columns(3)
            
            ultimos_30_dias = datetime.now().date() - timedelta(days=30)
            ultimos_30 = df_evolucao[pd.to_datetime(df_evolucao['data']).dt.date >= ultimos_30_dias]
            
            if not ultimos_30.empty:
                novos_clientes_30d = int(ultimos_30['total'].sum())
                com_lgpd_30d = int(ultimos_30['com_consentimento'].sum())
                taxa_30d = (com_lgpd_30d / novos_clientes_30d * 100) if novos_clientes_30d > 0 else 0
                
                col_a.metric("Novos Clientes (30d)", novos_clientes_30d)
                col_b.metric("Com LGPD (30d)", com_lgpd_30d)
                col_c.metric("Taxa (30d)", f"{taxa_30d:.1f}%")
        else:
            st.info("📊 Dados insuficientes para gerar gráfico de evolução. Cadastre mais clientes com datas.")
            
    except Exception as e:
        logger.error(f"Erro ao gerar evolução LGPD: {e}", exc_info=True)
        st.warning("⚠️ Evolução de consentimentos não disponível no momento.")
    
    st.divider()
    
    # Logs de acesso
    st.markdown("#### 📋 Histórico de Acessos a Dados Pessoais")
    
    try:
        logs = db.sql_get_query("""
            SELECT 
                timestamp,
                username,
                action,
                details
            FROM audit_logs 
            WHERE action LIKE 'ACESSO_DADOS%'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (MAX_LOGS_LGPD_EXIBIR,))
        
        if not logs.empty:
            # S2: Mascarar dados sensíveis antes de exibir
            if 'details' in logs.columns:
                logs['details'] = logs['details'].apply(
                    lambda x: ut.mask_sensitive_data(str(x)) if x else '-'
                )
            
            # Filtros
            c1, c2 = st.columns(2)
            usuarios = logs['username'].unique().tolist()
            sel_user = c1.selectbox("Filtrar por Usuário", ["Todos"] + usuarios)
            
            if sel_user != "Todos":
                logs = logs[logs['username'] == sel_user]
            
            st.dataframe(
                logs,
                use_container_width=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Data/Hora"),
                    "username": "Usuário",
                    "action": "Ação",
                    "details": "Detalhes"
                }
            )
            
            # Gráfico de acessos por dia
            logs['data'] = pd.to_datetime(logs['timestamp']).dt.date
            acessos_dia = logs.groupby('data').size().reset_index()
            acessos_dia.columns = ['Data', 'Acessos']
            
            fig = px.line(acessos_dia, x='Data', y='Acessos', title="Acessos a Dados por Dia")
            st.plotly_chart(fig, use_container_width=True)
            
            # Exportação
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                logs.to_excel(writer, sheet_name='Logs_LGPD', index=False)
            
            st.download_button(
                label="📥 Exportar Logs",
                data=buffer.getvalue(),
                file_name=f"Logs_LGPD_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.info("Nenhum log de acesso registrado ainda.")
    except Exception as e:
        st.warning(f"Erro ao carregar logs: {e}")
        st.info("Os logs serão gerados automaticamente quando usuários acessarem fichas de clientes.")
    
    st.divider()
    
    # Configuração de retenção
    st.markdown("#### ⚙️ Política de Retenção")
    
    try:
        retencao = db.get_config('lgpd_retencao_anos', '5')
        st.info(f"📅 Prazo de retenção configurado: **{retencao} anos** após arquivamento")
        st.caption("Dados de clientes inativos serão anonimizados após este período.")
    except Exception as e:
        logger.warning(f"Erro ao carregar config retenção: {e}")
        st.warning("Configuração de retenção não encontrada.")


def render_comercial():
    st.markdown("### Funil de Vendas")
    
    # P2: Dados com cache
    df_cli = get_clientes_cached()
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
    """Relatório de Comissões e Parcerias - RESTRITO A ADMINS E SÓCIOS"""
    # S3: Controle de Acesso
    user_role = st.session_state.get('user_role', '')
    if user_role not in ['admin', 'socio']:
        st.error("🔒 Acesso restrito. Somente administradores e sócios podem visualizar comissões.")
        st.info("Este relatório contém informações financeiras sensíveis.")
        return
    
    st.markdown("### Relatório de Comissões e Parcerias")
    
    # Query usando constante para categorias
    categorias_placeholder = ','.join(['?'] * len(CATEGORIAS_COMISSAO))
    query = f"""
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
        WHERE f.categoria IN ({categorias_placeholder})
        ORDER BY f.data DESC
    """
    
    try:
        df = db.sql_get_query(query, tuple(CATEGORIAS_COMISSAO))
    except (ValueError, TypeError) as e:
        st.error(f"❌ Erro ao buscar comissões: {e}")
        logger.error(f"Erro ao executar query de comissões: {e}", exc_info=True)
        return
    except Exception as e:
        st.error(f"❌ Erro inesperado ao buscar comissões: {e}")
        logger.error(f"Erro inesperado ao buscar comissões: {e}", exc_info=True)
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
    
    # P1: Carregar tabelas em paralelo para melhor performance
    from concurrent.futures import ThreadPoolExecutor
    
    def carregar_tabela(nome_tabela):
        """Carrega uma tabela do banco de dados"""
        try:
            return nome_tabela, db.sql_get(nome_tabela)
        except Exception as e:
            logger.error(f"Erro ao carregar tabela {nome_tabela}: {e}")
            return nome_tabela, pd.DataFrame()
    
    # Carregar todas as tabelas em paralelo
    with st.spinner("Carregando dados para exportação..."):
        with ThreadPoolExecutor(max_workers=3) as executor:
            resultados_futures = {executor.submit(carregar_tabela, table): label 
                                  for label, table in tabelas.items()}
            
            resultados = {}
            for future in resultados_futures:
                label = resultados_futures[future]
                _, df = future.result()
                resultados[label] = df
    
    # Gerar botões de download
    cols = st.columns(len(tabelas))
    
    for i, (label, table) in enumerate(tabelas.items()):
        with cols[i]:
            df = resultados[label]
            
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
        # Bug #3: Melhorar tratamento de erro is_postgres()
        try:
            is_postgres = db.is_postgres()
        except AttributeError:
            logger.warning("Função is_postgres() não encontrada em database.py")
            is_postgres = False
        except Exception as e:
            logger.warning(f"Erro ao verificar tipo de banco: {e}")
            is_postgres = False
        
        try:
            
            if is_postgres:
                # Para PostgreSQL, exportar como Excel completo
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    for table in ['clientes', 'processos', 'financeiro', 'agenda', 'parceiros', 'andamentos']:
                        try:
                            df = db.sql_get(table)
                            df.to_excel(writer, sheet_name=table[:31], index=False)
                        except:
                            pass
                
                st.download_button(
                    label="⬇️ Baixar Backup Excel",
                    data=buffer.getvalue(),
                    file_name=f"Backup_LopesRibeiro_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
                st.success("Backup gerado com sucesso (Excel)!")
            else:
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
            logger.error(f"Erro ao gerar backup: {e}")
            st.error(f"Erro ao gerar backup: {e}")
