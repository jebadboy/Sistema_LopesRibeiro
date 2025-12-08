import streamlit as st
import database as db
import utils as ut
from datetime import datetime, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def registrar_backup():
    """Registra que um backup foi realizado agora pelo usuário atual."""
    now = datetime.now().isoformat()
    db.set_config('last_backup', now)
    
    if hasattr(st, 'session_state') and 'user' in st.session_state:
        db.set_config('last_backup_user', st.session_state.user)
    else:
        db.set_config('last_backup_user', 'Sistema')
        
    # Não precisamos de st.rerun() aqui pois o botão de download já causa rerun

def render():
    # --- CSS Personalizado para Cards ---
    st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #ccc;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    
    @keyframes pulse-yellow {
        0% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 193, 7, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0); }
    }
    
    .card-red { border-left-color: #dc3545; }
    .card-blue { border-left-color: #0d6efd; }
    .card-yellow { border-left-color: #ffc107; }
    .card-green { border-left-color: #28a745; }
    
    .pulse-red { animation: pulse-red 2s infinite; }
    .pulse-yellow { animation: pulse-yellow 2s infinite; }
    
    .card-title {
        font-size: 14px;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 5px;
    }
    .card-value {
        font-size: 24px;
        font-weight: 700;
        color: #212529;
    }
    
    .link-btn {
        display: inline-block;
        padding: 10px 20px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        color: #212529;
        text-decoration: none;
        font-weight: 500;
        margin-right: 10px;
        margin-bottom: 10px;
        transition: all 0.2s;
    }
    .link-btn:hover {
        background-color: #e9ecef;
        border-color: #ced4da;
        color: #0f172a;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📊 Dashboard")
    
    # --- 1. Alerta de Backup (Funcional) ---
    last_backup_str = db.get_config('last_backup')
    mostrar_aviso = True
    db_path = "dados_escritorio.db"
    
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        if last_backup_str:
            try:
                last_backup = datetime.fromisoformat(last_backup_str)
                dias_desde_backup = (datetime.now() - last_backup).days
                if dias_desde_backup < 7:
                    mostrar_aviso = False
            except:
                pass # Se erro no parse, mostra aviso
    else:
        st.error("🚨 CRÍTICO: Banco de dados não encontrado ou vazio! Verifique o arquivo dados_escritorio.db")
        mostrar_aviso = False # Já mostrou erro crítico
            
    if mostrar_aviso:
        st.warning("⚠️ Atenção: Você ainda não realizou nenhum backup esta semana. Recomendamos fazer um novo backup para garantir a segurança dos seus dados.")
    
    # --- 2. Visão Geral (Cards) ---
    st.subheader("Visão Geral")
    st.caption("Resumo das atividades do escritório.")
    
    # Obter dados reais
    # Prazos próximos (7 dias)
    prazos_count = 0
    audiencias_count = 0
    a_receber_vencidos_count = 0
    
    try:
        # Prazos e Audiências
        agenda_df = db.get_agenda_eventos()
        if not agenda_df.empty:
            hoje = datetime.now().strftime('%Y-%m-%d')
            limite_7_dias = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Prazos próximos
            prazos = agenda_df[
                (agenda_df['tipo'] == 'prazo') & 
                (agenda_df['status'] == 'pendente') &
                (agenda_df['data_evento'] >= hoje) &
                (agenda_df['data_evento'] <= limite_7_dias)
            ]
            prazos_count = len(prazos)
            
            # Audiências próximas (qualquer data futura próxima)
            audiencias = agenda_df[
                (agenda_df['tipo'] == 'audiencia') & 
                (agenda_df['status'] == 'pendente') &
                (agenda_df['data_evento'] >= hoje)
            ]
            audiencias_count = len(audiencias)
            
        # Financeiro Vencido
        # (Assumindo que existe função ou query para isso, se não, usar 0 por segurança)
        # Implementação simplificada:
        fin_df = db.sql_get('financeiro')
        if not fin_df.empty:
            vencidos = fin_df[
                (fin_df['tipo'] == 'receita') &
                (fin_df['status'] == 'pendente') &
                (fin_df['data_vencimento'] < hoje)
            ]
            a_receber_vencidos_count = len(vencidos)
            
    except Exception as e:
        # Silencioso em prod, mas bom saber
        pass

    # Definir cores e animações dinamicamente
    class_prazos = "card-yellow pulse-yellow" if prazos_count > 0 else "card-green"
    class_audiencias = "card-blue" if audiencias_count > 0 else "card-green" # Audiências sem pulse por enquanto
    class_vencidos = "card-red pulse-red" if a_receber_vencidos_count > 0 else "card-green"
    
    # Aniversários
    from modules import aniversarios
    aniv_hoje = aniversarios.get_aniversariantes_hoje()
    aniv_proximos = aniversarios.get_aniversariantes_semana()
    
    aniv_count = len(aniv_hoje)
    aniv_icon = "🎉"
    aniv_label = "Aniversariantes Hoje"
    class_aniv = "card-green"
    
    if aniv_count > 0:
        class_aniv = "card-blue pulse-yellow" # Destaque festivo
    elif len(aniv_proximos) > 0:
        aniv_count = len(aniv_proximos)
        aniv_icon = "📅"
        aniv_label = "Próximos 7 dias"
        class_aniv = "card-yellow"

    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card {class_prazos}">
            <div class="card-title">{'🟡' if prazos_count > 0 else '🟢'} Prazos Próximos (7 dias)</div>
            <div class="card-value">{prazos_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card {class_audiencias}">
            <div class="card-title">{'👥' if audiencias_count > 0 else '🟢'} Audiências Próximas</div>
            <div class="card-value">{audiencias_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="metric-card {class_vencidos}">
            <div class="card-title">{'🔴' if a_receber_vencidos_count > 0 else '🟢'} A Receber (Vencidos)</div>
            <div class="card-value">{a_receber_vencidos_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c4:
        st.markdown(f"""
        <div class="metric-card {class_aniv}">
            <div class="card-title">{aniv_icon} {aniv_label}</div>
            <div class="card-value">{aniv_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Detalhes compactos abaixo do card
        if not aniv_hoje.empty:
            with st.expander("Ver Aniversariantes", expanded=False):
                for idx, cliente in aniv_hoje.iterrows():
                    idade = aniversarios.calcular_idade(cliente['data_nascimento']) if cliente['data_nascimento'] else None
                    st.caption(f"🎂 **{cliente['nome']}** ({idade} anos)")
                    if cliente['telefone']:
                        template = aniversarios.get_template_mensagem()
                        mensagem = aniversarios.formatar_mensagem_aniversario(cliente['nome'], idade, template)
                        link_whatsapp = aniversarios.gerar_link_whatsapp(cliente['telefone'], mensagem)
                        st.link_button("📱 WhatsApp", link_whatsapp, key=f"dash_wpp_{cliente['id']}", use_container_width=True)
                    st.divider()
        elif not aniv_proximos.empty:
            with st.expander("Próximos Aniversários", expanded=False):
                for idx, cliente in aniv_proximos.head(5).iterrows():
                    dias = aniversarios.dias_ate_aniversario(cliente['data_nascimento'])
                    st.caption(f"🎂 **{cliente['nome']}** - Em {dias} dias")
    
    # --- NOVO: Alertas de E-mail (Intimações) ---
    try:
        alertas_df = db.sql_get_query("""
            SELECT * FROM alertas_email 
            WHERE processado = 0 
            ORDER BY criado_em DESC
            LIMIT 10
        """)
        
        if not alertas_df.empty:
            st.markdown("### 📧 Alertas de E-mail (Intimações)")
            
            # Card de alerta
            st.error(f"**{len(alertas_df)} alerta(s) pendente(s) de processamento!**")
            
            with st.expander("Ver Alertas Pendentes", expanded=True):
                for idx, alerta in alertas_df.iterrows():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        tipo_icon = {
                            'alvará': '💰',
                            'mandado_pagamento': '💵',
                            'rpv': '📋',
                            'precatório': '📑',
                            'depósito': '🏦',
                            'intimação': '⚖️',
                            'citação': '📨'
                        }.get(alerta['tipo'], '📧')
                        
                        st.write(f"{tipo_icon} **{alerta['tipo'].upper()}**")
                        st.caption(f"📬 {alerta['remetente'][:40]}...")
                        st.caption(f"📄 {alerta['assunto'][:60]}...")
                        
                        if alerta['numero_processo']:
                            st.caption(f"🔢 Processo: {alerta['numero_processo']}")
                        if alerta['valor_detectado']:
                            st.caption(f"💲 Valor: R$ {alerta['valor_detectado']:,.2f}")
                    
                    with col2:
                        data_str = alerta['criado_em'][:10] if alerta['criado_em'] else '---'
                        st.caption(f"📅 {data_str}")
                    
                    with col3:
                        if st.button("✅ Processar", key=f"proc_alerta_{alerta['id']}"):
                            db.crud_update(
                                "alertas_email",
                                {"processado": 1},
                                "id = ?", [alerta['id']],
                                f"Alerta {alerta['id']} marcado como processado"
                            )
                            st.rerun()
                    
                    st.divider()
    except Exception as e:
        # Silencioso se tabela não existir ainda
        pass
    
    # --- NOVO: Gráficos Dinâmicos ---
    st.markdown("### 📈 Análises Visuais")
    
    tab_graf1, tab_graf2, tab_graf3 = st.tabs(["📊 Processos por Fase", "💰 Fluxo de Caixa", "👥 Clientes por Mês"])
    
    with tab_graf1:
        try:
            proc_df = db.sql_get('processos')
            if not proc_df.empty and 'fase' in proc_df.columns:
                fase_counts = proc_df['fase'].value_counts().reset_index()
                fase_counts.columns = ['Fase', 'Quantidade']
                
                fig_pizza = px.pie(
                    fase_counts, 
                    values='Quantidade', 
                    names='Fase',
                    title='Distribuição de Processos por Fase',
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4  # Donut chart
                )
                fig_pizza.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.info("Nenhum processo cadastrado para gerar o gráfico.")
        except Exception as e:
            st.warning(f"Erro ao gerar gráfico de processos: {e}")
    
    with tab_graf2:
        try:
            fin_df = db.sql_get('financeiro')
            if not fin_df.empty and 'data_vencimento' in fin_df.columns:
                # Converter data e filtrar últimos 6 meses
                fin_df['data_vencimento'] = pd.to_datetime(fin_df['data_vencimento'], errors='coerce')
                fin_df = fin_df.dropna(subset=['data_vencimento'])
                
                data_limite = datetime.now() - timedelta(days=180)
                fin_df = fin_df[fin_df['data_vencimento'] >= data_limite]
                
                if not fin_df.empty:
                    # Agrupar por mês
                    fin_df['mes'] = fin_df['data_vencimento'].dt.to_period('M').astype(str)
                    
                    # Separar receitas e despesas
                    receitas = fin_df[fin_df['tipo'] == 'receita'].groupby('mes')['valor'].sum().reset_index()
                    receitas.columns = ['Mês', 'Receitas']
                    
                    despesas = fin_df[fin_df['tipo'] == 'despesa'].groupby('mes')['valor'].sum().reset_index()
                    despesas.columns = ['Mês', 'Despesas']
                    
                    # Merge
                    fluxo = pd.merge(receitas, despesas, on='Mês', how='outer').fillna(0)
                    fluxo = fluxo.sort_values('Mês')
                    
                    fig_fluxo = go.Figure()
                    fig_fluxo.add_trace(go.Scatter(
                        x=fluxo['Mês'], y=fluxo['Receitas'],
                        name='Receitas', mode='lines+markers',
                        line=dict(color='#28a745', width=3),
                        fill='tozeroy', fillcolor='rgba(40, 167, 69, 0.2)'
                    ))
                    fig_fluxo.add_trace(go.Scatter(
                        x=fluxo['Mês'], y=fluxo['Despesas'],
                        name='Despesas', mode='lines+markers',
                        line=dict(color='#dc3545', width=3),
                        fill='tozeroy', fillcolor='rgba(220, 53, 69, 0.2)'
                    ))
                    fig_fluxo.update_layout(
                        title='Fluxo de Caixa - Últimos 6 Meses',
                        xaxis_title='Mês',
                        yaxis_title='Valor (R$)',
                        height=350,
                        margin=dict(l=20, r=20, t=40, b=20),
                        legend=dict(orientation='h', yanchor='bottom', y=1.02)
                    )
                    st.plotly_chart(fig_fluxo, use_container_width=True)
                else:
                    st.info("Nenhum dado financeiro nos últimos 6 meses.")
            else:
                st.info("Nenhum lançamento financeiro para gerar o gráfico.")
        except Exception as e:
            st.warning(f"Erro ao gerar gráfico financeiro: {e}")
    
    with tab_graf3:
        try:
            cli_df = db.sql_get('clientes')
            if not cli_df.empty and 'data_cadastro' in cli_df.columns:
                cli_df['data_cadastro'] = pd.to_datetime(cli_df['data_cadastro'], errors='coerce')
                cli_df = cli_df.dropna(subset=['data_cadastro'])
                
                if not cli_df.empty:
                    # Últimos 6 meses
                    data_limite = datetime.now() - timedelta(days=180)
                    cli_df = cli_df[cli_df['data_cadastro'] >= data_limite]
                    
                    if not cli_df.empty:
                        cli_df['mes'] = cli_df['data_cadastro'].dt.to_period('M').astype(str)
                        cli_mensal = cli_df.groupby('mes').size().reset_index()
                        cli_mensal.columns = ['Mês', 'Novos Clientes']
                        cli_mensal = cli_mensal.sort_values('Mês')
                        
                        fig_cli = px.bar(
                            cli_mensal,
                            x='Mês',
                            y='Novos Clientes',
                            title='Novos Clientes por Mês',
                            color='Novos Clientes',
                            color_continuous_scale='Blues'
                        )
                        fig_cli.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_cli, use_container_width=True)
                    else:
                        st.info("Nenhum cliente cadastrado nos últimos 6 meses.")
                else:
                    st.info("Dados de cadastro não disponíveis.")
            else:
                st.info("Nenhum cliente cadastrado para gerar o gráfico.")
        except Exception as e:
            st.warning(f"Erro ao gerar gráfico de clientes: {e}")
        
    # --- 3. Links Úteis ---
    st.markdown("### 🔗 Links Úteis")
    
    links = [
        {"nome": "PJe Comunica", "url": "https://comunica.pje.jus.br/"},
        {"nome": "PJe TJRJ (1º Grau)", "url": "https://tjrj.pje.jus.br/1g/login.seam"},
        {"nome": "Portal TJRJ", "url": "http://www.tjrj.jus.br/"},
        {"nome": "PJe TRT1", "url": "https://pje.trt1.jus.br/primeirograu/login.seam"},
    ]
    
    cols_links = st.columns(len(links))
    for i, link in enumerate(links):
        with cols_links[i]:
            st.link_button(link['nome'], link['url'], use_container_width=True)

    st.divider()
    
    # --- 4. Quadro de Avisos ---
    st.markdown("### 🔔 Quadro de Avisos")
    
    # Recuperar aviso salvo (usando tabela config se possível, ou session state)
    aviso_atual = db.get_config('aviso_mural') or ""
    
    with st.container():
        st.info(f"📌 **Aviso da Equipe:**\n\n{aviso_atual}" if aviso_atual else "Nenhum aviso no momento.")
        
        with st.expander("✏️ Editar Aviso"):
            novo_aviso = st.text_area("Novo aviso:", value=aviso_atual)
            col_save, col_del = st.columns([1, 1])
            with col_save:
                if st.button("Postar Aviso"):
                    db.set_config('aviso_mural', novo_aviso)
                    st.success("Aviso atualizado!")
                    st.rerun()
            with col_del:
                if st.button("🗑️ Excluir Aviso", type="secondary"):
                    db.set_config('aviso_mural', "")
                    st.success("Aviso removido!")
                    st.rerun()

    st.divider()
    
    # --- 5. Manutenção (Mantido do original mas compactado) ---
    with st.expander("🛠️ Opções de Manutenção e Backup"):
        col_bkp, col_info = st.columns([1, 2])
        with col_bkp:
            if os.path.exists("dados_escritorio.db") and os.path.getsize("dados_escritorio.db") > 0:
                with open("dados_escritorio.db", "rb") as fp:
                    st.download_button(
                        "💾 Baixar Backup (DB)", 
                        fp, 
                        f"backup_sistema_{datetime.now().strftime('%Y%m%d')}.db", 
                        type="primary",
                        on_click=registrar_backup
                    )
            else:
                st.error("Banco de dados não encontrado ou vazio.")
        with col_info:
            st.write("**Histórico de Backups:**")
            if last_backup_str:
                try:
                    dt = datetime.fromisoformat(last_backup_str).strftime('%d/%m/%Y às %H:%M')
                    user = db.get_config('last_backup_user', 'Usuário Desconhecido')
                    st.info(f"✅ Último backup realizado em **{dt}** por **{user}**")
                except:
                    st.caption("Data de backup inválida.")
            else:
                st.warning("⚠️ Nenhum backup registrado recentemente.")
            
            st.caption("O backup é salvo automaticamente ao clicar no botão de download. Guarde o arquivo em local seguro (nuvem ou HD externo).")
