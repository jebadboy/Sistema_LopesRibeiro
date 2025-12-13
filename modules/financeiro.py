import streamlit as st
import database as db
import utils as ut
import pandas as pd
import io
import base64
import logging
import crypto
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import utils_recibo as ur
import urllib.parse
import utils_email
import email_templates

logger = logging.getLogger(__name__)

def render():
    st.markdown("<h1 style='color: var(--text-main);'>💰 Gestão Financeira</h1>", unsafe_allow_html=True)
    
    # --- DASHBOARD SUPERIOR (BIG NUMBERS) ---
    verificar_recorrencias() # Verificar e gerar recorrencias ao carregar
    render_dashboard_header()
    
    # --- ABAS PRINCIPAIS ---
    t1, t2, t3, t4 = st.tabs(["📝 Lançamentos & Extrato", "📊 Relatórios", "🧾 Recibo", "📥 Importar"])
    
    with t1:
        render_lancamentos_tab()
    
    with t2:
        render_relatorios_tab()

    with t3:
        render_recibos_tab()
    
    with t4:
        render_importar_tab()

def render_dashboard_header():
    """Renderiza os Big Numbers e Gráfico Resumo no topo."""
    df = db.sql_get("financeiro")
    
    if df.empty:
        st.info("👋 Bem-vindo ao seu Financeiro! Comece lançando sua primeira receita ou despesa na aba abaixo para ver os indicadores.")
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
    
    # 4. Comparativo com Mês Anterior
    mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
    ano_anterior = hoje.year if hoje.month > 1 else hoje.year - 1
    
    df_mes_ant = df[
        (df['vencimento'].dt.month == mes_anterior) & 
        (df['vencimento'].dt.year == ano_anterior)
    ]
    
    entradas_mes_ant = df_mes_ant[(df_mes_ant['tipo'] == 'Entrada') & (df_mes_ant['status_pagamento'] == 'Pago')]['valor'].sum()
    saidas_mes_ant = df_mes_ant[(df_mes_ant['tipo'] == 'Saída') & (df_mes_ant['status_pagamento'] == 'Pago')]['valor'].sum()
    saldo_mes_ant = entradas_mes_ant - saidas_mes_ant
    
    # Calcular variação percentual
    variacao_saldo = ((saldo_mes - saldo_mes_ant) / saldo_mes_ant * 100) if saldo_mes_ant != 0 else 0
    
    # 5. Alertas de Vencimentos Próximos (7 dias)
    data_limite_alerta = hoje + timedelta(days=7)
    vencimentos_proximos = df[
        (df['status_pagamento'] == 'Pendente') & 
        (df['vencimento'] >= pd.Timestamp(hoje.date())) &
        (df['vencimento'] <= pd.Timestamp(data_limite_alerta.date()))
    ]
    qtd_venc_proximos = len(vencimentos_proximos)
    valor_venc_proximos = vencimentos_proximos['valor'].sum()
    
    # Renderizar Metrics (expandido para 4 colunas)
    c1, c2, c3, c4 = st.columns(4)
    
    # Saldo com comparativo
    delta_saldo = f"{variacao_saldo:+.1f}% vs mês ant." if saldo_mes_ant != 0 else None
    c1.metric("Saldo do Mês (Caixa)", ut.formatar_moeda(saldo_mes), delta=delta_saldo)
    
    c2.metric("Previsão (Competência)", ut.formatar_moeda(previsao_mes), help="Considera tudo que vence neste mês, pago ou não.")
    c3.metric("Inadimplência Total", ut.formatar_moeda(inadimplencia), delta="-Atrasados" if inadimplencia > 0 else None, delta_color="inverse")
    c4.metric("📅 Venc. Próximos (7d)", f"{qtd_venc_proximos} ({ut.formatar_moeda(valor_venc_proximos)})", 
              delta="⚠️ Atenção" if qtd_venc_proximos > 0 else "✅ OK",
              delta_color="inverse" if qtd_venc_proximos > 0 else "normal")
    
    # Alerta visual se houver vencimentos
    if qtd_venc_proximos > 0:
        with st.expander(f"⚠️ {qtd_venc_proximos} vencimentos nos próximos 7 dias", expanded=False):
            for _, v in vencimentos_proximos.iterrows():
                icon = "💰" if v['tipo'] == 'Entrada' else "💸"
                try:
                    data_fmt = pd.to_datetime(v['vencimento']).strftime('%d/%m')
                except:
                    data_fmt = str(v['vencimento'])[:10]
                st.write(f"{icon} **{data_fmt}** - {v['descricao'][:30]}... | {ut.formatar_moeda(v['valor'])}")
    
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
        
        # Garantir colunas e ordem consistente
        if 'Entrada' not in chart_data.columns: chart_data['Entrada'] = 0
        if 'Saída' not in chart_data.columns: chart_data['Saída'] = 0
        
        # Reordenar para garantir cores corretas (Entrada primeiro = verde, Saída = vermelho)
        chart_data = chart_data[['Entrada', 'Saída']]
        st.bar_chart(chart_data, color=["#00cc96", "#ff4b4b"])

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
        
        categoria = None
        centro_custo = None
        id_cliente = None
        id_processo_sel = None  # Inicializado para evitar erro de escopo
        
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
                
                # Seleção de Processo para vincular (e ativar repasse)
                id_processo_sel = None
                if cliente_nome != "Avulso":
                    # Buscar processos do cliente
                    cli_id_temp = dfc[dfc['nome'] == cliente_nome].iloc[0]['id']
                    df_procs = db.sql_get_query("SELECT id, acao FROM processos WHERE id_cliente=?", (cli_id_temp,))
                    if not df_procs.empty:
                        lista_procs = ["Nenhum"] + df_procs['acao'].tolist()
                        
                        # Tentar pre-fill
                        idx_proc = 0
                        if pre_fill.get('id_processo'):
                             proc_row = df_procs[df_procs['id'] == pre_fill['id_processo']]
                             if not proc_row.empty:
                                 acao_nome = proc_row.iloc[0]['acao']
                                 if acao_nome in lista_procs:
                                     idx_proc = lista_procs.index(acao_nome)
                        
                        proc_sel = st.selectbox("Vincular Processo", lista_procs, index=idx_proc)
                        if proc_sel != "Nenhum":
                            id_processo_sel = int(df_procs[df_procs['acao'] == proc_sel].iloc[0]['id'])

                centro_custo = "Receita Operacional"
            else:
                centro_custo = "Outros"
        
        # Campos Comuns
        desc_val = pre_fill.get('descricao', "")
        descricao = st.text_input("Descrição (Ex: Honorários Divórcio)", value=desc_val)
        valor = st.number_input("Valor Total (R$)", min_value=0.01, step=100.0)
        data_venc = st.date_input("Vencimento Inicial", value=datetime.now())
        
        # Link do Comprovante
        comprovante_link = st.text_input("Link do Comprovante (Google Drive)", placeholder="Cole o link do arquivo ou pasta aqui")
        
        # Parcelamento (Para Entradas E Saídas)
        parcelas = st.number_input("Parcelar em quantas vezes?", min_value=1, max_value=60, value=1, key="parcelas_input")
        if parcelas > 1:
            st.caption(f"📑 Serão gerados {parcelas} lançamentos de {ut.formatar_moeda(valor/parcelas)}")
        
        c1, c2, c3, c4 = st.columns(4)
        status = c1.selectbox("Status", ["Pendente", "Pago"])
        responsavel = c2.selectbox("Responsável", ["Eduardo", "Sheila", "Sistema"])
        meio_pagamento = c3.selectbox("Meio de Pagamento", ["PIX", "Dinheiro", "Cartão", "Boleto", "Transferência", "Outro"])
        is_recorrente = c4.checkbox("Recorrente?")
        
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
                # Verificação de Duplicidade (Simples)
                duplicado = db.sql_get_query(
                    "SELECT id FROM financeiro WHERE descricao = ? AND valor = ? AND vencimento = ? AND tipo = ?",
                    (descricao, round(valor_parcela, 2), data_base.strftime("%Y-%m-%d"), tipo)
                )
                if not duplicado.empty:
                    st.warning("⚠️ Atenção: Já existe um lançamento idêntico (mesma descrição, valor, data e tipo).")
                    if not st.checkbox("Confirmar lançamento duplicado mesmo assim?", key="dupl_confirm"):
                        st.stop()
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
                        "id_processo": id_processo_sel,
                        "centro_custo": centro_custo,
                        "recorrente": 1 if is_recorrente else 0,
                        "recorrencia": "Mensal" if is_recorrente else None,
                        "data_pagamento": datetime.now().strftime("%Y-%m-%d") if status == "Pago" else None,
                        "meio_pagamento": meio_pagamento,
                        "comprovante_link": comprovante_link
                    }
                    
                    db.crud_insert("financeiro", dados, f"Lançamento {tipo}")

                    # --- LÓGICA DE REPASSE DE PARCERIA ---
                    # CORREÇÃO: Calcular repasse apenas na PRIMEIRA parcela usando o valor TOTAL
                    # Isso evita múltiplos lançamentos de repasse em parcelamentos
                    if tipo == "Entrada" and id_processo_sel and i == 0:  # Apenas na primeira iteração
                        # Buscar dados do processo
                        proc_data = db.sql_get_query("SELECT parceiro_nome, parceiro_percentual FROM processos WHERE id=?", (id_processo_sel,))
                        if not proc_data.empty:
                            p_nome = proc_data.iloc[0]['parceiro_nome']
                            p_pct = proc_data.iloc[0]['parceiro_percentual']
                            
                            if p_nome and p_pct > 0:
                                # Usar VALOR TOTAL, não valor da parcela
                                valor_repasse = round(valor * (p_pct / 100), 2)
                                
                                # Criar lançamento de saída (Repasse) - único para todo o parcelamento
                                dados_repasse = {
                                    "data": datetime.now().strftime("%Y-%m-%d"),
                                    "tipo": "Saída",
                                    "categoria": "Repasse de Parceria",
                                    "descricao": f"Repasse {p_nome} - {descricao}",  # Sem número de parcela
                                    "valor": valor_repasse,
                                    "responsavel": "Sistema",
                                    "status_pagamento": "Pendente",
                                    "vencimento": data_base.strftime("%Y-%m-%d"),  # Vencimento da primeira parcela
                                    "id_processo": id_processo_sel,
                                    "centro_custo": "Repasse",
                                    "recorrente": 0
                                }
                                db.crud_insert("financeiro", dados_repasse, f"Repasse automático para {p_nome}")
                                st.toast(f"💸 Repasse de R$ {valor_repasse} ({p_pct}% de R$ {valor}) gerado para {p_nome}!", icon="🤝")
                    # -------------------------------------
                
                st.success(f"{parcelas} lançamento(s) realizado(s) com sucesso!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

def render_extrato_lista():
    df = db.sql_get("financeiro", "vencimento DESC")
    
    if df.empty:
        st.info("📭 Nenhum lançamento encontrado.")
        return
    
    # Converter datas para filtros
    df['vencimento_dt'] = pd.to_datetime(df['vencimento'], errors='coerce')
    
    # ===== FILTROS AVANÇADOS =====
    with st.expander("🔍 Filtros Avançados", expanded=False):
        # Linha 1: Busca e Período
        col_busca, col_data_ini, col_data_fim = st.columns([2, 1, 1])
        with col_busca:
            busca_texto = st.text_input("🔎 Buscar por descrição", placeholder="Digite para buscar...", key="fin_busca")
        with col_data_ini:
            data_ini = st.date_input("Data início", value=None, key="fin_data_ini")
        with col_data_fim:
            data_fim = st.date_input("Data fim", value=None, key="fin_data_fim")
        
        # Linha 2: Tipo, Categoria, Status
        c1, c2, c3 = st.columns(3)
        f_tipo = c1.multiselect("Tipo", df['tipo'].unique(), key="fin_tipo")
        f_cat = c2.multiselect("Categoria", df['categoria'].dropna().unique(), key="fin_cat")
        f_status = c3.multiselect("Status", df['status_pagamento'].unique(), key="fin_status")
    
    # ===== APLICAR FILTROS =====
    df_filtrado = df.copy()
    
    if busca_texto:
        df_filtrado = df_filtrado[df_filtrado['descricao'].str.contains(busca_texto, case=False, na=False)]
    if data_ini:
        df_filtrado = df_filtrado[df_filtrado['vencimento_dt'] >= pd.Timestamp(data_ini)]
    if data_fim:
        df_filtrado = df_filtrado[df_filtrado['vencimento_dt'] <= pd.Timestamp(data_fim)]
    if f_tipo:
        df_filtrado = df_filtrado[df_filtrado['tipo'].isin(f_tipo)]
    if f_cat:
        df_filtrado = df_filtrado[df_filtrado['categoria'].isin(f_cat)]
    if f_status:
        df_filtrado = df_filtrado[df_filtrado['status_pagamento'].isin(f_status)]
    
    # ===== RESUMO DOS FILTROS =====
    total_entradas = df_filtrado[df_filtrado['tipo'] == 'Entrada']['valor'].sum()
    total_saidas = df_filtrado[df_filtrado['tipo'] == 'Saída']['valor'].sum()
    saldo = total_entradas - total_saidas
    
    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    col_res1.metric("Registros", len(df_filtrado))
    col_res2.metric("🟢 Entradas", ut.formatar_moeda(total_entradas))
    col_res3.metric("🔴 Saídas", ut.formatar_moeda(total_saidas))
    col_res4.metric("Saldo", ut.formatar_moeda(saldo))
    
    st.divider()
    
    # ===== PAGINAÇÃO =====
    ITENS_POR_PAGINA = 15
    total_paginas = max(1, (len(df_filtrado) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    
    col_pg1, col_pg2, col_pg3 = st.columns([1, 2, 1])
    with col_pg2:
        pagina_atual = st.number_input(f"Página (de {total_paginas})", min_value=1, max_value=total_paginas, value=1, key="fin_pagina")
    
    inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    df_pagina = df_filtrado.iloc[inicio:fim]
    
    # ===== EXIBIÇÃO =====
    for index, row in df_pagina.iterrows():
        icon = "💰" if row['tipo'] == "Entrada" else "💸"
        status_icon = "✅" if row['status_pagamento'] == "Pago" else "⏳"
        
        # Formatar data para exibição
        try:
            data_fmt = pd.to_datetime(row['vencimento']).strftime('%d/%m/%Y')
        except:
            data_fmt = str(row['vencimento'])[:10]
        
        with st.expander(f"{icon} {status_icon} {data_fmt} | {row['descricao'][:40]}... | {ut.formatar_moeda(row['valor'])}"):
            # ===== MODO EDIÇÃO =====
            edit_key = f"edit_mode_{row['id']}"
            
            if st.session_state.get(edit_key, False):
                # Formulário de edição
                with st.form(f"form_edit_{row['id']}"):
                    st.markdown("**✏️ Editando Lançamento**")
                    
                    col_e1, col_e2 = st.columns(2)
                    new_desc = col_e1.text_input("Descrição", value=row['descricao'])
                    new_valor = col_e2.number_input("Valor", value=float(row['valor']), min_value=0.01)
                    
                    col_e3, col_e4 = st.columns(2)
                    new_venc = col_e3.date_input("Vencimento", value=pd.to_datetime(row['vencimento']).date())
                    new_status = col_e4.selectbox("Status", ["Pendente", "Pago"], index=0 if row['status_pagamento'] == "Pendente" else 1)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    if col_btn1.form_submit_button("💾 Salvar", type="primary"):
                        db.crud_update("financeiro", {
                            "descricao": new_desc,
                            "valor": new_valor,
                            "vencimento": new_venc.strftime("%Y-%m-%d"),
                            "status_pagamento": new_status,
                            "data_pagamento": datetime.now().strftime("%Y-%m-%d") if new_status == "Pago" else None
                        }, "id = ?", (row['id'],), "Edição de lançamento")
                        st.session_state[edit_key] = False
                        st.rerun()
                    
                    if col_btn2.form_submit_button("❌ Cancelar"):
                        st.session_state[edit_key] = False
                        st.rerun()
            else:
                # Exibição normal
                c_det1, c_det2 = st.columns(2)
                
                with c_det1:
                    st.write(f"**Categoria:** {row['categoria']}")
                    st.write(f"**Centro de Custo:** {row.get('centro_custo', 'N/A')}")
                    st.write(f"**Responsável:** {row.get('responsavel', 'N/A')}")
                    if row.get('meio_pagamento'):
                        st.write(f"**Pagamento:** {row['meio_pagamento']}")
                    if row.get('comprovante_link'):
                        st.markdown(f"[📄 Ver Comprovante]({row['comprovante_link']})")
                
                with c_det2:
                    # Ações rápidas
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    # Botão Editar
                    if col_act1.button("✏️ Editar", key=f"btn_edit_{row['id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()
                    
                    # Alterar Status rápido
                    if row['status_pagamento'] == "Pendente":
                        if col_act2.button("✅ Pagar", key=f"pagar_{row['id']}"):
                            db.crud_update("financeiro", {
                                "status_pagamento": "Pago",
                                "data_pagamento": datetime.now().strftime("%Y-%m-%d")
                            }, "id = ?", (row['id'],), "Baixa rápida")
                            st.rerun()
                    else:
                        if col_act2.button("↩️ Estornar", key=f"estornar_{row['id']}"):
                            db.crud_update("financeiro", {
                                "status_pagamento": "Pendente",
                                "data_pagamento": None
                            }, "id = ?", (row['id'],), "Estorno de pagamento")
                            st.rerun()
                    
                    # Excluir
                    if col_act3.button("🗑️", key=f"del_{row['id']}", help="Excluir"):
                        db.crud_delete("financeiro", "id = ?", (row['id'],), "Exclusão")
                        st.rerun()
                    
                    st.divider()
                    
                    # Ações adicionais
                    if row['status_pagamento'] == 'Pago' and row['tipo'] == 'Entrada':
                        if st.button("📄 Emitir Recibo", key=f"rec_{row['id']}", use_container_width=True):
                            st.session_state['recibo_pre_fill'] = {
                                'id_lancamento': row['id'],
                                'valor': row['valor'],
                                'descricao': row['descricao'],
                                'id_cliente': row.get('id_cliente'),
                                'data_pagamento': row.get('data_pagamento')
                            }
                            st.info("Vá para a aba 'Emitir Recibo'.")
                    
                    if row['status_pagamento'] == 'Pendente' and row['tipo'] == 'Entrada' and row.get('id_cliente'):
                        cliente_data = db.sql_get_query("SELECT nome, email FROM clientes WHERE id = ?", (row['id_cliente'],))
                        if not cliente_data.empty and cliente_data.iloc[0].get('email'):
                            if st.button("📧 Cobrança", key=f"cob_{row['id']}", use_container_width=True):
                                cli = cliente_data.iloc[0]
                                try:
                                    data_venc = datetime.strptime(str(row['vencimento'])[:10], '%Y-%m-%d').date()
                                    dias_atraso = max(0, (datetime.now().date() - data_venc).days)
                                except Exception as e:
                                    logger.warning(f"Erro ao calcular dias atraso: {e}")
                                    dias_atraso = 0
                                
                                venc_fmt = datetime.strptime(str(row['vencimento'])[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                                corpo = email_templates.template_lembrete_pagamento(cli['nome'], row['descricao'], float(row['valor']), venc_fmt, dias_atraso)
                                sucesso, erro = utils_email.enviar_email(cli['email'], "Lembrete de Pagamento - Lopes & Ribeiro", corpo)
                                if sucesso:
                                    st.success(f"✅ Lembrete enviado!")
                                else:
                                    st.error(f"❌ Falha: {erro}")

def render_relatorios_tab():
    st.markdown("### 📊 Análise Financeira Detalhada")
    
    df = db.sql_get("financeiro")
    if df.empty:
        st.warning("Sem dados para análise.")
        return
        
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['vencimento'] = pd.to_datetime(df['vencimento'], errors='coerce')
    
    # Sub-abas de Relatórios
    tab_visao, tab_dre, tab_graficos, tab_inadim, tab_export = st.tabs(["📈 Visão Geral", "📊 DRE", "🥧 Gráficos", "⚠️ Inadimplência", "📥 Exportar"])
    
    with tab_visao:
        # Filtro de Período
        c1, c2 = st.columns(2)
        ano = c1.selectbox("Ano", sorted(df['vencimento'].dt.year.dropna().unique(), reverse=True))
        
        df_ano = df[df['vencimento'].dt.year == ano]
        
        # 1. Despesas por Categoria
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
    
    with tab_dre:
        st.markdown("#### 📊 Demonstrativo de Resultado (DRE Simplificado)")
        
        # Seleção de período
        col_dre1, col_dre2 = st.columns(2)
        mes_dre = col_dre1.selectbox("Mês", list(range(1, 13)), index=datetime.now().month - 1, format_func=lambda x: ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][x-1])
        ano_dre = col_dre2.selectbox("Ano", sorted(df['vencimento'].dt.year.dropna().unique(), reverse=True), key="dre_ano")
        
        df_dre = df[
            (df['vencimento'].dt.month == mes_dre) & 
            (df['vencimento'].dt.year == ano_dre) &
            (df['status_pagamento'] == 'Pago')
        ]
        
        # Calcular valores
        receita_bruta = df_dre[df_dre['tipo'] == 'Entrada']['valor'].sum()
        
        # Despesas por categoria
        df_desp = df_dre[df_dre['tipo'] == 'Saída']
        desp_pessoal = df_desp[df_desp['categoria'].isin(['Pessoal', 'Salários'])]['valor'].sum()
        desp_admin = df_desp[df_desp['categoria'].isin(['Aluguel', 'Energia/Água', 'Internet', 'Impostos'])]['valor'].sum()
        desp_operacional = df_desp[df_desp['categoria'].isin(['Software', 'Marketing', 'Outros'])]['valor'].sum()
        desp_repasse = df_desp[df_desp['categoria'] == 'Repasse de Parceria']['valor'].sum()
        
        total_despesas = df_desp['valor'].sum()
        lucro_liquido = receita_bruta - total_despesas
        margem = (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
        
        # Exibir DRE
        st.markdown("---")
        dre_data = {
            "Descrição": [
                "📈 RECEITA BRUTA",
                "  ├─ Honorários",
                "  ├─ Sucumbência",
                "  └─ Outros",
                "📉 (-) DESPESAS",
                "  ├─ Pessoal",
                "  ├─ Administrativo",
                "  ├─ Operacional",
                "  └─ Repasses",
                "━━━━━━━━━━━━━━━━━━",
                "💰 LUCRO LÍQUIDO",
                "📊 MARGEM (%)"
            ],
            "Valor": [
                ut.formatar_moeda(receita_bruta),
                ut.formatar_moeda(df_dre[(df_dre['tipo'] == 'Entrada') & (df_dre['categoria'] == 'Honorários')]['valor'].sum()),
                ut.formatar_moeda(df_dre[(df_dre['tipo'] == 'Entrada') & (df_dre['categoria'] == 'Sucumbência')]['valor'].sum()),
                ut.formatar_moeda(df_dre[(df_dre['tipo'] == 'Entrada') & (~df_dre['categoria'].isin(['Honorários', 'Sucumbência']))]['valor'].sum()),
                ut.formatar_moeda(total_despesas),
                ut.formatar_moeda(desp_pessoal),
                ut.formatar_moeda(desp_admin),
                ut.formatar_moeda(desp_operacional),
                ut.formatar_moeda(desp_repasse),
                "",
                ut.formatar_moeda(lucro_liquido),
                f"{margem:.1f}%"
            ]
        }
        
        st.dataframe(pd.DataFrame(dre_data), use_container_width=True, hide_index=True)
        
        # Indicadores visuais
        col_ind1, col_ind2, col_ind3 = st.columns(3)
        col_ind1.metric("Receita", ut.formatar_moeda(receita_bruta))
        col_ind2.metric("Despesas", ut.formatar_moeda(total_despesas))
        col_ind3.metric("Lucro", ut.formatar_moeda(lucro_liquido), delta=f"{margem:.1f}%")
    
    with tab_graficos:
        st.markdown("#### 🥧 Gráficos de Distribuição")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("##### Despesas por Categoria")
            df_desp_ano = df_ano[df_ano['tipo'] == 'Saída']
            if not df_desp_ano.empty:
                desp_cat = df_desp_ano.groupby('categoria')['valor'].sum()
                
                # Criar dados para gráfico de pizza (usando plotly)
                import plotly.express as px
                fig1 = px.pie(
                    values=desp_cat.values, 
                    names=desp_cat.index,
                    title="Distribuição de Despesas",
                    color_discrete_sequence=px.colors.sequential.Reds
                )
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Sem despesas no período.")
        
        with col_graf2:
            st.markdown("##### Receitas por Origem")
            df_rec_ano = df_ano[df_ano['tipo'] == 'Entrada']
            if not df_rec_ano.empty:
                rec_cat = df_rec_ano.groupby('categoria')['valor'].sum()
                
                fig2 = px.pie(
                    values=rec_cat.values, 
                    names=rec_cat.index,
                    title="Distribuição de Receitas",
                    color_discrete_sequence=px.colors.sequential.Greens
                )
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sem receitas no período.")
        
        # Gráfico de evolução mensal
        st.markdown("##### 📈 Evolução Mensal")
        df_evol = df[df['status_pagamento'] == 'Pago'].copy()
        if not df_evol.empty:
            df_evol['mes'] = df_evol['vencimento'].dt.strftime('%Y-%m')
            evol_data = df_evol.groupby(['mes', 'tipo'])['valor'].sum().unstack().fillna(0)
            
            if 'Entrada' not in evol_data.columns: evol_data['Entrada'] = 0
            if 'Saída' not in evol_data.columns: evol_data['Saída'] = 0
            
            evol_data['Lucro'] = evol_data['Entrada'] - evol_data['Saída']
            
            fig3 = px.line(
                evol_data.reset_index(),
                x='mes',
                y=['Entrada', 'Saída', 'Lucro'],
                title="Evolução Financeira",
                labels={'value': 'Valor (R$)', 'mes': 'Mês'},
                color_discrete_map={'Entrada': '#00cc96', 'Saída': '#ff4b4b', 'Lucro': '#636efa'}
            )
            st.plotly_chart(fig3, use_container_width=True)
    
    with tab_inadim:
        st.markdown("#### ⚠️ Relatório de Inadimplência")
        st.caption("Receitas pendentes com vencimento no passado")
        
        hoje = datetime.now().date()
        
        # Filtrar inadimplentes
        df_inadim = df[
            (df['tipo'] == 'Entrada') & 
            (df['status_pagamento'] == 'Pendente') & 
            (df['vencimento'].dt.date < hoje)
        ].copy()
        
        if df_inadim.empty:
            st.success("🎉 Nenhuma inadimplência encontrada!")
        else:
            # Calcular dias de atraso
            df_inadim['dias_atraso'] = df_inadim['vencimento'].apply(
                lambda x: (hoje - x.date()).days if pd.notna(x) else 0
            )
            
            # Buscar nome do cliente
            def get_cliente_nome(id_cli):
                if pd.isna(id_cli):
                    return "Avulso"
                cli = db.sql_get_query("SELECT nome FROM clientes WHERE id=?", (int(id_cli),))
                return cli.iloc[0]['nome'] if not cli.empty else "Avulso"
            
            df_inadim['cliente'] = df_inadim['id_cliente'].apply(get_cliente_nome)
            
            # Resumo
            total_inadim = df_inadim['valor'].sum()
            qtd_inadim = len(df_inadim)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total em Atraso", ut.formatar_moeda(total_inadim))
            c2.metric("Quantidade", qtd_inadim)
            c3.metric("Atraso Médio", f"{int(df_inadim['dias_atraso'].mean())} dias")
            
            st.divider()
            
            # Tabela detalhada
            df_exibir = df_inadim[['cliente', 'descricao', 'valor', 'vencimento', 'dias_atraso']].copy()
            df_exibir.columns = ['Cliente', 'Descrição', 'Valor', 'Vencimento', 'Dias Atraso']
            df_exibir['Valor'] = df_exibir['Valor'].apply(ut.formatar_moeda)
            df_exibir['Vencimento'] = df_exibir['Vencimento'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
    
    with tab_export:
        st.markdown("#### 📥 Exportar Dados para Excel")
        
        tipo_export = st.radio("O que deseja exportar?", 
                               ["Extrato Completo", "Apenas Inadimplência", "Resumo por Categoria"],
                               horizontal=True)
        
        if st.button("📥 Gerar Excel", type="primary"):
            import io
            
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                if tipo_export == "Extrato Completo":
                    df_export = df.copy()
                    df_export['vencimento'] = df_export['vencimento'].dt.strftime('%d/%m/%Y')
                    df_export.to_excel(writer, sheet_name='Extrato', index=False)
                    
                elif tipo_export == "Apenas Inadimplência":
                    hoje = datetime.now().date()
                    df_inadim = df[
                        (df['tipo'] == 'Entrada') & 
                        (df['status_pagamento'] == 'Pendente') & 
                        (df['vencimento'].dt.date < hoje)
                    ].copy()
                    df_inadim['vencimento'] = df_inadim['vencimento'].dt.strftime('%d/%m/%Y')
                    df_inadim.to_excel(writer, sheet_name='Inadimplencia', index=False)
                    
                else:  # Resumo por Categoria
                    receitas = df[df['tipo'] == 'Entrada'].groupby('categoria')['valor'].sum().reset_index()
                    receitas.columns = ['Categoria', 'Total Receitas']
                    
                    despesas = df[df['tipo'] == 'Saída'].groupby('categoria')['valor'].sum().reset_index()
                    despesas.columns = ['Categoria', 'Total Despesas']
                    
                    receitas.to_excel(writer, sheet_name='Receitas', index=False)
                    despesas.to_excel(writer, sheet_name='Despesas', index=False)
            
            buffer.seek(0)
            
            nome_arquivo = f"Financeiro_{tipo_export.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            st.download_button(
                label="⬇️ Baixar Excel",
                data=buffer,
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Arquivo gerado com sucesso!")
        
        st.divider()
        
        # Relatório PDF
        st.markdown("#### 📄 Relatório em PDF")
        st.caption("Gere um relatório resumido em PDF para enviar aos sócios")
        
        col_pdf1, col_pdf2 = st.columns(2)
        mes_pdf = col_pdf1.selectbox("Mês do Relatório", list(range(1, 13)), 
                                      index=datetime.now().month - 1,
                                      format_func=lambda x: ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                                                             'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][x-1],
                                      key="pdf_mes")
        ano_pdf = col_pdf2.selectbox("Ano", sorted(df['vencimento'].dt.year.dropna().unique(), reverse=True), key="pdf_ano")
        
        if st.button("📄 Gerar Relatório PDF", type="primary"):
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=1)
            elements.append(Paragraph("RELATÓRIO FINANCEIRO", title_style))
            elements.append(Paragraph(f"Mês: {mes_pdf}/{ano_pdf}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Filtrar dados do mês
            df_pdf = df[
                (df['vencimento'].dt.month == mes_pdf) & 
                (df['vencimento'].dt.year == ano_pdf) &
                (df['status_pagamento'] == 'Pago')
            ]
            
            receitas = df_pdf[df_pdf['tipo'] == 'Entrada']['valor'].sum()
            despesas = df_pdf[df_pdf['tipo'] == 'Saída']['valor'].sum()
            lucro = receitas - despesas
            margem = (lucro / receitas * 100) if receitas > 0 else 0
            
            # Tabela resumo
            data = [
                ["Descrição", "Valor"],
                ["Receita Total", f"R$ {receitas:,.2f}"],
                ["Despesas Total", f"R$ {despesas:,.2f}"],
                ["Lucro Líquido", f"R$ {lucro:,.2f}"],
                ["Margem", f"{margem:.1f}%"]
            ]
            
            table = Table(data, colWidths=[200, 150])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
            
            # Rodapé
            elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
            elements.append(Paragraph("Lopes & Ribeiro Advocacia", styles['Normal']))
            
            doc.build(elements)
            pdf_buffer.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Relatório PDF",
                data=pdf_buffer,
                file_name=f"Relatorio_Financeiro_{mes_pdf}_{ano_pdf}.pdf",
                mime="application/pdf"
            )
            st.success("Relatório PDF gerado!")


def render_recibos_tab():
    st.markdown("### 🧾 Emitir Recibo de Honorários")
    
    # Verificar pre-fill da session_state
    pre_fill = st.session_state.get('recibo_pre_fill', {})
    
    origem = st.radio("Origem dos Dados", ["Selecionar Cliente Cadastrado", "Selecionar Lançamento Existente", "Preenchimento Manual"], horizontal=True)
    
    dados_recibo = {}
    
    if origem == "Selecionar Cliente Cadastrado":
        dfc = db.sql_get("clientes")
        if dfc.empty:
            st.warning("Nenhum cliente cadastrado.")
            return
            
        lista_clientes = dfc['nome'].tolist()
        sel_cliente = st.selectbox("Selecione o Cliente", lista_clientes)
        
        if sel_cliente:
            cli_row = dfc[dfc['nome'] == sel_cliente].iloc[0]
            
            c1, c2 = st.columns(2)
            nome_final = c1.text_input("Nome do Pagador", value=cli_row['nome'])
            
            # Descriptografar CPF se estiver criptografado
            cpf_raw = cli_row['cpf_cnpj'] if cli_row['cpf_cnpj'] else ""
            cpf_display = ""
            cpf_precisa_manual = False
            
            if cpf_raw:
                cpf_str = str(cpf_raw)
                # Verificar se está criptografado (ENC: ou apenas começa com ENC)
                if cpf_str.startswith("ENC:"):
                    # Formato padrão - tentar descriptografar
                    try:
                        cpf_decrypted = crypto.decrypt(cpf_raw)
                        if cpf_decrypted and not str(cpf_decrypted).startswith("ENC"):
                            cpf_display = cpf_decrypted
                        else:
                            cpf_precisa_manual = True
                    except Exception as e:
                        logger.warning(f"Erro ao descriptografar CPF: {e}")
                        cpf_precisa_manual = True
                elif cpf_str.startswith("ENC") or cpf_str.startswith("gAAAA"):
                    # Formato antigo ou base64 direto - não conseguimos descriptografar
                    cpf_precisa_manual = True
                else:
                    # Não está criptografado - usar diretamente
                    cpf_display = cpf_raw
            
            if cpf_precisa_manual:
                st.caption("⚠️ CPF criptografado - insira manualmente se necessário")
            
            cpf_final = c2.text_input("CPF/CNPJ", value=cpf_display, placeholder="Digite o CPF/CNPJ")
            
            c3, c4 = st.columns(2)
            valor = c3.number_input("Valor (R$)", min_value=0.01, step=100.0)
            data = c4.date_input("Data do Pagamento", value=datetime.now())
            
            desc = st.text_area("Descrição (Referente a)", "Honorários Advocatícios")
            
            dados_recibo = {
                'nome_cliente': nome_final,
                'cpf_cliente': cpf_final,
                'valor': valor,
                'descricao': desc,
                'data': data
            }

    elif origem == "Selecionar Lançamento Existente":
        # Buscar entradas
        df = db.sql_get("financeiro", "vencimento DESC")
        df_entradas = df[df['tipo'] == 'Entrada']
        
        if df_entradas.empty:
            st.warning("Nenhuma entrada registrada para gerar recibo.")
            return
            
        # Criar label para selectbox
        df_entradas['label'] = df_entradas.apply(lambda x: f"{x['vencimento']} | {x['descricao']} | R$ {x['valor']}", axis=1)
        
        # Tentar selecionar automaticamente se vier do pre-fill
        idx_sel = 0
        if pre_fill:
            # Tentar achar o label correspondente
            row_pf = df_entradas[df_entradas['id'] == pre_fill['id_lancamento']]
            if not row_pf.empty:
                lbl = row_pf.iloc[0]['label']
                labels = df_entradas['label'].unique().tolist()
                if lbl in labels:
                    idx_sel = labels.index(lbl)
        
        sel_lanc = st.selectbox("Selecione o Lançamento", df_entradas['label'].unique(), index=idx_sel)
        
        if sel_lanc:
            row = df_entradas[df_entradas['label'] == sel_lanc].iloc[0]
            
            # Tentar buscar dados do cliente se vinculado
            nome_cli = "Cliente Avulso"
            cpf_cli = ""
            
            if row['id_cliente']:
                cli = db.sql_get_query("SELECT * FROM clientes WHERE id = ?", (int(row['id_cliente']),))
                if not cli.empty:
                    nome_cli = cli.iloc[0]['nome']
                    # Descriptografar CPF com fallback
                    cpf_raw = cli.iloc[0]['cpf_cnpj'] if cli.iloc[0]['cpf_cnpj'] else ""
                    if cpf_raw:
                        try:
                            cpf_decrypted = crypto.decrypt(cpf_raw)
                            if cpf_decrypted and not str(cpf_decrypted).startswith("ENC"):
                                cpf_cli = cpf_decrypted
                        except:
                            pass
            
            st.info(f"Dados carregados: {nome_cli} - R$ {row['valor']}")
            
            # Permitir edição
            c1, c2 = st.columns(2)
            nome_final = c1.text_input("Nome do Pagador", value=nome_cli)
            cpf_final = c2.text_input("CPF/CNPJ", value=cpf_cli, placeholder="Digite o CPF/CNPJ")
            
            dados_recibo = {
                'nome_cliente': nome_final,
                'cpf_cliente': cpf_final,
                'valor': float(row['valor']),
                'descricao': row['descricao'],
                'data': row['data_pagamento'] if row['data_pagamento'] else datetime.now()
            }
            
    else: # Manual
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do Pagador")
        cpf = c2.text_input("CPF/CNPJ")
        
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor (R$)", min_value=0.01)
        data = c4.date_input("Data do Pagamento", value=datetime.now())
        
        desc = st.text_area("Descrição (Referente a)", "Honorários Advocatícios")
        
        dados_recibo = {
            'nome_cliente': nome,
            'cpf_cliente': cpf,
            'valor': valor,
            'descricao': desc,
            'data': data
        }

    st.divider()
    
    if st.button("📄 Gerar Recibo PDF", type="primary"):
        if not dados_recibo.get('nome_cliente'):
            st.error("Nome do cliente é obrigatório.")
            return
            
        pdf_buffer = ur.gerar_recibo_pdf(dados_recibo)
        
        # Colunas para Download e WhatsApp
        col_down, col_whats = st.columns(2)
        
        # 1. Download
        nome_arquivo = f"Recibo_{dados_recibo['nome_cliente'].replace(' ', '_')}.pdf"
        col_down.download_button(
            label="⬇️ Baixar PDF",
            data=pdf_buffer,
            file_name=nome_arquivo,
            mime="application/pdf"
        )
        
        # 2. WhatsApp
        msg = f"Olá {dados_recibo['nome_cliente']}, segue em anexo o recibo de pagamento no valor de R$ {dados_recibo['valor']:,.2f} referente a {dados_recibo['descricao']}."
        msg_encoded = urllib.parse.quote(msg)
        link_wa = f"https://wa.me/?text={msg_encoded}"
        
        col_whats.markdown(f"""
            <a href="{link_wa}" target="_blank">
                <button style="
                    background-color:#25D366; 
                    color:white; 
                    border:none; 
                    padding:0.5rem 1rem; 
                    border-radius:0.5rem; 
                    cursor:pointer;
                    font-weight:bold;
                    width:100%;">
                    📱 Compartilhar no WhatsApp
                </button>
            </a>
            <div style="font-size:0.8em; color:gray; margin-top:5px;">
                *Baixe o PDF primeiro e anexe na conversa.
            </div>
        """, unsafe_allow_html=True)
        
        # Preview
        st.markdown("### Pré-visualização")
        import base64
        base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)


def verificar_recorrencias():
    """Verifica e gera lançamentos recorrentes."""
    try:
        # Buscar lançamentos recorrentes ativos
        df_rec = db.sql_get_query("SELECT * FROM financeiro WHERE recorrente=1")
        
        if df_rec.empty:
            return

        hoje = datetime.now().date()
        
        for idx, row in df_rec.iterrows():
            venc_atual = datetime.strptime(row['vencimento'], '%Y-%m-%d').date()
            
            # Se vencimento é passado ou hoje, verificar se precisa gerar o próximo
            # Regra: Gerar sempre 1 mês para frente se não existir
            
            proximo_venc = venc_atual + relativedelta(months=1)
            
            # Verificar se já existe lançamento com mesma descrição e vencimento (aprox)
            # Para evitar duplicidade, checamos descrição exata e data exata
            
            exists = db.sql_get_query(
                "SELECT id FROM financeiro WHERE descricao = ? AND vencimento = ?", 
                (row['descricao'], proximo_venc.strftime('%Y-%m-%d'))
            )
            
            if exists.empty:
                # Se não existe e a data original já passou (ou está próxima, ex: 5 dias antes)
                # Vamos gerar se o próximo vencimento for até daqui a 35 dias (para garantir que gere o do mês seguinte)
                
                limite_geracao = hoje + timedelta(days=35)
                
                if proximo_venc <= limite_geracao:
                    # Clonar dados
                    novos_dados = {
                        "data": hoje.strftime("%Y-%m-%d"),
                        "tipo": row['tipo'],
                        "categoria": row['categoria'],
                        "descricao": row['descricao'],
                        "valor": row['valor'],
                        "responsavel": "Sistema (Recorrência)",
                        "status_pagamento": "Pendente",
                        "vencimento": proximo_venc.strftime("%Y-%m-%d"),
                        "id_cliente": row['id_cliente'],
                        "id_processo": row['id_processo'],
                        "centro_custo": row['centro_custo'],
                        "recorrente": 1, # O novo também é recorrente para continuar a cadeia
                        "recorrencia": row['recorrencia'],
                        "comprovante_link": None
                    }
                    
                    db.crud_insert("financeiro", novos_dados, f"Recorrência gerada: {row['descricao']}")
                    # Opcional: Desativar recorrencia do anterior? Não, pois usamos a cadeia.
                    # Mas para evitar crescimento exponencial se tivermos varios antigos,
                    # idealmente só o ÚLTIMO deveria ser recorrente=1.
                    # Ajuste: Ao gerar o novo, removemos a flag recorrente do antigo.
                    
                    db.sql_run("UPDATE financeiro SET recorrente=0 WHERE id=?", (row['id'],))
                    
    except Exception as e:
        print(f"Erro ao verificar recorrências: {e}")


def render_importar_tab():
    """Aba para importar lançamentos via Excel"""
    st.markdown("### 📥 Importar Lançamentos")
    st.caption("Importe vários lançamentos de uma vez através de um arquivo Excel")
    
    # Template para download
    with st.expander("📄 Baixar Template Excel", expanded=False):
        st.info("""
        **Formato esperado do arquivo:**
        - **data** (DD/MM/YYYY): Data do lançamento
        - **tipo** (Entrada/Saída): Tipo do lançamento
        - **descricao**: Descrição do lançamento
        - **valor**: Valor em reais (ex: 1500.50)
        - **vencimento** (DD/MM/YYYY): Data de vencimento
        - **categoria**: Categoria do lançamento
        - **status** (Pendente/Pago): Status do pagamento
        """)
        
        # Gerar template
        template_data = {
            'data': ['01/12/2024', '05/12/2024'],
            'tipo': ['Entrada', 'Saída'],
            'descricao': ['Honorários João Silva', 'Aluguel Escritório'],
            'valor': [2500.00, 1500.00],
            'vencimento': ['10/12/2024', '10/12/2024'],
            'categoria': ['Honorários', 'Aluguel'],
            'status': ['Pendente', 'Pago']
        }
        df_template = pd.DataFrame(template_data)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_template.to_excel(writer, sheet_name='Lançamentos', index=False)
        buffer.seek(0)
        
        st.download_button(
            "⬇️ Baixar Template",
            data=buffer,
            file_name="template_lancamentos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.divider()
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=['xlsx', 'xls'], key="import_excel")
    
    if uploaded_file:
        try:
            df_import = pd.read_excel(uploaded_file)
            
            st.markdown("**Preview dos dados:**")
            st.dataframe(df_import.head(10), use_container_width=True)
            
            st.markdown(f"**Total de linhas:** {len(df_import)}")
            
            # Validação básica
            colunas_necessarias = ['tipo', 'descricao', 'valor', 'vencimento']
            colunas_faltando = [c for c in colunas_necessarias if c not in df_import.columns]
            
            if colunas_faltando:
                st.error(f"❌ Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
                return
            
            if st.button("📤 Importar Lançamentos", type="primary"):
                with st.spinner("Importando..."):
                    importados = 0
                    erros = 0
                    
                    for idx, row in df_import.iterrows():
                        try:
                            # Parsear datas
                            data_lanc = datetime.now().strftime("%Y-%m-%d")
                            if 'data' in row and pd.notna(row['data']):
                                try:
                                    data_lanc = pd.to_datetime(row['data'], dayfirst=True).strftime("%Y-%m-%d")
                                except:
                                    pass
                            
                            vencimento = datetime.now().strftime("%Y-%m-%d")
                            if pd.notna(row['vencimento']):
                                try:
                                    vencimento = pd.to_datetime(row['vencimento'], dayfirst=True).strftime("%Y-%m-%d")
                                except:
                                    pass
                            
                            dados = {
                                "data": data_lanc,
                                "tipo": row['tipo'],
                                "descricao": str(row['descricao']),
                                "valor": float(row['valor']),
                                "vencimento": vencimento,
                                "categoria": row.get('categoria', 'Outros') if pd.notna(row.get('categoria')) else 'Outros',
                                "status_pagamento": row.get('status', 'Pendente') if pd.notna(row.get('status')) else 'Pendente',
                                "responsavel": "Importação",
                                "centro_custo": "Importado",
                                "recorrente": 0
                            }
                            
                            db.crud_insert("financeiro", dados, "Importação Excel")
                            importados += 1
                            
                        except Exception as e:
                            logger.error(f"Erro na linha {idx}: {e}")
                            erros += 1
                    
                    st.success(f"✅ {importados} lançamentos importados com sucesso!")
                    if erros > 0:
                        st.warning(f"⚠️ {erros} linhas com erro foram ignoradas.")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo: {e}")
