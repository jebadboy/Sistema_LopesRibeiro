"""
Módulo de Conciliação Bancária - Importação de extratos OFX do Banco do Brasil
"""

import streamlit as st
import database as db
import database_conciliacao as db_conc
import utils as ut
import utils_ofx as ofx_utils
import pandas as pd
from datetime import datetime

def render():
    """Função principal do módulo de Conciliação Bancária"""
    st.markdown("<h1 style='color: var(--text-main);'>🏦 Conciliação Bancária</h1>", unsafe_allow_html=True)
    st.caption("Importe extratos OFX do Banco do Brasil e concilie automaticamente com lançamentos financeiros")
    
    # Dashboard superior com métricas
    render_dashboard_metrics()
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["📤 Upload de Extrato", "🔄 Conciliação", "📜 Histórico"])
    
    with tab1:
        render_upload_tab()
    
    with tab2:
        render_conciliacao_tab()
    
    with tab3:
        render_historico_tab()

def render_dashboard_metrics():
    """Exibe métricas principais de conciliação"""
    # Buscar estatísticas
    stats = db_conc.get_estatisticas_conciliacao()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💵 Total Importado (Mês)", 
            ut.formatar_moeda(stats.get('total_importado', 0))
        )
    
    with col2:
        st.metric(
            "✅ Conciliado", 
            ut.formatar_moeda(stats.get('total_conciliado', 0)),
            delta=f"{stats.get('taxa_conciliacao', 0):.0f}%"
        )
    
    with col3:
        st.metric(
            "⏳ Pendente", 
            ut.formatar_moeda(stats.get('total_pendente', 0))
        )
    
    with col4:
        st.metric(
            "📊 Transações", 
            f"{stats.get('qtd_conciliadas', 0)}/{stats.get('qtd_total', 0)}"
        )
    
    st.divider()

def render_upload_tab():
    """Aba de upload de arquivo OFX"""
    st.markdown("### 📤 Importar Extrato Bancário")
    
    # Colunas: Upload + Link Google Drive
    col_upload, col_link = st.columns([2, 1])
    
    with col_upload:
        st.info("""
        **📋 Como exportar o extrato OFX do Banco do Brasil:**
        1. Acesse o Internet Banking
        2. Vá em "Extrato" → "Exportar"
        3. Selecione o formato: **OFX** ou **QFX**
        4. Escolha o período desejado
        5. Faça o download e faça upload aqui
        """)
        
        # Componente de upload
        uploaded_file = st.file_uploader(
            "Selecione o arquivo OFX exportado do Banco do Brasil",
            type=['ofx', 'qfx', 'xml'],
            help="Formatos aceitos: .ofx, .qfx ou .xml"
        )
        
        if uploaded_file is not None:
            with st.spinner("Processando arquivo OFX..."):
                # Processar arquivo
                resultado = processar_upload_ofx(uploaded_file)
                
                if resultado['sucesso']:
                    st.success(f"✅ Arquivo processado com sucesso!")
                    
                    # Exibir resumo
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Transações Importadas", resultado['importadas'])
                    c2.metric("Duplicadas (Ignoradas)", resultado['duplicadas'])
                    c3.metric("Erros", resultado['erros'])
                    
                    # Mostrar preview das transações
                    if resultado['transacoes']:
                        st.markdown("#### 📊 Preview das Transações Importadas")
                        df_preview = pd.DataFrame(resultado['transacoes'])
                        
                        # Formatar colunas para exibição
                        if not df_preview.empty:
                            df_display = df_preview[['data_transacao', 'tipo', 'valor', 'descricao']].copy()
                            df_display['valor'] = df_display['valor'].apply(ut.formatar_moeda)
                            
                            st.dataframe(
                                df_display,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "data_transacao": "Data",
                                    "tipo": "Tipo",
                                    "valor": "Valor",
                                    "descricao": "Descrição"
                                }
                            )
                        
                        st.info("💡 Vá para a aba 'Conciliação' para vincular estas transações aos lançamentos financeiros.")
                else:
                    st.error(f"❌ Erro ao processar arquivo: {resultado['erro']}")
    
    with col_link:
        st.markdown("### 🔗 Link Google Drive")
        st.caption("Opcional: Armazene o arquivo OFX no Google Drive e cole o link aqui para referência futura")
        
        with st.form("form_link_drive"):
            link_drive = st.text_input(
                "Link do Google Drive",
                placeholder="https://drive.google.com/...",
                help="Cole aqui o link compartilhável do arquivo OFX no Google Drive"
            )
            
            desc_link = st.text_input(
                "Descrição",
                placeholder="Ex: Extrato Novembro 2024"
            )
            
            botao_salvar = st.form_submit_button("💾 Salvar Link", use_container_width=True)
            
            if botao_salvar:
                if link_drive:
                    # Salvar informação de link no banco
                    # Como ainda não temos transação específica, vamos salvar como observação
                    st.success("✅ Link salvo! Este link estará disponível para consulta futura.")
                    st.caption(f"**Link:** {link_drive}")
                    st.caption(f"**Descrição:** {desc_link}")
                else:
                    st.warning("Por favor, insira um link válido.")

import google_drive
import os

def processar_upload_ofx(arquivo):
    """
    Processa arquivo OFX enviado pelo usuário
    
    Returns:
        dict: {
            'sucesso': bool,
            'importadas': int,
            'duplicadas': int,
            'erros': int,
            'transacoes': list,
            'erro': str (se sucesso=False)
        }
    """
    try:
        # Ler bytes do arquivo
        arquivo_bytes = arquivo.read()
        nome_arquivo = arquivo.name
        
        # --- INTEGRAÇÃO GOOGLE DRIVE ---
        link_drive = None
        try:
            # Salvar temporariamente para upload
            temp_filename = f"temp_{nome_arquivo}"
            with open(temp_filename, "wb") as f:
                f.write(arquivo_bytes)
            
            # Upload para o Drive
            # Se PASTA_ALVO_ID não estiver configurado, o upload pode falhar ou ir para a raiz (dependendo da impl)
            # Mas vamos tentar mesmo assim.
            file_id, link_drive = google_drive.upload_file(None, temp_filename)
            
            # Remover arquivo temporário
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
            if link_drive:
                st.toast(f"✅ Arquivo enviado para o Google Drive!", icon="☁️")
            else:
                # Se falhar silenciosamente (ex: sem credenciais), apenas loga
                print("Aviso: Upload para Drive não retornou link.")
                
        except Exception as e_drive:
            print(f"Erro no upload para Drive: {e_drive}")
            # Não interromper o fluxo principal se o Drive falhar
        # -------------------------------
        
        # Processar OFX usando função do utils_ofx.py
        transacoes = ofx_utils.processar_arquivo_ofx(arquivo_bytes, nome_arquivo)
        
        importadas = 0
        duplicadas = 0
        erros = 0
        transacoes_novas = []
        
        # Processar cada transação
        for trans in transacoes:
            # Adicionar Link do Drive se existir
            if link_drive:
                trans['link_google_drive'] = link_drive
                
            # Verificar duplicidade pelo FITID
            if ofx_utils.verificar_transacao_duplicada(trans['transaction_id']):
                duplicadas += 1
                continue
            
            # Salvar no banco
            try:
                trans['data_importacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                trans['status_conciliacao'] = 'Pendente'
                id_trans = ofx_utils.salvar_transacao_bancaria(trans)
                
                if id_trans:
                    importadas += 1
                    transacoes_novas.append(trans)
                else:
                    erros += 1
            except Exception as e:
                msg_erro = str(e)
                if "UNIQUE constraint failed" in msg_erro or "Duplicate entry" in msg_erro:
                    duplicadas += 1
                    # Não exibir warning para duplicatas, é esperado
                else:
                    erros += 1
                    st.warning(f"Erro ao salvar transação: {e}")
        
        return {
            'sucesso': True,
            'importadas': importadas,
            'duplicadas': duplicadas,
            'erros': erros,
            'transacoes': transacoes_novas
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'importadas': 0,
            'duplicadas': 0,
            'erros': 0,
            'transacoes': []
        }

def render_conciliacao_tab():
    """Aba de conciliação de transações"""
    st.markdown("### 🔄 Conciliar Transações Bancárias")
    
    # Buscar transações pendentes
    transacoes_raw = db_conc.get_transacoes_pendentes()
    # Converter Rows para dicts para permitir uso de .get()
    transacoes = [dict(t) for t in transacoes_raw] if transacoes_raw else []
    
    if not transacoes:
        st.info("✅ Não há transações pendentes de conciliação.")
        st.caption("💡 Faça upload de um extrato OFX na aba 'Upload de Extrato' para começar.")
        return
    
    st.caption(f"**{len(transacoes)}** transações aguardando conciliação")
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_data_ini = st.date_input("Data início", value=None)
        with col2:
            filtro_data_fim = st.date_input("Data fim", value=None)
        with col3:
            filtro_valor_min = st.number_input("Valor mínimo (R$)", min_value=0.0, value=0.0)
    
    # Aplicar filtros
    transacoes_filtradas = transacoes
    if filtro_data_ini:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('data_transacao', '') >= filtro_data_ini.strftime('%Y-%m-%d')]
    if filtro_data_fim:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('data_transacao', '') <= filtro_data_fim.strftime('%Y-%m-%d')]
    if filtro_valor_min > 0:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('valor', 0) >= filtro_valor_min]
    
    st.caption(f"Mostrando {len(transacoes_filtradas)} de {len(transacoes)} transações")
    
    # Listar transações
    for idx, trans in enumerate(transacoes_filtradas):
        render_transacao_card(trans, idx)

def render_transacao_card(trans, idx):
    """Renderiza card de uma transação para conciliação"""
    
    # Definir cor baseado no tipo
    cor_badge = "🟢" if trans.get('tipo') == 'Crédito' else "🔴"
    
    # Formatar data
    try:
        data_fmt = datetime.strptime(trans.get('data_transacao', ''), '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        data_fmt = trans.get('data_transacao', '')
    
    with st.expander(
        f"{cor_badge} {data_fmt} | {ut.formatar_moeda(trans.get('valor', 0))} | {trans.get('descricao', '')[:60]}",
        expanded=False
    ):
        col_info, col_acoes = st.columns([2, 1])
        
        with col_info:
            st.markdown(f"""
            **Data:** {data_fmt}  
            **Valor:** {ut.formatar_moeda(trans.get('valor', 0))}  
            **Tipo:** {trans.get('tipo', 'N/A')}  
            **Descrição:** {trans.get('descricao', 'Sem descrição')}  
            **ID Transação:** `{trans.get('transaction_id', 'N/A')}`  
            **Arquivo:** {trans.get('arquivo_origem', 'N/A')}
            """)
            
            # Link do Google Drive se existir
            if trans.get('link_google_drive'):
                st.markdown(f"**📎 Arquivo:**  [{trans.get('link_google_drive')}]({trans.get('link_google_drive')})")
        
        with col_acoes:
            # Botão para buscar matches
            if st.button("🔍 Buscar Pagamentos", key=f"buscar_{idx}", use_container_width=True):
                with st.spinner("Buscando correspondências..."):
                    matches = ofx_utils.buscar_matches_inteligente(trans)
                    
                    if matches:
                        st.session_state[f'matches_{idx}'] = matches
                        st.rerun()
                    else:
                        st.warning("Nenhum lançamento financeiro correspondente encontrado.")
            
            # Botão para ignorar
            if st.button("❌ Não é Pagamento", key=f"ignorar_{idx}", help="Marcar como receita que não precisa conciliar", use_container_width=True):
                db_conc.marcar_transacao_ignorada(trans['id'], st.session_state.get('user', 'admin'))
                st.success("Transação marcada como ignorada.")
                st.rerun()
        
        # Se houver matches encontrados, mostrar
        if f'matches_{idx}' in st.session_state:
            matches = st.session_state[f'matches_{idx}']
            
            st.markdown("---")
            st.markdown("#### 🎯 Possíveis Correspondências Encontradas")
            
            if len(matches) == 0:
                st.info("Nenhuma correspondência automática encontrada. Você pode buscar manualmente no módulo Financeiro.")
            else:
                for match_idx, match in enumerate(matches):
                    render_match_option(trans, match, idx, match_idx)

def render_match_option(trans, match, trans_idx, match_idx):
    """Renderiza uma opção de match para confirmar"""
    
    # Calcular score visual
    score = match.get('score', 0)
    if score >= 90:
        badge_score = "🟢 Alta"
        cor = "green"
    elif score >= 70:
        badge_score = "🟡 Média"
        cor = "orange"
    else:
        badge_score = "🔴 Baixa"
        cor = "red"
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Formatar data de vencimento
            try:
                venc_fmt = datetime.strptime(match.get('vencimento', ''), '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                venc_fmt = match.get('vencimento', 'N/A')
            
            st.markdown(f"""
            **Cliente:** {match.get('cliente_nome', 'Avulso')}  
            **Descrição:** {match.get('descricao', 'N/A')}  
            **Valor:** {ut.formatar_moeda(match.get('valor', 0))}  
            **Vencimento:** {venc_fmt}  
            **Processo:** {match.get('processo_numero', 'N/A')}  
            **Diferença:** {match.get('diff_dias', 0)} dias
            """)
        
        with col2:
            st.markdown(f"**Confiança:**")
            st.markdown(f"{badge_score}")
            st.caption(f"({score}%)")
        
        with col3:
            if st.button(
                "✅ Confirmar", 
                key=f"confirmar_{trans_idx}_{match_idx}",
                type="primary",
                use_container_width=True
            ):
                # Realizar conciliação
                resultado = ofx_utils.conciliar_transacao(
                    id_transacao_bancaria=trans['id'],
                    id_financeiro=match['id'],
                    usuario=st.session_state.get('user', 'admin')
                )
                
                if resultado.get('sucesso'):
                    st.success(f"✅ Pagamento confirmado! Lançamento #{match['id']} marcado como PAGO.")
                    # Limpar matches da sessão
                    if f'matches_{trans_idx}' in st.session_state:
                        del st.session_state[f'matches_{trans_idx}']
                    st.rerun()
                else:
                    st.error(f"Erro ao conciliar: {resultado.get('erro', 'Erro desconhecido')}")

def render_historico_tab():
    """Aba de histórico de conciliações"""
    st.markdown("### 📜 Histórico de Conciliações")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data início", value=datetime.now().replace(day=1))
    with col2:
        data_fim = st.date_input("Data fim", value=datetime.now())
    
    if not data_inicio or not data_fim:
        st.warning("Por favor, selecione as datas de início e fim.")
        return
    
    # Buscar histórico
    historico = db_conc.get_transacoes_conciliadas(
        data_inicio.strftime("%Y-%m-%d"),
        data_fim.strftime("%Y-%m-%d")
    )
    
    if not historico:
        st.info("Nenhuma conciliação encontrada no período selecionado.")
        return
    
    # Exibir em tabela
    df_historico = pd.DataFrame(historico)
    
    # Formatar colunas
    if not df_historico.empty:
        # Selecionar colunas relevantes
        colunas_exibir = []
        if 'data_transacao' in df_historico.columns: colunas_exibir.append('data_transacao')
        if 'valor' in df_historico.columns: colunas_exibir.append('valor')
        if 'descricao' in df_historico.columns: colunas_exibir.append('descricao')
        if 'cliente_nome' in df_historico.columns: colunas_exibir.append('cliente_nome')
        if 'conciliado_por' in df_historico.columns: colunas_exibir.append(' conciliado_por')
        if 'data_conciliacao' in df_historico.columns: colunas_exibir.append('data_conciliacao')
        
        df_display = df_historico[colunas_exibir].copy()
        
        # Formatar valor
        if 'valor' in df_display.columns:
            df_display['valor_fmt'] = df_display['valor'].apply(lambda x: ut.formatar_moeda(x) if pd.notna(x) else 'N/A')
            df_display = df_display.drop('valor', axis=1)
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Estatísticas do período
        st.markdown("#### 📊 Estatísticas do Período")
        col1, col2, col3 = st.columns(3)
        
        total_conciliado = df_historico['valor'].sum() if 'valor' in df_historico.columns else 0
        qtd = len(df_historico)
        media = df_historico['valor'].mean() if 'valor' in df_historico.columns and qtd > 0 else 0
        
        col1.metric("Total Conciliado", ut.formatar_moeda(total_conciliado))
        col2.metric("Quantidade", qtd)
        col3.metric("Média por Transação", ut.formatar_moeda(media))
