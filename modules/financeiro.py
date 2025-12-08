import streamlit as st
import database as db
import utils as ut
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import utils_recibo as ur
import urllib.parse

def render():
    st.markdown("<h1 style='color: var(--text-main);'>💰 Gestão Financeira</h1>", unsafe_allow_html=True)
    
    # --- DASHBOARD SUPERIOR (BIG NUMBERS) ---
    verificar_recorrencias() # Verificar e gerar recorrencias ao carregar
    render_dashboard_header()
    
    # --- ABAS PRINCIPAIS ---
    t1, t2, t3 = st.tabs(["📝 Lançamentos & Extrato", "📊 Relatórios Gerenciais", "🧾 Emitir Recibo"])
    
    with t1:
        render_lancamentos_tab()
    
    with t2:
        render_relatorios_tab()

    with t3:
        render_recibos_tab()

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
        
        # Parcelamento (Apenas para Entradas ou Saídas grandes)
        parcelas = 1
        if tipo == "Entrada":
            parcelas = st.number_input("Parcelar em quantas vezes?", min_value=1, max_value=60, value=1)
            if parcelas > 1:
                st.caption(f"Serão gerados {parcelas} lançamentos de {ut.formatar_moeda(valor/parcelas)}")
        
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
                    if tipo == "Entrada" and id_processo_sel: # Usar id_processo_sel definido acima
                        # Buscar dados do processo
                        proc_data = db.sql_get_query("SELECT parceiro_nome, parceiro_percentual FROM processos WHERE id=?", (id_processo_sel,))
                        if not proc_data.empty:
                            p_nome = proc_data.iloc[0]['parceiro_nome']
                            p_pct = proc_data.iloc[0]['parceiro_percentual']
                            
                            if p_nome and p_pct > 0:
                                valor_repasse = round(valor_parcela * (p_pct / 100), 2)
                                
                                # Criar lançamento de saída (Repasse)
                                dados_repasse = {
                                    "data": datetime.now().strftime("%Y-%m-%d"),
                                    "tipo": "Saída",
                                    "categoria": "Repasse de Parceria",
                                    "descricao": f"Repasse {p_nome} - {desc_final}",
                                    "valor": valor_repasse,
                                    "responsavel": "Sistema",
                                    "status_pagamento": "Pendente",
                                    "vencimento": venc_atual.strftime("%Y-%m-%d"),
                                    "id_processo": id_processo_sel,
                                    "centro_custo": "Repasse",
                                    "recorrente": 0
                                }
                                db.crud_insert("financeiro", dados_repasse, f"Repasse automático para {p_nome}")
                                st.toast(f"💸 Repasse de R$ {valor_repasse} gerado para {p_nome}!", icon="🤝")
                    # -------------------------------------
                
                st.success(f"{parcelas} lançamento(s) realizado(s) com sucesso!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

def render_extrato_lista():
    df = db.sql_get("financeiro", "vencimento DESC")
    
    if df.empty:
        st.info("📭 Nenhum lançamento encontrado para os filtros selecionados.")
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
                
                # Exibir meio de pagamento se disponível
                if row.get('meio_pagamento'):
                    st.write(f"**Pagamento:** {row['meio_pagamento']}")
                
                if row.get('comprovante_link'):
                    st.markdown(f"[📄 Ver Comprovante]({row['comprovante_link']})", unsafe_allow_html=True)
                
            # Coluna 2: Ações
            with c_det2:
                novo_status = st.selectbox("Alterar Status", ["Pendente", "Pago"], index=0 if row['status_pagamento']=="Pendente" else 1, key=f"st_{row['id']}")
                
                if novo_status != row['status_pagamento']:
                    db.crud_update("financeiro", 
                                  {"status_pagamento": novo_status, 
                                   "data_pagamento": datetime.now().strftime("%Y-%m-%d") if novo_status == "Pago" else None},
                                  "id = ?", (row['id'],), "Alteração Status Extrato")
                    st.rerun()
                
                # Botão para Emitir Recibo (Se Pago e Entrada)
                if row['status_pagamento'] == 'Pago' and row['tipo'] == 'Entrada':
                    if st.button("📄 Emitir Recibo", key=f"rec_{row['id']}"):
                        st.session_state['recibo_pre_fill'] = {
                            'id_lancamento': row['id'],
                            'valor': row['valor'],
                            'descricao': row['descricao'],
                            'id_cliente': row['id_cliente'],
                            'data_pagamento': row['data_pagamento']
                        }
                        # Forçar mudança de aba (gambiarra visual ou instrução)
                        st.info("Vá para a aba 'Emitir Recibo' para gerar o PDF.")
                
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
    df['vencimento'] = pd.to_datetime(df['vencimento'], errors='coerce')
    
    # Sub-abas de Relatórios
    tab_visao, tab_inadim, tab_export = st.tabs(["📈 Visão Geral", "⚠️ Inadimplência", "📥 Exportar"])
    
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
            cpf_final = c2.text_input("CPF/CNPJ", value=cli_row['cpf_cnpj'] if cli_row['cpf_cnpj'] else "")
            
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
                    cpf_cli = cli.iloc[0]['cpf_cnpj'] if cli.iloc[0]['cpf_cnpj'] else ""
            
            st.info(f"Dados carregados: {nome_cli} - R$ {row['valor']}")
            
            # Permitir edição
            c1, c2 = st.columns(2)
            nome_final = c1.text_input("Nome do Pagador", value=nome_cli)
            cpf_final = c2.text_input("CPF/CNPJ", value=cpf_cli)
            
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

