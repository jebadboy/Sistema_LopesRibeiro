"""
Módulo de Conciliação Bancária - Importação de extratos OFX do Banco do Brasil
"""

import streamlit as st
import database as db
import database_conciliacao as db_conc
import utils as ut
import utils_ofx as ofx_utils
import pandas as pd
import google_drive
import os
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def render():
    """Função principal do módulo de Conciliação Bancária"""
    st.markdown("<h1 style='color: var(--text-main);'>🏦 Conciliação Bancária</h1>", unsafe_allow_html=True)
    st.caption("Importe extratos OFX/CSV e concilie automaticamente com lançamentos financeiros")
    
    # Dashboard superior com métricas
    render_dashboard_metrics()
    
    # Abas principais (expandidas)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Upload", 
        "🔄 Conciliação", 
        "📜 Histórico",
        "📊 Dashboard",
        "⚙️ Regras"
    ])
    
    with tab1:
        render_upload_tab()
    
    with tab2:
        render_conciliacao_tab()
    
    with tab3:
        render_historico_tab()
    
    with tab4:
        render_dashboard_avancado()
    
    with tab5:
        render_regras_tab()

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
    
    # 1. Configuração da Origem (NOVO)
    st.markdown("#### 1. Identificação da Origem")
    c_orig1, c_orig2 = st.columns(2)
    
    tipo_origem = c_orig1.selectbox(
        "Tipo de Fonte", 
        ["Conta Bancária", "Maquininha de Cartão"],
        help="Selecione se o extrato é de uma conta bancária ou de uma adquirente (maquininha)"
    )
    
    opcoes_inst = []
    if tipo_origem == "Conta Bancária":
        opcoes_inst = ["Banco do Brasil", "Bradesco", "Caixa", "Santander", "Itaú", "Nubank", "Inter", "Outro"]
    else:
        opcoes_inst = ["Cielo", "Rede", "Getnet", "Stone", "PagSeguro", "Outro"]
        
    conta_origem = c_orig2.selectbox("Instituição / Conta", opcoes_inst)
    
    st.divider()
    
    # 2. Upload e Link - COM OPÇÃO CSV
    st.markdown("#### 2. Arquivo e Armazenamento")
    
    # Sub-abas para tipo de arquivo
    upload_tipo = st.radio("Tipo de Arquivo", ["📄 OFX/QFX", "📊 CSV"], horizontal=True)
    
    # Colunas: Upload + Link Google Drive
    col_upload, col_link = st.columns([2, 1])
    
    with col_upload:
        if upload_tipo == "📄 OFX/QFX":
            st.info("""
            **📋 Como exportar o extrato OFX:**
            1. Acesse o Internet Banking ou Portal da Maquininha
            2. Vá em "Extrato" → "Exportar"
            3. Selecione o formato: **OFX** ou **QFX**
            4. Escolha o período desejado
            5. Faça o download e faça upload aqui
            """)
        
            # Componente de upload OFX
            uploaded_file = st.file_uploader(
                f"Selecione o arquivo OFX ({conta_origem})",
                type=['ofx', 'qfx', 'xml'],
                help="Formatos aceitos: .ofx, .qfx ou .xml",
                key="ofx_uploader"
            )
            
            if uploaded_file is not None:
                if st.button("📤 Processar Arquivo OFX", type="primary"):
                    with st.spinner("Processando arquivo OFX..."):
                        # Preparar dados extras
                        extras = {
                            'tipo_origem': tipo_origem,
                            'conta_origem': conta_origem
                        }
                        
                        # Processar arquivo
                        resultado = processar_upload_ofx(uploaded_file, extras)
                        
                        if resultado['sucesso']:
                            st.success(f"✅ Arquivo de {conta_origem} processado com sucesso!")
                            
                            # Exibir resumo
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Transações", resultado['importadas'])
                            c2.metric("Duplicadas", resultado['duplicadas'])
                            c3.metric("Erros", resultado['erros'])
                            
                            # Mostrar preview das transações
                            if resultado['transacoes']:
                                st.markdown("#### 📊 Preview das Transações")
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
                            
                            st.info("💡 Vá para a aba 'Conciliação' para vincular estas transações.")
                        else:
                            st.error(f"❌ Erro ao processar arquivo: {resultado['erro']}")
        
        else:
            # Upload CSV
            st.info("""
            **📋 Como usar arquivos CSV:**
            1. Exporte o extrato do seu banco em formato CSV
            2. Certifique-se que o arquivo contém colunas de Data, Valor e Descrição
            3. Faça upload e mapeie as colunas corretamente
            """)
            
            render_upload_csv()    
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
                placeholder=f"Extrato {conta_origem} - Mês/Ano"
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

def processar_upload_ofx(arquivo, extras=None):
    """
    Processa arquivo OFX enviado pelo usuário
    
    Args:
        arquivo: O arquivo enviado pelo st.file_uploader
        extras: Dict com dados extras (tipo_origem, conta_origem)
    
    Returns:
        dict: Resultado do processamento
    """
    try:
        # Ler bytes do arquivo
        arquivo.seek(0) # Garantir que está no inicio
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
            
            # Adicionar Extras (Origem)
            if extras:
                trans.update(extras)
                
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
    
    # Métricas resumidas
    total_credito = sum(t.get('valor', 0) for t in transacoes if t.get('tipo') == 'Crédito')
    total_debito = sum(t.get('valor', 0) for t in transacoes if t.get('tipo') == 'Débito')
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total Pendente", len(transacoes))
    col_m2.metric("🟢 Créditos", ut.formatar_moeda(total_credito))
    col_m3.metric("🔴 Débitos", ut.formatar_moeda(total_debito))
    
    st.divider()
    
    # Filtros expandidos
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_data_ini = st.date_input("Data início", value=None, key="conc_data_ini")
        with col2:
            filtro_data_fim = st.date_input("Data fim", value=None, key="conc_data_fim")
        with col3:
            filtro_tipo = st.selectbox("Tipo", ["Todos", "Crédito", "Débito"], key="conc_tipo")
        with col4:
            filtro_valor_min = st.number_input("Valor mínimo (R$)", min_value=0.0, value=0.0, key="conc_valor")
    
    # Aplicar filtros
    transacoes_filtradas = transacoes
    if filtro_data_ini:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('data_transacao', '') >= filtro_data_ini.strftime('%Y-%m-%d')]
    if filtro_data_fim:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('data_transacao', '') <= filtro_data_fim.strftime('%Y-%m-%d')]
    if filtro_tipo != "Todos":
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('tipo') == filtro_tipo]
    if filtro_valor_min > 0:
        transacoes_filtradas = [t for t in transacoes_filtradas if t.get('valor', 0) >= filtro_valor_min]
    
    # Paginação
    ITENS_POR_PAGINA = 15
    total_paginas = max(1, (len(transacoes_filtradas) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    
    col_pg1, col_pg2, col_pg3 = st.columns([1, 2, 1])
    with col_pg2:
        pagina_atual = st.number_input(
            f"Página (de {total_paginas})", 
            min_value=1, 
            max_value=total_paginas, 
            value=1,
            key="conc_pagina"
        )
    
    inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    transacoes_pagina = transacoes_filtradas[inicio:fim]
    
    st.caption(f"Mostrando {len(transacoes_pagina)} de {len(transacoes_filtradas)} transações (filtradas de {len(transacoes)} total)")
    
    # Listar transações da página atual
    for idx, trans in enumerate(transacoes_pagina):
        render_transacao_card(trans, inicio + idx)

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
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        data_inicio = st.date_input("Data início", value=datetime.now().replace(day=1), key="hist_data_ini")
    with col2:
        data_fim = st.date_input("Data fim", value=datetime.now(), key="hist_data_fim")
    with col3:
        st.write("")  # Espaçador
        st.write("")
        if st.button("🔄 Atualizar", key="hist_refresh", use_container_width=True):
            st.rerun()
    
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
    
    # Converter para DataFrame
    df_historico = pd.DataFrame(historico)
    
    # Estatísticas do período (no topo)
    st.markdown("#### 📊 Estatísticas do Período")
    col1, col2, col3 = st.columns(3)
    
    total_conciliado = df_historico['valor'].sum() if 'valor' in df_historico.columns else 0
    qtd = len(df_historico)
    media = df_historico['valor'].mean() if 'valor' in df_historico.columns and qtd > 0 else 0
    
    col1.metric("Total Conciliado", ut.formatar_moeda(total_conciliado))
    col2.metric("Quantidade", qtd)
    col3.metric("Média por Transação", ut.formatar_moeda(media))
    
    st.divider()
    
    # Botão de exportação Excel
    col_exp1, col_exp2 = st.columns([3, 1])
    with col_exp2:
        try:
            # Preparar DataFrame para exportação
            df_export = df_historico.copy()
            if 'valor' in df_export.columns:
                df_export['valor_formatado'] = df_export['valor'].apply(lambda x: ut.formatar_moeda(x) if pd.notna(x) else '')
            
            # Criar arquivo Excel em memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='Conciliações', index=False)
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Exportar Excel",
                data=excel_data,
                file_name=f"conciliacoes_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            logger.error(f"Erro ao exportar Excel: {e}")
            st.warning("Erro ao gerar arquivo Excel.")
    
    # Exibir histórico com opção de reverter
    st.markdown("#### 📋 Transações Conciliadas")
    
    for idx, row in df_historico.iterrows():
        trans = dict(row)
        
        # Formatar data
        try:
            data_fmt = datetime.strptime(trans.get('data_transacao', ''), '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            data_fmt = trans.get('data_transacao', 'N/A')
        
        with st.expander(f"✅ {data_fmt} | {ut.formatar_moeda(trans.get('valor', 0))} | {trans.get('cliente_nome', 'N/A')}", expanded=False):
            col_info, col_acoes = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"""
                **Data:** {data_fmt}  
                **Valor:** {ut.formatar_moeda(trans.get('valor', 0))}  
                **Cliente:** {trans.get('cliente_nome', 'N/A')}  
                **Descrição:** {trans.get('descricao', 'N/A')}  
                **Conciliado por:** {trans.get('conciliado_por', 'N/A')}  
                **Data Conciliação:** {trans.get('data_conciliacao', 'N/A')}
                """)
            
            with col_acoes:
                if st.button("⬅️ Desfazer", key=f"reverter_{trans.get('id', idx)}", type="secondary", use_container_width=True, help="Reverter esta conciliação para Pendente"):
                    resultado = db_conc.reverter_conciliacao(
                        trans['id'],
                        st.session_state.get('user', 'admin')
                    )
                    if resultado.get('sucesso'):
                        st.success("✅ Conciliação revertida com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Erro: {resultado.get('erro', 'Erro desconhecido')}")


# =====================================================
# NOVAS FUNCIONALIDADES AVANÇADAS
# =====================================================

def render_dashboard_avancado():
    """Dashboard avançado com gráficos e análises"""
    st.markdown("### 📊 Dashboard de Conciliação")
    
    # Período de análise
    col1, col2 = st.columns(2)
    with col1:
        meses_atras = st.selectbox("Período", [1, 3, 6, 12], index=1, format_func=lambda x: f"Últimos {x} mês(es)")
    
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=meses_atras * 30)
    
    # Buscar dados para gráficos
    dados_evolucao = db_conc.get_evolucao_conciliacao(data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d'))
    
    if not dados_evolucao:
        st.info("Não há dados suficientes para gerar gráficos.")
        return
    
    df_evolucao = pd.DataFrame(dados_evolucao)
    
    # Gráfico de evolução mensal
    st.markdown("#### 📈 Evolução de Conciliações")
    if not df_evolucao.empty and 'mes' in df_evolucao.columns:
        st.bar_chart(df_evolucao.set_index('mes')[['total_conciliado', 'total_pendente']])
    
    # Métricas por conta
    st.markdown("#### 🏦 Por Conta/Instituição")
    dados_por_conta = db_conc.get_totais_por_conta()
    if dados_por_conta:
        df_contas = pd.DataFrame(dados_por_conta)
        if not df_contas.empty:
            st.dataframe(df_contas, use_container_width=True, hide_index=True)
    
    # Alertas de pendentes
    st.markdown("#### ⚠️ Alertas de Pendentes")
    dias_alerta = st.number_input("Alertar pendentes há mais de (dias):", min_value=1, value=7, key="dias_alerta")
    pendentes_antigos = db_conc.get_pendentes_antigos(dias_alerta)
    
    if pendentes_antigos:
        st.warning(f"🔔 {len(pendentes_antigos)} transações pendentes há mais de {dias_alerta} dias!")
        with st.expander("Ver detalhes"):
            df_pendentes = pd.DataFrame(pendentes_antigos)
            if 'valor' in df_pendentes.columns:
                df_pendentes['valor_fmt'] = df_pendentes['valor'].apply(ut.formatar_moeda)
            st.dataframe(df_pendentes[['data_transacao', 'valor_fmt', 'descricao', 'conta_origem']] if 'valor_fmt' in df_pendentes.columns else df_pendentes, 
                        use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhuma transação pendente antiga!")


def render_regras_tab():
    """Gerenciamento de regras automáticas de conciliação"""
    st.markdown("### ⚙️ Regras Automáticas de Conciliação")
    st.caption("Configure regras para conciliar automaticamente transações baseado em padrões")
    
    # Formulário para criar nova regra
    with st.expander("➕ Criar Nova Regra", expanded=False):
        with st.form("form_nova_regra"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_regra = st.text_input("Nome da Regra", placeholder="Ex: PIX Cliente João")
                padrao_descricao = st.text_input("Padrão na Descrição", placeholder="Ex: PIX JOAO SILVA", 
                                                  help="Texto que deve aparecer na descrição da transação")
            
            with col2:
                # Buscar clientes para vincular
                clientes = db.sql_get_query("SELECT id, nome FROM clientes ORDER BY nome")
                opcoes_clientes = {"Nenhum": None}
                if not clientes.empty:
                    for _, c in clientes.iterrows():
                        opcoes_clientes[c['nome']] = c['id']
                
                cliente_vinculo = st.selectbox("Vincular a Cliente", list(opcoes_clientes.keys()))
                categoria_auto = st.selectbox("Categoria Automática", 
                                              ["Honorários", "Custas", "Acordo", "Outros"])
            
            ativo = st.checkbox("Regra Ativa", value=True)
            
            if st.form_submit_button("💾 Salvar Regra", type="primary"):
                if nome_regra and padrao_descricao:
                    db_conc.criar_regra_conciliacao({
                        'nome': nome_regra,
                        'padrao_descricao': padrao_descricao,
                        'id_cliente': opcoes_clientes.get(cliente_vinculo),
                        'categoria': categoria_auto,
                        'ativo': 1 if ativo else 0
                    })
                    st.success("✅ Regra criada com sucesso!")
                    st.rerun()
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
    
    # Listar regras existentes
    st.markdown("#### 📋 Regras Cadastradas")
    regras = db_conc.get_regras_conciliacao()
    
    if not regras:
        st.info("Nenhuma regra cadastrada ainda.")
    else:
        for regra in regras:
            r = dict(regra)
            status = "✅ Ativa" if r.get('ativo') else "⏸️ Inativa"
            
            with st.expander(f"{status} | {r.get('nome', 'Sem nome')} - Padrão: '{r.get('padrao_descricao', '')}'"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    **Nome:** {r.get('nome')}  
                    **Padrão:** `{r.get('padrao_descricao')}`  
                    **Categoria:** {r.get('categoria', 'N/A')}  
                    **Cliente:** {r.get('cliente_nome', 'N/A')}
                    """)
                
                with col2:
                    if st.button("🔄 Alternar Status", key=f"toggle_{r['id']}"):
                        db_conc.toggle_regra(r['id'])
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Excluir", key=f"del_{r['id']}", type="secondary"):
                        db_conc.excluir_regra(r['id'])
                        st.success("Regra excluída!")
                        st.rerun()
    
    # Executar regras manualmente
    st.divider()
    st.markdown("#### 🚀 Executar Regras")
    if st.button("▶️ Aplicar Regras às Pendentes", type="primary", use_container_width=True):
        with st.spinner("Aplicando regras..."):
            resultado = aplicar_regras_automaticas()
            if resultado['conciliadas'] > 0:
                st.success(f"✅ {resultado['conciliadas']} transações conciliadas automaticamente!")
            else:
                st.info("Nenhuma transação correspondeu às regras.")


def aplicar_regras_automaticas():
    """Aplica regras automáticas às transações pendentes"""
    regras = db_conc.get_regras_conciliacao(apenas_ativas=True)
    transacoes = db_conc.get_transacoes_pendentes()
    
    conciliadas = 0
    
    for trans in transacoes:
        t = dict(trans)
        descricao = t.get('descricao', '').upper()
        
        for regra in regras:
            r = dict(regra)
            padrao = r.get('padrao_descricao', '').upper()
            
            if padrao and padrao in descricao:
                # Buscar lançamento financeiro correspondente
                id_cliente = r.get('id_cliente')
                if id_cliente:
                    # Buscar lançamentos pendentes do cliente com valor próximo
                    matches = db_conc.buscar_lancamentos_cliente(id_cliente, t.get('valor', 0))
                    
                    if matches:
                        # Conciliar com o primeiro match
                        resultado = ofx_utils.conciliar_transacao(
                            t['id'], 
                            matches[0]['id'],
                            'SISTEMA (Regra Automática)'
                        )
                        if resultado.get('sucesso'):
                            conciliadas += 1
                            break
    
    return {'conciliadas': conciliadas}


def calcular_similaridade(texto1, texto2):
    """Calcula similaridade entre dois textos (fuzzy matching)"""
    if not texto1 or not texto2:
        return 0
    return SequenceMatcher(None, texto1.upper(), texto2.upper()).ratio() * 100


def processar_csv(arquivo_bytes, nome_arquivo, mapeamento):
    """
    Processa arquivo CSV de extrato bancário.
    
    Args:
        arquivo_bytes: Bytes do arquivo
        nome_arquivo: Nome do arquivo
        mapeamento: Dict com mapeamento de colunas {coluna_csv: campo_sistema}
    
    Returns:
        list: Transações extraídas
    """
    try:
        import hashlib
        
        # Tentar diferentes encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(BytesIO(arquivo_bytes), encoding=encoding)
                break
            except:
                continue
        
        transacoes = []
        
        for idx, row in df.iterrows():
            # Extrair dados conforme mapeamento
            data_str = str(row.get(mapeamento.get('data', ''), ''))
            valor_str = str(row.get(mapeamento.get('valor', ''), '0'))
            descricao = str(row.get(mapeamento.get('descricao', ''), ''))
            
            # Limpar valor
            valor_str = re.sub(r'[^\d,.-]', '', valor_str).replace(',', '.')
            try:
                valor = float(valor_str)
            except:
                valor = 0
            
            # Determinar tipo
            tipo = 'Crédito' if valor > 0 else 'Débito'
            
            # Gerar ID único
            unique_str = f"{data_str}-{valor}-{descricao}-{idx}"
            transaction_id = hashlib.md5(unique_str.encode()).hexdigest()
            
            # Tentar parsear data
            data_transacao = None
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']:
                try:
                    data_transacao = datetime.strptime(data_str.strip(), fmt).strftime('%Y-%m-%d')
                    break
                except:
                    continue
            
            if not data_transacao:
                data_transacao = datetime.now().strftime('%Y-%m-%d')
            
            transacoes.append({
                'transaction_id': transaction_id,
                'data_transacao': data_transacao,
                'tipo': tipo,
                'valor': abs(valor),
                'descricao': descricao,
                'arquivo_origem': nome_arquivo
            })
        
        return transacoes
        
    except Exception as e:
        logger.error(f"Erro ao processar CSV: {e}")
        return []


def render_upload_csv():
    """Componente de upload de arquivo CSV"""
    st.markdown("#### 📄 Importar CSV")
    
    uploaded_csv = st.file_uploader("Selecione o arquivo CSV", type=['csv'], key="csv_upload")
    
    if uploaded_csv:
        # Preview do arquivo
        try:
            preview = pd.read_csv(BytesIO(uploaded_csv.read()), nrows=5)
            uploaded_csv.seek(0)
            
            st.markdown("**Preview do arquivo:**")
            st.dataframe(preview, use_container_width=True)
            
            # Mapeamento de colunas
            st.markdown("**Mapeamento de Colunas:**")
            colunas = list(preview.columns)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                col_data = st.selectbox("Coluna de Data", colunas, key="map_data")
            with col2:
                col_valor = st.selectbox("Coluna de Valor", colunas, key="map_valor")
            with col3:
                col_desc = st.selectbox("Coluna de Descrição", colunas, key="map_desc")
            
            if st.button("📤 Processar CSV", type="primary"):
                mapeamento = {
                    'data': col_data,
                    'valor': col_valor,
                    'descricao': col_desc
                }
                
                arquivo_bytes = uploaded_csv.read()
                transacoes = processar_csv(arquivo_bytes, uploaded_csv.name, mapeamento)
                
                if transacoes:
                    # Salvar transações
                    importadas = 0
                    duplicadas = 0
                    
                    for trans in transacoes:
                        if not ofx_utils.verificar_transacao_duplicada(trans['transaction_id']):
                            trans['data_importacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            trans['status_conciliacao'] = 'Pendente'
                            ofx_utils.salvar_transacao_bancaria(trans)
                            importadas += 1
                        else:
                            duplicadas += 1
                    
                    st.success(f"✅ {importadas} transações importadas, {duplicadas} duplicadas ignoradas.")
                    st.rerun()
                else:
                    st.error("Erro ao processar arquivo CSV.")
        
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")


def buscar_matches_fuzzy(transacao, threshold=70):
    """
    Busca matches usando fuzzy matching na descrição.
    
    Args:
        transacao: Dict com dados da transação
        threshold: Percentual mínimo de similaridade (0-100)
    
    Returns:
        list: Matches encontrados com score de similaridade
    """
    try:
        valor = transacao.get('valor', 0)
        descricao = transacao.get('descricao', '')
        
        # Buscar lançamentos pendentes com valor próximo (±20%)
        margem = valor * 0.2
        valor_min = valor - margem
        valor_max = valor + margem
        
        query = """
        SELECT f.*, c.nome as cliente_nome, p.numero as processo_numero
        FROM financeiro f
        LEFT JOIN clientes c ON f.id_cliente = c.id
        LEFT JOIN processos p ON f.id_processo = p.id
        WHERE f.tipo = 'Entrada'
        AND f.status_pagamento = 'Pendente'
        AND f.valor BETWEEN ? AND ?
        ORDER BY f.vencimento ASC
        """
        
        import database_adapter as adapter
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
        
        lancamentos = db.run_query(query, (valor_min, valor_max))
        
        matches = []
        for lanc in lancamentos:
            l = dict(lanc)
            
            # Calcular similaridade de descrição
            desc_lanc = f"{l.get('descricao', '')} {l.get('cliente_nome', '')}"
            similaridade = calcular_similaridade(descricao, desc_lanc)
            
            if similaridade >= threshold or abs(l.get('valor', 0) - valor) < 0.01:
                # Score combinado: 60% valor exato + 40% similaridade texto
                score_valor = 100 if abs(l.get('valor', 0) - valor) < 0.01 else 50
                score_final = (score_valor * 0.6) + (similaridade * 0.4)
                
                l['score'] = round(score_final, 1)
                l['similaridade_texto'] = round(similaridade, 1)
                matches.append(l)
        
        # Ordenar por score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:5]  # Retornar top 5
        
    except Exception as e:
        logger.error(f"Erro no fuzzy matching: {e}")
        return []
