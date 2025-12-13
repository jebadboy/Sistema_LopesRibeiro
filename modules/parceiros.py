import streamlit as st
import database as db
import pandas as pd
from datetime import datetime
import utils as ut
import re

def render():
    st.markdown("<h1 style='color: var(--text-main);'>🤝 Gestão de Parceiros</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Lista de Parceiros", 
        "➕ Novo Parceiro",
        "💰 Histórico de Repasses",
        "📊 Relatório de Pagamentos"
    ])
    
    with tab1:
        render_lista_parceiros()
        
    with tab2:
        render_novo_parceiro()
    
    with tab3:
        render_historico_repasses()
    
    with tab4:
        render_relatorio_pagamentos()


def render_lista_parceiros():
    """Lista parceiros com opção de edição e exclusão."""
    df = db.sql_get("parceiros")
    
    if df.empty:
        st.info("Nenhum parceiro cadastrado.")
        return
    
    # Estatísticas rápidas
    total_parceiros = len(df)
    ativos = len(df[df['ativo'] == 1]) if 'ativo' in df.columns else total_parceiros
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Parceiros", total_parceiros)
    col2.metric("Parceiros Ativos", ativos)
    col3.metric("Parceiros Inativos", total_parceiros - ativos)
    
    st.divider()
    
    # Filtro de status
    filtro_status = st.selectbox(
        "Filtrar por Status",
        ["Todos", "Ativos", "Inativos"],
        key="filtro_status_parceiros"
    )
    
    df_filtrado = df.copy()
    if filtro_status == "Ativos":
        df_filtrado = df[df['ativo'] == 1]
    elif filtro_status == "Inativos":
        df_filtrado = df[df['ativo'] == 0]
    
    # Listar parceiros
    for index, row in df_filtrado.iterrows():
        status_icon = "🟢" if row.get('ativo', 1) else "🔴"
        with st.expander(f"{status_icon} {row['nome']} ({row['email'] or 'Sem email'})"):
            
            # Botão de edição no topo
            if st.button("✏️ Editar", key=f"edit_parc_{row['id']}"):
                st.session_state[f"editando_parceiro_{row['id']}"] = True
                st.rerun()
            
            # Modo de edição
            if st.session_state.get(f"editando_parceiro_{row['id']}", False):
                render_form_edicao(row)
            else:
                # Visualização normal
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**CPF/CNPJ:** {row['cpf_cnpj'] or '-'}")
                    st.write(f"**Telefone:** {row['telefone'] or '-'}")
                    st.write(f"**Chave PIX:** {row['chave_pix'] or '-'}")
                with c2:
                    st.write(f"**Dados Bancários:** {row['dados_bancarios'] or '-'}")
                    st.write(f"**Status:** {'Ativo' if row.get('ativo', 1) else 'Inativo'}")
                
                # Processos vinculados
                st.divider()
                processos_parceiro = get_processos_parceiro(row['nome'])
                if not processos_parceiro.empty:
                    st.caption(f"📁 **{len(processos_parceiro)} Processo(s) Vinculado(s)**")
                    for _, proc in processos_parceiro.iterrows():
                        percentual = proc.get('parceiro_percentual', 0) or 0
                        st.write(f"• {proc['cliente_nome']} - {proc['acao'][:30]}... ({percentual}%)")
                else:
                    st.caption("Nenhum processo vinculado a este parceiro.")
                
                # Ações
                st.divider()
                col_actions = st.columns(3)
                
                with col_actions[0]:
                    if row.get('ativo', 1):
                        if st.button("🔴 Desativar", key=f"deactivate_{row['id']}"):
                            db.crud_update("parceiros", {"ativo": 0}, "id = ?", (row['id'],), f"Parceiro desativado: {row['nome']}")
                            st.rerun()
                    else:
                        if st.button("🟢 Ativar", key=f"activate_{row['id']}"):
                            db.crud_update("parceiros", {"ativo": 1}, "id = ?", (row['id'],), f"Parceiro ativado: {row['nome']}")
                            st.rerun()
                
                with col_actions[2]:
                    if st.button("🗑️ Excluir", key=f"del_parc_{row['id']}"):
                        db.crud_delete("parceiros", "id = ?", (row['id'],), f"Exclusão de parceiro {row['nome']}")
                        st.rerun()


def render_form_edicao(row):
    """Formulário de edição de parceiro existente."""
    st.markdown("### ✏️ Editando Parceiro")
    
    with st.form(f"form_edit_parceiro_{row['id']}"):
        nome = st.text_input("Nome Completo *", value=row['nome'])
        c1, c2 = st.columns(2)
        cpf_cnpj = c1.text_input("CPF/CNPJ", value=row['cpf_cnpj'] or "")
        email = c2.text_input("Email", value=row['email'] or "")
        
        c3, c4 = st.columns(2)
        telefone = c3.text_input("Telefone", value=row['telefone'] or "")
        chave_pix = c4.text_input("Chave PIX", value=row['chave_pix'] or "")
        
        dados_bancarios = st.text_area("Dados Bancários", value=row['dados_bancarios'] or "")
        
        col_btn1, col_btn2 = st.columns(2)
        submitted = col_btn1.form_submit_button("💾 Salvar Alterações", type="primary")
        cancelar = col_btn2.form_submit_button("❌ Cancelar")
        
        if cancelar:
            st.session_state[f"editando_parceiro_{row['id']}"] = False
            st.rerun()
        
        if submitted:
            if not nome:
                st.error("Nome é obrigatório.")
            elif email and not ut.validar_email(email):
                st.error("E-mail inválido.")
            else:
                dados = {
                    "nome": nome,
                    "cpf_cnpj": ut.formatar_documento(cpf_cnpj) if cpf_cnpj else "",
                    "email": email,
                    "telefone": ut.formatar_celular(telefone) if telefone else "",
                    "chave_pix": chave_pix,
                    "dados_bancarios": dados_bancarios
                }
                db.crud_update("parceiros", dados, "id = ?", (row['id'],), f"Parceiro atualizado: {nome}")
                st.session_state[f"editando_parceiro_{row['id']}"] = False
                st.success("Parceiro atualizado com sucesso!")
                st.rerun()


def render_novo_parceiro():
    """Cadastro de novo parceiro."""
    st.markdown("### Cadastrar Novo Parceiro")
    
    with st.form("form_novo_parceiro"):
        nome = st.text_input("Nome Completo *")
        c1, c2 = st.columns(2)
        cpf_cnpj = c1.text_input("CPF/CNPJ")
        email = c2.text_input("Email")
        
        c3, c4 = st.columns(2)
        telefone = c3.text_input("Telefone")
        chave_pix = c4.text_input("Chave PIX")
        
        dados_bancarios = st.text_area("Dados Bancários (Banco, Agência, Conta)")
        
        submitted = st.form_submit_button("Salvar Parceiro", type="primary")
        
        if submitted:
            # Proteção contra clique duplo
            if st.session_state.get('salvando_parceiro', False):
                st.warning("⚠️ Salvamento em andamento, aguarde...")
            elif not nome:
                st.error("Nome é obrigatório.")
            elif email and not ut.validar_email(email):
                st.error("E-mail inválido.")
            else:
                st.session_state['salvando_parceiro'] = True
                try:
                    # Formatações
                    cpf_cnpj_fmt = ut.formatar_documento(cpf_cnpj) if cpf_cnpj else ""
                    telefone_fmt = ut.formatar_celular(telefone) if telefone else ""
                    
                    dados = {
                        "nome": nome,
                        "cpf_cnpj": cpf_cnpj_fmt,
                        "email": email,
                        "telefone": telefone_fmt,
                        "chave_pix": chave_pix,
                        "dados_bancarios": dados_bancarios,
                        "ativo": 1
                    }
                    db.crud_insert("parceiros", dados, f"Novo parceiro: {nome}")
                    st.success("Parceiro cadastrado com sucesso!")
                    st.session_state['salvando_parceiro'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
                    st.session_state['salvando_parceiro'] = False


def render_historico_repasses():
    """Exibe histórico de repasses/comissões por parceiro."""
    st.markdown("### 💰 Histórico de Repasses")
    
    # Buscar parceiros
    df_parceiros = db.sql_get("parceiros")
    
    if df_parceiros.empty:
        st.info("Cadastre parceiros para visualizar o histórico de repasses.")
        return
    
    # Seletor de parceiro
    parceiro_selecionado = st.selectbox(
        "Selecione o Parceiro",
        ["Todos"] + df_parceiros['nome'].tolist(),
        key="parceiro_historico"
    )
    
    # Buscar processos com esse parceiro
    if parceiro_selecionado == "Todos":
        processos = db.sql_get_query("""
            SELECT p.id, p.numero, p.cliente_nome, p.acao, p.parceiro_nome, 
                   p.parceiro_percentual, p.valor_causa, p.fase_processual
            FROM processos p
            WHERE p.parceiro_nome IS NOT NULL AND p.parceiro_nome != ''
            ORDER BY p.id DESC
        """)
    else:
        processos = db.sql_get_query("""
            SELECT p.id, p.numero, p.cliente_nome, p.acao, p.parceiro_nome, 
                   p.parceiro_percentual, p.valor_causa, p.fase_processual
            FROM processos p
            WHERE p.parceiro_nome = ?
            ORDER BY p.id DESC
        """, (parceiro_selecionado,))
    
    if processos.empty:
        st.warning("Nenhum processo encontrado para este parceiro.")
        return
    
    # Calcular totais
    total_valor_causa = processos['valor_causa'].fillna(0).sum()
    
    # Calcular comissões estimadas
    processos['comissao_estimada'] = processos.apply(
        lambda row: (row['valor_causa'] or 0) * (row['parceiro_percentual'] or 0) / 100, 
        axis=1
    )
    total_comissao = processos['comissao_estimada'].sum()
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Processos Vinculados", len(processos))
    col2.metric("Valor Total das Causas", f"R$ {total_valor_causa:,.2f}")
    col3.metric("Comissão Estimada Total", f"R$ {total_comissao:,.2f}")
    
    st.divider()
    
    # Tabela detalhada
    st.markdown("#### 📋 Detalhamento por Processo")
    
    for _, proc in processos.iterrows():
        with st.expander(f"📁 {proc['cliente_nome']} - {proc['acao'][:40]}..."):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Número:** {proc['numero'] or 'Não informado'}")
                st.write(f"**Valor da Causa:** R$ {proc['valor_causa'] or 0:,.2f}")
                st.write(f"**Fase:** {proc['fase_processual'] or 'Não informada'}")
            with c2:
                st.write(f"**Parceiro:** {proc['parceiro_nome']}")
                st.write(f"**Percentual:** {proc['parceiro_percentual'] or 0}%")
                st.write(f"**Comissão Estimada:** R$ {proc['comissao_estimada']:,.2f}")
            
            # Buscar lançamentos financeiros deste processo
            lancamentos = db.sql_get_query("""
                SELECT data, descricao, valor, status_pagamento, tipo
                FROM financeiro
                WHERE id_processo = ?
                ORDER BY data DESC
            """, (proc['id'],))
            
            if not lancamentos.empty:
                st.markdown("**Lançamentos Financeiros:**")
                for _, lanc in lancamentos.iterrows():
                    status_icon = "✅" if lanc['status_pagamento'] == 'Pago' else "⏳"
                    st.write(f"  {status_icon} {lanc['data']} - {lanc['descricao']}: R$ {lanc['valor']:,.2f}")


def render_relatorio_pagamentos():
    """Relatório consolidado de pagamentos a parceiros."""
    st.markdown("### 📊 Relatório de Pagamentos a Parceiros")
    
    # Período
    col1, col2 = st.columns(2)
    data_inicio = col1.date_input("Data Início", value=datetime(datetime.now().year, 1, 1))
    data_fim = col2.date_input("Data Fim", value=datetime.now())
    
    if st.button("🔄 Gerar Relatório", type="primary"):
        # Buscar todos os processos com parceiros
        processos = db.sql_get_query("""
            SELECT p.parceiro_nome, p.parceiro_percentual, p.valor_causa, p.cliente_nome, p.acao,
                   f.valor as valor_pago, f.data as data_pagamento
            FROM processos p
            LEFT JOIN financeiro f ON f.id_processo = p.id AND f.status_pagamento = 'Pago'
            WHERE p.parceiro_nome IS NOT NULL AND p.parceiro_nome != ''
            AND (f.data IS NULL OR (f.data >= ? AND f.data <= ?))
        """, (str(data_inicio), str(data_fim)))
        
        if processos.empty:
            st.warning("Nenhum dado encontrado para o período selecionado.")
            return
        
        # Agrupar por parceiro
        resumo = processos.groupby('parceiro_nome').agg({
            'valor_causa': 'sum',
            'valor_pago': 'sum',
            'cliente_nome': 'count'
        }).reset_index()
        
        resumo.columns = ['Parceiro', 'Valor Total Causas', 'Valor Pago no Período', 'Qtd Processos']
        
        # Calcular comissão devida (estimativa)
        resumo['Comissão Estimada'] = resumo['Valor Total Causas'] * 0.10  # 10% padrão
        
        st.markdown("#### 📋 Resumo por Parceiro")
        st.dataframe(
            resumo.style.format({
                'Valor Total Causas': 'R$ {:,.2f}',
                'Valor Pago no Período': 'R$ {:,.2f}',
                'Comissão Estimada': 'R$ {:,.2f}'
            }),
            use_container_width=True
        )
        
        # Totais
        st.divider()
        total_causas = resumo['Valor Total Causas'].sum()
        total_pago = resumo['Valor Pago no Período'].sum()
        total_comissao = resumo['Comissão Estimada'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Causas", f"R$ {total_causas:,.2f}")
        col2.metric("Total Pago", f"R$ {total_pago:,.2f}")
        col3.metric("Comissão Total Estimada", f"R$ {total_comissao:,.2f}")


# === FUNÇÕES AUXILIARES ===

def get_processos_parceiro(nome_parceiro: str) -> pd.DataFrame:
    """Retorna processos vinculados a um parceiro."""
    return db.sql_get_query("""
        SELECT id, numero, cliente_nome, acao, parceiro_percentual, fase_processual
        FROM processos
        WHERE parceiro_nome = ?
        ORDER BY id DESC
    """, (nome_parceiro,))


def get_total_comissoes_parceiro(nome_parceiro: str) -> float:
    """Calcula o total de comissões devidas a um parceiro."""
    processos = get_processos_parceiro(nome_parceiro)
    if processos.empty:
        return 0.0
    
    total = 0.0
    for _, proc in processos.iterrows():
        # Buscar entradas pagas do processo
        entradas = db.sql_get_query("""
            SELECT SUM(valor) as total
            FROM financeiro
            WHERE id_processo = ? AND tipo = 'Entrada' AND status_pagamento = 'Pago'
        """, (proc['id'],))
        
        valor_recebido = entradas.iloc[0]['total'] if not entradas.empty and entradas.iloc[0]['total'] else 0
        percentual = proc.get('parceiro_percentual', 0) or 0
        total += valor_recebido * (percentual / 100)
    
    return total
