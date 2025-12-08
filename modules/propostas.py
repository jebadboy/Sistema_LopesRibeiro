import streamlit as st
import database as db
import utils as ut
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def render():
    st.markdown("<h1 style='color: var(--text-main);'>💰 Gestão de Propostas</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Funil de Vendas", "📑 Modelos de Proposta", "📈 Relatórios"])
    
    with tab1:
        render_funil()
        
    with tab2:
        render_modelos()
    
    with tab3:
        render_relatorios()

def render_funil():
    st.markdown("### Funil de Vendas")
    
    # Buscar clientes com status de proposta relevante
    df = db.sql_get("clientes")
    if df.empty:
        st.info("Nenhum cliente cadastrado.")
        return
        
    # Filtrar apenas quem está em negociação
    df = df[df['status_cliente'] == 'EM NEGOCIAÇÃO']
    
    if df.empty:
        st.info("Nenhum cliente em negociação no momento.")
        st.caption("Para adicionar clientes ao funil, acesse Clientes (CRM) e altere o status para 'EM NEGOCIAÇÃO'.")
        return
    
    # Colunas do Kanban
    fases = ["Em Análise", "Enviada", "Aprovada", "Rejeitada"]
    
    # Garantir que status_proposta tenha valor
    df['status_proposta'] = df['status_proposta'].fillna("Em Análise")
    
    # Métricas Rápidas
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    df['proposta_valor'] = pd.to_numeric(df['proposta_valor'], errors='coerce').fillna(0)
    
    total_pipeline = df[df['status_proposta'].isin(['Em Análise', 'Enviada'])]['proposta_valor'].sum()
    total_aprovado = df[df['status_proposta'] == 'Aprovada']['proposta_valor'].sum()
    total_rejeitado = df[df['status_proposta'] == 'Rejeitada']['proposta_valor'].sum()
    qtd_negociacao = len(df[df['status_proposta'].isin(['Em Análise', 'Enviada'])])
    
    col_m1.metric("🎯 Pipeline", ut.formatar_moeda(total_pipeline), f"{qtd_negociacao} propostas")
    col_m2.metric("✅ Aprovado", ut.formatar_moeda(total_aprovado))
    col_m3.metric("❌ Rejeitado", ut.formatar_moeda(total_rejeitado))
    
    # Taxa de conversão
    total_finalizados = len(df[df['status_proposta'].isin(['Aprovada', 'Rejeitada'])])
    aprovados = len(df[df['status_proposta'] == 'Aprovada'])
    taxa = (aprovados / total_finalizados * 100) if total_finalizados > 0 else 0
    col_m4.metric("📊 Taxa Conversão", f"{taxa:.1f}%")
    
    st.divider()
    
    # Kanban
    cols = st.columns(len(fases))
    
    for i, fase in enumerate(fases):
        with cols[i]:
            # Cor do header baseado na fase
            cores = {
                "Em Análise": "#3498db",
                "Enviada": "#f39c12", 
                "Aprovada": "#27ae60",
                "Rejeitada": "#e74c3c"
            }
            st.markdown(f"<h4 style='color: {cores[fase]};'>{fase}</h4>", unsafe_allow_html=True)
            
            df_fase = df[df['status_proposta'] == fase]
            st.caption(f"{len(df_fase)} propostas")
            
            for idx, row in df_fase.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['nome']}**")
                    val = row['proposta_valor'] if row['proposta_valor'] else 0
                    st.caption(f"💰 R$ {val:,.2f}")
                    
                    # Objeto da proposta
                    if row.get('proposta_objeto'):
                        st.caption(f"📋 {row['proposta_objeto'][:30]}...")
                    
                    # Indicador de Estagnação
                    if row.get('data_cadastro'):
                        try:
                            dt_cad_str = str(row['data_cadastro'])[:10]
                            if '-' in dt_cad_str:
                                dt_cad = datetime.strptime(dt_cad_str, '%Y-%m-%d')
                            else:
                                dt_cad = datetime.strptime(dt_cad_str, '%d/%m/%Y')
                            
                            dias = (datetime.now() - dt_cad).days
                            if dias > 30:
                                st.warning(f"⏳ {dias} dias na base")
                            elif dias > 10:
                                st.caption(f"🕒 {dias} dias")
                        except:
                            pass
                    
                    # Ações
                    col_act1, col_act2 = st.columns(2)
                    
                    with col_act1:
                        # Mover fase
                        nova_fase = st.selectbox(
                            "Mover:", 
                            fases, 
                            index=fases.index(fase), 
                            key=f"mv_prop_{row['id']}", 
                            label_visibility="collapsed"
                        )
                        
                        if nova_fase != fase:
                            db.sql_run("UPDATE clientes SET status_proposta=? WHERE id=?", (nova_fase, row['id']))
                            
                            if nova_fase == "Aprovada":
                                st.toast(f"🎉 Proposta de {row['nome']} Aprovada!")
                            
                            st.rerun()
                    
                    with col_act2:
                        # Botão Converter em Processo (apenas para Aprovadas)
                        if fase == "Aprovada":
                            if st.button("➡️ Processo", key=f"conv_{row['id']}", help="Converter em Processo"):
                                converter_em_processo(row)
                                st.rerun()

def converter_em_processo(cliente_row):
    """Converte proposta aprovada em processo."""
    try:
        # Criar processo com dados do cliente
        dados_processo = {
            "numero": "",  # Será preenchido depois
            "cliente_nome": cliente_row['nome'],
            "id_cliente": cliente_row['id'],
            "area": "Cível",  # Padrão, pode ser editado
            "acao": cliente_row.get('proposta_objeto', 'Ação a definir'),
            "status": "Ativo",
            "fase_processual": "Petição Inicial",
            "valor_causa": cliente_row.get('proposta_valor', 0),
            "tipo_honorario": "Entrada + Êxito",
            "responsavel": "A definir"
        }
        
        # Inserir processo
        processo_id = db.crud_insert("processos", dados_processo, f"Processo criado via proposta: {cliente_row['nome']}")
        
        # Atualizar cliente para ATIVO
        db.sql_run("""
            UPDATE clientes 
            SET status_cliente = 'ATIVO', status_proposta = 'Convertida'
            WHERE id = ?
        """, (cliente_row['id'],))
        
        st.success(f"✅ Processo #{processo_id} criado para {cliente_row['nome']}!")
        st.toast("Acesse Processos para completar os dados.", icon="📋")
        
    except Exception as e:
        st.error(f"Erro ao criar processo: {e}")

def render_modelos():
    st.markdown("### Modelos de Proposta")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("#### ➕ Novo Modelo")
        with st.form("form_modelo"):
            nome = st.text_input("Nome do Modelo (Ex: Divórcio)")
            area = st.selectbox("Área", ["Cível", "Família", "Trabalhista", "Previdenciário", "Criminal", "Outros"])
            valor = st.number_input("Valor Sugerido (R$)", min_value=0.0, step=100.0)
            desc = st.text_area("Descrição Padrão (Objeto)")
            
            if st.form_submit_button("💾 Salvar Modelo", type="primary"):
                if not nome:
                    st.error("Nome é obrigatório.")
                else:
                    try:
                        db.sql_run(
                            "INSERT INTO modelos_proposta (nome_modelo, area_atuacao, descricao, titulo) VALUES (?,?,?,?)",
                            (nome, area, desc, f"R$ {valor:,.2f}")
                        )
                        st.success("Modelo salvo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
    
    with c2:
        st.markdown("#### 📚 Modelos Cadastrados")
        df_mod = db.sql_get("modelos_proposta")
        
        if df_mod.empty:
            st.info("Nenhum modelo cadastrado. Crie seu primeiro modelo ao lado.")
        else:
            for idx, row in df_mod.iterrows():
                titulo_valor = row.get('titulo', 'R$ 0,00')
                with st.expander(f"📄 {row['nome_modelo']} ({row['area_atuacao']}) - {titulo_valor}"):
                    st.write(row.get('descricao', 'Sem descrição'))
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("📋 Aplicar a Cliente", key=f"apply_mod_{row['id']}"):
                            st.session_state['modelo_aplicar'] = row
                            st.info("Selecione um cliente abaixo para aplicar este modelo.")
                    with col_b:
                        if st.button("🗑️ Excluir", key=f"del_mod_{row['id']}"):
                            db.sql_run("DELETE FROM modelos_proposta WHERE id=?", (row['id'],))
                            st.rerun()
        
        # Aplicar modelo a cliente
        if 'modelo_aplicar' in st.session_state:
            st.divider()
            st.markdown("#### Aplicar Modelo a Cliente")
            
            modelo = st.session_state['modelo_aplicar']
            st.info(f"Modelo selecionado: **{modelo['nome_modelo']}**")
            
            # Selecionar cliente
            df_cli = db.sql_get("clientes")
            if not df_cli.empty:
                clientes_neg = df_cli[df_cli['status_cliente'] == 'EM NEGOCIAÇÃO']['nome'].tolist()
                if clientes_neg:
                    cliente_sel = st.selectbox("Selecione o Cliente", clientes_neg)
                    
                    if st.button("✅ Aplicar Modelo", type="primary"):
                        cli_id = df_cli[df_cli['nome'] == cliente_sel].iloc[0]['id']
                        # Extrair valor do titulo
                        try:
                            valor_str = modelo.get('titulo', 'R$ 0').replace('R$', '').replace('.', '').replace(',', '.').strip()
                            valor_num = float(valor_str) if valor_str else 0
                        except:
                            valor_num = 0
                        
                        db.sql_run("""
                            UPDATE clientes 
                            SET proposta_valor = ?, proposta_objeto = ?
                            WHERE id = ?
                        """, (valor_num, modelo.get('descricao', ''), cli_id))
                        
                        st.success(f"Modelo aplicado a {cliente_sel}!")
                        del st.session_state['modelo_aplicar']
                        st.rerun()
                else:
                    st.warning("Nenhum cliente em negociação para aplicar o modelo.")
            
            if st.button("Cancelar"):
                del st.session_state['modelo_aplicar']
                st.rerun()

def render_relatorios():
    st.markdown("### 📈 Relatório de Conversão")
    
    df = db.sql_get("clientes")
    
    if df.empty:
        st.info("Nenhum dado para análise.")
        return
    
    # Filtrar apenas quem teve algum status de proposta
    df_prop = df[df['status_proposta'].notna() & (df['status_proposta'] != '')]
    
    if df_prop.empty:
        st.info("Nenhuma proposta registrada ainda.")
        return
    
    # Métricas
    st.markdown("#### Métricas do Funil")
    
    total_propostas = len(df_prop)
    aprovadas = len(df_prop[df_prop['status_proposta'] == 'Aprovada'])
    rejeitadas = len(df_prop[df_prop['status_proposta'] == 'Rejeitada'])
    em_andamento = len(df_prop[df_prop['status_proposta'].isin(['Em Análise', 'Enviada'])])
    convertidas = len(df_prop[df_prop['status_proposta'] == 'Convertida'])
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Propostas", total_propostas)
    c2.metric("Em Andamento", em_andamento)
    c3.metric("Aprovadas", aprovadas)
    c4.metric("Convertidas", convertidas)
    c5.metric("Rejeitadas", rejeitadas)
    
    st.divider()
    
    # Taxas
    st.markdown("#### Taxas de Conversão")
    
    finalizadas = aprovadas + rejeitadas + convertidas
    taxa_aprovacao = (aprovadas + convertidas) / finalizadas * 100 if finalizadas > 0 else 0
    taxa_rejeicao = rejeitadas / finalizadas * 100 if finalizadas > 0 else 0
    
    col1, col2 = st.columns(2)
    col1.metric("✅ Taxa de Aprovação", f"{taxa_aprovacao:.1f}%")
    col2.metric("❌ Taxa de Rejeição", f"{taxa_rejeicao:.1f}%")
    
    st.divider()
    
    # Gráfico de Funil
    st.markdown("#### Visualização do Funil")
    
    dados_funil = {
        'Fase': ['Em Análise', 'Enviada', 'Aprovada', 'Convertida', 'Rejeitada'],
        'Quantidade': [
            len(df_prop[df_prop['status_proposta'] == 'Em Análise']),
            len(df_prop[df_prop['status_proposta'] == 'Enviada']),
            aprovadas,
            convertidas,
            rejeitadas
        ]
    }
    
    df_chart = pd.DataFrame(dados_funil)
    st.bar_chart(df_chart.set_index('Fase'))
    
    # Valor por fase
    st.markdown("#### Valor por Fase")
    
    df_prop['proposta_valor'] = pd.to_numeric(df_prop['proposta_valor'], errors='coerce').fillna(0)
    
    valor_por_fase = df_prop.groupby('status_proposta')['proposta_valor'].sum()
    
    if not valor_por_fase.empty:
        for fase, valor in valor_por_fase.items():
            st.write(f"**{fase}:** {ut.formatar_moeda(valor)}")
