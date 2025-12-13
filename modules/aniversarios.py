import streamlit as st
import database as db
import utils as ut
from datetime import datetime, date
import pandas as pd
import utils_email
import email_templates
import urllib.parse
import io

def render():
    st.markdown("<h1 style='color: var(--text-main);'>🎂 Aniversários</h1>", unsafe_allow_html=True)
    
    # Garantir que a tabela de configuração existe
    _criar_tabela_config()
    
    # === MÉTRICAS VISUAIS ===
    col1, col2, col3 = st.columns(3)
    
    aniv_hoje = get_aniversariantes_hoje()
    aniv_semana = get_aniversariantes_semana()
    aniv_mes = get_aniversariantes_mes()
    
    with col1:
        st.metric("🎂 Hoje", len(aniv_hoje) if not aniv_hoje.empty else 0, 
                  delta="🎉" if not aniv_hoje.empty else None)
    with col2:
        st.metric("📆 Esta Semana", len(aniv_semana) if not aniv_semana.empty else 0)
    with col3:
        st.metric("📅 Este Mês", len(aniv_mes) if not aniv_mes.empty else 0)
    
    st.divider()
    
    # Tabs
    t1, t2, t3, t4 = st.tabs(["🎉 Hoje e Próximos", "📅 Calendário Mensal", "📜 Histórico Envios", "⚙️ Configurações"])
    
    with t1:
        render_aniversariantes()
    
    with t2:
        render_calendario_mes()
    
    with t3:
        render_historico()
    
    with t4:
        render_configuracoes()

def _criar_tabela_config():
    """Cria tabela de configuração se não existir"""
    try:
        db.sql_run("""
            CREATE TABLE IF NOT EXISTS config_aniversarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dias_antecedencia INTEGER DEFAULT 7,
                template_mensagem TEXT,
                ativo INTEGER DEFAULT 1
            )
        """)
        
        # Tabela de histórico de mensagens enviadas
        db.sql_run("""
            CREATE TABLE IF NOT EXISTS historico_aniversarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente INTEGER NOT NULL,
                nome_cliente TEXT,
                data_envio TEXT NOT NULL,
                tipo_envio TEXT DEFAULT 'whatsapp',
                ano_referencia INTEGER,
                sucesso INTEGER DEFAULT 1,
                observacao TEXT
            )
        """)
    except:
        pass

def _registrar_envio(id_cliente, nome_cliente, tipo_envio='whatsapp', sucesso=True, observacao=''):
    """Registra envio de mensagem de aniversário"""
    try:
        ano_atual = date.today().year
        db.sql_run("""
            INSERT INTO historico_aniversarios (id_cliente, nome_cliente, data_envio, tipo_envio, ano_referencia, sucesso, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (id_cliente, nome_cliente, datetime.now().isoformat(), tipo_envio, ano_atual, int(sucesso), observacao))
        return True
    except:
        return False

def _verificar_ja_enviado(id_cliente):
    """Verifica se já foi enviada mensagem este ano para este cliente"""
    try:
        ano_atual = date.today().year
        resultado = db.sql_get_query(f"""
            SELECT COUNT(*) as total FROM historico_aniversarios 
            WHERE id_cliente = {id_cliente} AND ano_referencia = {ano_atual} AND sucesso = 1
        """)
        if not resultado.empty:
            return resultado.iloc[0]['total'] > 0
    except:
        pass
    return False

def _get_historico():
    """Retorna histórico de mensagens enviadas"""
    try:
        return db.sql_get_query("""
            SELECT * FROM historico_aniversarios 
            ORDER BY data_envio DESC 
            LIMIT 100
        """)
    except:
        return pd.DataFrame()

def render_aniversariantes():
    """Mostra aniversariantes do dia e próximos dias"""
    
    # Aniversariantes de HOJE
    st.markdown("### 🎉 Aniversariantes de Hoje")
    
    aniv_hoje = get_aniversariantes_hoje()
    
    if not aniv_hoje.empty:
        st.success(f"🎊 Hoje temos **{len(aniv_hoje)}** aniversariante(s)!")
        
        # === BOTÃO ENVIAR PARA TODOS ===
        col_massa1, col_massa2 = st.columns([2, 1])
        with col_massa1:
            if st.button("📱 Enviar WhatsApp para TODOS", type="primary", use_container_width=True):
                template = get_template_mensagem()
                links = []
                for _, cliente in aniv_hoje.iterrows():
                    if cliente['telefone']:
                        idade = calcular_idade(cliente['data_nascimento'])
                        mensagem = formatar_mensagem_aniversario(cliente['nome'], idade, template)
                        link = gerar_link_whatsapp(cliente['telefone'], mensagem)
                        if link:
                            links.append((cliente['nome'], link))
                
                if links:
                    st.info(f"Abrindo {len(links)} janela(s) do WhatsApp...")
                    for nome, link in links:
                        st.markdown(f"- [{nome}]({link})")
        
        with col_massa2:
            # Exportar aniversariantes de hoje
            if st.button("📊 Exportar Excel", use_container_width=True):
                output = io.BytesIO()
                aniv_hoje.to_excel(output, index=False, engine='openpyxl')
                st.download_button(
                    "⬇️ Download",
                    data=output.getvalue(),
                    file_name=f"aniversariantes_hoje_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        st.divider()
        
        for idx, cliente in aniv_hoje.iterrows():
            ja_enviado = _verificar_ja_enviado(cliente['id'])
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                
                idade = calcular_idade(cliente['data_nascimento']) if cliente['data_nascimento'] else None
                idade_texto = f"{idade} anos" if idade else "Idade não disponível"
                
                # Indicador de já enviado
                status_envio = " ✅ Já parabenizado(a)!" if ja_enviado else ""
                c1.markdown(f"### 🎂 {cliente['nome']}{status_envio}")
                c1.caption(f"**{idade_texto}** • {ut.formatar_celular(cliente['telefone']) if cliente['telefone'] else 'Sem telefone'}")
                
                # Botão WhatsApp + Registrar
                if cliente['telefone']:
                    template = get_template_mensagem()
                    mensagem = formatar_mensagem_aniversario(cliente['nome'], idade, template)
                    link_whatsapp = gerar_link_whatsapp(cliente['telefone'], mensagem)
                    
                    if link_whatsapp:
                        # Usar link_button mas também oferecer botão de registro
                        c2.link_button(
                            "📱 WhatsApp",
                            link_whatsapp,
                            use_container_width=True,
                            type="primary" if not ja_enviado else "secondary"
                        )
                        # Botão para registrar envio após clicar no WhatsApp
                        if not ja_enviado:
                            if c2.button("✓ Registrar", key=f"reg_wpp_{cliente['id']}", help="Clique após enviar pelo WhatsApp"):
                                _registrar_envio(cliente['id'], cliente['nome'], 'whatsapp', True)
                                st.success(f"✅ Envio registrado para {cliente['nome']}!")
                                st.rerun()
                    else:
                        c2.warning("Tel. inválido")
                else:
                    c2.warning("Sem telefone")
                
                # Botão E-mail com registro automático
                if cliente.get('email'):
                    if c3.button("📧 E-mail", key=f"email_hoje_{cliente['id']}", use_container_width=True, disabled=ja_enviado):
                        corpo_email = email_templates.template_aniversario(cliente['nome'], idade)
                        sucesso, erro = utils_email.enviar_email(
                            cliente['email'],
                            "🎂 Feliz Aniversário! - Lopes & Ribeiro",
                            corpo_email
                        )
                        if sucesso:
                            # Registrar envio no histórico
                            _registrar_envio(cliente['id'], cliente['nome'], 'email', True)
                            st.success(f"✅ E-mail de parabéns enviado para {cliente['nome']}!")
                            st.rerun()
                        else:
                            _registrar_envio(cliente['id'], cliente['nome'], 'email', False, erro)
                            st.error(f"❌ Falha ao enviar: {erro}")
                else:
                    c3.caption("Sem e-mail")
                
                # Botão Ficha do Cliente - Navega usando session_state
                if c4.button("📋 Ficha", key=f"ficha_hoje_{cliente['id']}", use_container_width=True, help="Navegar para ficha do cliente"):
                    st.session_state['navegar_cliente_id'] = cliente['id']
                    st.session_state['menu_selected'] = 'Clientes (CRM)'
                    st.info(f"👉 Clique em 'Clientes (CRM)' no menu para ver {cliente['nome']}")
    else:
        st.info("Nenhum aniversariante hoje.")
    
    st.divider()
    
    # Próximos Aniversariantes - USAR DIAS DA CONFIG
    config = _get_config()
    dias_antecedencia = config.get('dias_antecedencia', 7) if config else 7
    
    st.markdown(f"### 📆 Próximos Aniversariantes ({dias_antecedencia} dias)")
    
    aniv_proximos = get_aniversariantes_periodo(dias_antecedencia)
    
    if not aniv_proximos.empty:
        for idx, cliente in aniv_proximos.iterrows():
            dias_restantes = dias_ate_aniversario(cliente['data_nascimento'])
            
            if dias_restantes == 0:
                continue  # Já mostrado em "Hoje"
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                
                idade_futura = calcular_idade(cliente['data_nascimento'], proximo_aniversario=True) if cliente['data_nascimento'] else None
                idade_texto = f"Fará {idade_futura} anos" if idade_futura else ""
                
                c1.markdown(f"**{cliente['nome']}**")
                c1.caption(f"{idade_texto}")
                
                c2.metric("Em", f"{dias_restantes} dias")
                
                # Botão WhatsApp
                if cliente['telefone']:
                    template = get_template_mensagem()
                    mensagem = formatar_mensagem_aniversario(cliente['nome'], idade_futura, template)
                    link_whatsapp = gerar_link_whatsapp(cliente['telefone'], mensagem)
                    
                    if link_whatsapp:
                        c3.link_button(
                            "📱 Enviar",
                            link_whatsapp,
                            use_container_width=True
                        )
                    else:
                        c3.caption("Tel. inválido")
                else:
                    c3.caption("Sem telefone")
                
                # Botão Ficha
                if c4.button("📋", key=f"ficha_prox_{cliente['id']}", use_container_width=True, help="Navegar para ficha do cliente"):
                    st.session_state['navegar_cliente_id'] = cliente['id']
                    st.session_state['menu_selected'] = 'Clientes (CRM)'
                    st.info(f"👉 Clique em 'Clientes (CRM)' no menu para ver {cliente['nome']}")
    else:
        st.info(f"Nenhum aniversariante nos próximos {dias_antecedencia} dias.")

def _get_config():
    """Retorna configuração atual"""
    try:
        config = db.sql_get_query("SELECT * FROM config_aniversarios LIMIT 1")
        if not config.empty:
            return config.iloc[0].to_dict()
    except:
        pass
    return None


def render_historico():
    """Exibe histórico de mensagens de aniversário enviadas"""
    st.markdown("### 📜 Histórico de Mensagens Enviadas")
    
    historico = _get_historico()
    
    if not historico.empty:
        # Métricas resumo
        col1, col2, col3 = st.columns(3)
        
        ano_atual = date.today().year
        envios_ano = len(historico[historico['ano_referencia'] == ano_atual]) if 'ano_referencia' in historico.columns else 0
        envios_whatsapp = len(historico[historico['tipo_envio'] == 'whatsapp']) if 'tipo_envio' in historico.columns else 0
        envios_email = len(historico[historico['tipo_envio'] == 'email']) if 'tipo_envio' in historico.columns else 0
        
        col1.metric("📅 Este Ano", envios_ano)
        col2.metric("📱 Via WhatsApp", envios_whatsapp)
        col3.metric("📧 Via E-mail", envios_email)
        
        st.divider()
        
        # Filtros
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            filtro_ano = st.selectbox("Ano", sorted(historico['ano_referencia'].dropna().unique(), reverse=True) if 'ano_referencia' in historico.columns else [ano_atual])
        with col_filtro2:
            filtro_tipo = st.selectbox("Tipo de Envio", ["Todos", "whatsapp", "email"])
        
        # Aplicar filtros
        historico_filtrado = historico.copy()
        if 'ano_referencia' in historico_filtrado.columns:
            historico_filtrado = historico_filtrado[historico_filtrado['ano_referencia'] == filtro_ano]
        if filtro_tipo != "Todos" and 'tipo_envio' in historico_filtrado.columns:
            historico_filtrado = historico_filtrado[historico_filtrado['tipo_envio'] == filtro_tipo]
        
        # Exibir tabela
        if not historico_filtrado.empty:
            st.info(f"📊 Total: {len(historico_filtrado)} mensagem(ns) registrada(s)")
            
            # Formatar para exibição
            colunas_exibir = ['nome_cliente', 'data_envio', 'tipo_envio', 'sucesso']
            colunas_existentes = [c for c in colunas_exibir if c in historico_filtrado.columns]
            
            if colunas_existentes:
                df_exibir = historico_filtrado[colunas_existentes].copy()
                df_exibir.columns = ['Cliente', 'Data/Hora Envio', 'Tipo', 'Sucesso'][:len(colunas_existentes)]
                st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            
            # Botão exportar
            if st.button("📊 Exportar Histórico"):
                output = io.BytesIO()
                historico_filtrado.to_excel(output, index=False, engine='openpyxl')
                st.download_button(
                    "⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name=f"historico_aniversarios_{filtro_ano}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Nenhum registro encontrado com os filtros selecionados.")
    else:
        st.info("📭 Nenhuma mensagem de aniversário registrada ainda.")
        st.caption("Os envios serão registrados automaticamente ao clicar nos botões de WhatsApp ou E-mail.")


def render_calendario_mes():
    """Mostra todos os aniversariantes do mês selecionado"""
    
    # === SELETOR DE MÊS ===
    col1, col2, col3 = st.columns([2, 2, 1])
    
    meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    with col1:
        mes_atual = date.today().month
        mes_selecionado = st.selectbox(
            "Selecione o mês",
            range(1, 13),
            index=mes_atual - 1,
            format_func=lambda x: meses_nomes[x-1]
        )
    
    with col2:
        ano_atual = date.today().year
        ano_selecionado = st.number_input("Ano", min_value=2020, max_value=2030, value=ano_atual)
    
    # Buscar aniversariantes do mês selecionado
    aniv_mes = get_aniversariantes_mes_especifico(mes_selecionado)
    
    with col3:
        # Exportar aniversariantes do mês
        if st.button("📊 Excel", use_container_width=True, help="Exportar lista"):
            if not aniv_mes.empty:
                output = io.BytesIO()
                aniv_mes.to_excel(output, index=False, engine='openpyxl')
                st.download_button(
                    "⬇️ Download",
                    data=output.getvalue(),
                    file_name=f"aniversariantes_{meses_nomes[mes_selecionado-1]}_{ano_selecionado}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Nenhum aniversariante para exportar")
    
    st.divider()
    
    if not aniv_mes.empty:
        st.success(f"📊 Total de **{len(aniv_mes)}** aniversariante(s) em {meses_nomes[mes_selecionado-1]}")
        
        # Agrupar por dia do mês
        aniv_mes['dia_mes'] = pd.to_datetime(aniv_mes['data_nascimento']).dt.day
        aniv_mes = aniv_mes.sort_values('dia_mes')
        
        for dia, grupo in aniv_mes.groupby('dia_mes'):
            st.markdown(f"#### 📅 Dia {int(dia)}")
            
            for idx, cliente in grupo.iterrows():
                idade = calcular_idade(cliente['data_nascimento'], proximo_aniversario=True)
                
                c1, c2 = st.columns([3, 1])
                tel_formatado = ut.formatar_celular(cliente['telefone']) if cliente.get('telefone') else "Sem telefone"
                c1.write(f"🎂 **{cliente['nome']}** ({idade} anos) • {tel_formatado}")
                
                if cliente.get('telefone'):
                    template = get_template_mensagem()
                    mensagem = formatar_mensagem_aniversario(cliente['nome'], idade, template)
                    link_whatsapp = gerar_link_whatsapp(cliente['telefone'], mensagem)
                    if link_whatsapp:
                        c2.link_button("📱 WhatsApp", link_whatsapp, key=f"wpp_mes_{cliente['id']}")
                
            st.divider()
    else:
        st.info(f"Nenhum aniversariante em {meses_nomes[mes_selecionado-1]}.")

def render_configuracoes():
    """Configurações de alertas e mensagens"""
    
    st.markdown("### ⚙️ Configurações de Alertas")
    
    # Buscar configuração atual
    config = db.sql_get_query("SELECT * FROM config_aniversarios LIMIT 1")
    
    if config.empty:
        # Criar configuração padrão
        db.sql_run("""
            INSERT INTO config_aniversarios (dias_antecedencia, template_mensagem, ativo) 
            VALUES (7, 'Olá {nome}! 🎉🎂

Feliz Aniversário! Desejamos muita saúde, paz e prosperidade neste novo ciclo de vida!

Um abraço da equipe!', 1)
        """)
        config = db.sql_get_query("SELECT * FROM config_aniversarios LIMIT 1")
    
    config_row = config.iloc[0]
    
    with st.form("config_aniversarios"):
        st.markdown("#### 📆 Antecedência de Alertas")
        dias = st.number_input(
            "Dias de antecedência para alerta",
            min_value=1,
            max_value=30,
            value=int(config_row['dias_antecedencia']),
            help="Quantos dias antes do aniversário você quer ser alertado"
        )
        
        st.markdown("#### 💬 Template de Mensagem WhatsApp")
        st.caption("Use **{nome}** e **{idade}** como placeholders que serão substituídos automaticamente")
        
        template = st.text_area(
            "Mensagem Padrão",
            value=config_row['template_mensagem'],
            height=150,
            help="Mensagem que será pré-preenchida no WhatsApp"
        )
        
        ativo = st.checkbox("Ativar alertas de aniversário", value=bool(config_row['ativo']))
        
        if st.form_submit_button("💾 Salvar Configurações", type="primary"):
            db.sql_run(
                "UPDATE config_aniversarios SET dias_antecedencia=?, template_mensagem=?, ativo=? WHERE id=?",
                (dias, template, int(ativo), config_row['id'])
            )
            st.success("Configurações salvas com sucesso!")
            st.rerun()
    
    # Preview da mensagem
    st.markdown("---")
    st.markdown("#### 👁️ Preview da Mensagem")
    nome_exemplo = "João Silva"
    idade_exemplo = 35
    preview = formatar_mensagem_aniversario(nome_exemplo, idade_exemplo, template)
    st.code(preview, language=None)

# ============== FUNÇÕES AUXILIARES ==============

def get_aniversariantes_hoje():
    """Retorna DataFrame com clientes que fazem aniversário hoje"""
    query = """
        SELECT * FROM clientes 
        WHERE data_nascimento IS NOT NULL
        AND strftime('%m-%d', data_nascimento) = strftime('%m-%d', 'now')
        AND status_cliente != 'INATIVO'
        ORDER BY nome
    """
    return db.sql_get_query(query)

def get_aniversariantes_semana():
    """Retorna DataFrame com aniversariantes dos próximos 7 dias"""
    hoje = date.today()
    aniversariantes = []
    
    # Buscar todos os clientes com data de nascimento
    clientes = db.sql_get_query("""
        SELECT * FROM clientes 
        WHERE data_nascimento IS NOT NULL
        AND status_cliente != 'INATIVO'
    """)
    
    if clientes.empty:
        return pd.DataFrame()
    
    for idx, cliente in clientes.iterrows():
        dias = dias_ate_aniversario(cliente['data_nascimento'])
        if 0 < dias <= 7:  # Próximos 7 dias (excluindo hoje)
            aniversariantes.append(cliente)
    
    if aniversariantes:
        return pd.DataFrame(aniversariantes)
    return pd.DataFrame()

def get_aniversariantes_mes():
    """Retorna DataFrame com todos os aniversariantes do mês atual"""
    query = """
        SELECT * FROM clientes 
        WHERE data_nascimento IS NOT NULL
        AND strftime('%m', data_nascimento) = strftime('%m', 'now')
        AND status_cliente != 'INATIVO'
        ORDER BY strftime('%d', data_nascimento)
    """
    return db.sql_get_query(query)

def get_aniversariantes_mes_especifico(mes):
    """Retorna DataFrame com todos os aniversariantes de um mês específico"""
    query = f"""
        SELECT * FROM clientes 
        WHERE data_nascimento IS NOT NULL
        AND CAST(strftime('%m', data_nascimento) AS INTEGER) = {mes}
        AND status_cliente != 'INATIVO'
        ORDER BY strftime('%d', data_nascimento)
    """
    return db.sql_get_query(query)

def get_aniversariantes_periodo(dias):
    """Retorna DataFrame com aniversariantes dos próximos N dias"""
    hoje = date.today()
    aniversariantes = []
    
    # Buscar todos os clientes com data de nascimento
    clientes = db.sql_get_query("""
        SELECT * FROM clientes 
        WHERE data_nascimento IS NOT NULL
        AND status_cliente != 'INATIVO'
    """)
    
    if clientes.empty:
        return pd.DataFrame()
    
    for idx, cliente in clientes.iterrows():
        dias_restantes = dias_ate_aniversario(cliente['data_nascimento'])
        if dias_restantes is not None and 0 < dias_restantes <= dias:
            aniversariantes.append(cliente)
    
    if aniversariantes:
        return pd.DataFrame(aniversariantes)
    return pd.DataFrame()

def gerar_link_whatsapp(telefone, mensagem):
    """Gera link do WhatsApp Web com mensagem pré-formatada"""
    if not telefone:
        return None
    
    # Limpar telefone (apenas números)
    telefone_limpo = ut.limpar_numeros(telefone)
    
    # Adicionar código do país se não tiver (Brasil = 55)
    if not telefone_limpo.startswith('55'):
        telefone_limpo = '55' + telefone_limpo
    
    # Codificar mensagem para URL
    mensagem_encoded = urllib.parse.quote(mensagem)
    
    # Gerar link
    link = f"https://wa.me/{telefone_limpo}?text={mensagem_encoded}"
    
    return link

def get_template_mensagem():
    """Retorna o template de mensagem configurado"""
    config = db.sql_get_query("SELECT template_mensagem FROM config_aniversarios LIMIT 1")
    
    if not config.empty:
        return config.iloc[0]['template_mensagem']
    
    # Template padrão caso não haja configuração
    return """Olá {nome}! 🎉🎂

Feliz Aniversário! Desejamos muita saúde, paz e prosperidade neste novo ciclo de vida!

Um abraço da equipe!"""

def formatar_mensagem_aniversario(nome, idade, template):
    """Substitui placeholders no template"""
    mensagem = template.replace('{nome}', nome)
    
    if idade:
        mensagem = mensagem.replace('{idade}', str(idade))
    else:
        mensagem = mensagem.replace('{idade}', '')
    
    return mensagem

def calcular_idade(data_nascimento_str, proximo_aniversario=False):
    """Calcula a idade a partir da data de nascimento"""
    if not data_nascimento_str:
        return None
    
    try:
        data_nasc = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
        hoje = date.today()
        
        idade = hoje.year - data_nasc.year
        
        # Ajustar se ainda não fez aniversário este ano
        if (hoje.month, hoje.day) < (data_nasc.month, data_nasc.day):
            idade -= 1
        
        # Se for para calcular idade no próximo aniversário
        if proximo_aniversario:
            if (hoje.month, hoje.day) < (data_nasc.month, data_nasc.day):
                # Ainda não fez aniversário este ano
                return idade + 1
            else:
                # Já fez aniversário este ano, então próximo é ano que vem
                return idade + 1
        
        return idade
    except:
        return None

def dias_ate_aniversario(data_nascimento_str):
    """Calcula quantos dias faltam para o próximo aniversário"""
    if not data_nascimento_str:
        return None
    
    try:
        data_nasc = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
        hoje = date.today()
        
        # Próximo aniversário neste ano
        try:
            proximo_aniversario = date(hoje.year, data_nasc.month, data_nasc.day)
        except ValueError:
             # Se nascido em 29/02 e estamos em ano não bissexto, antecipar para 28/02
             proximo_aniversario = date(hoje.year, 2, 28)
        
        # Se já passou este ano, calcular para o próximo ano
        if proximo_aniversario < hoje:
            try:
                proximo_aniversario = date(hoje.year + 1, data_nasc.month, data_nasc.day)
            except ValueError:
                 proximo_aniversario = date(hoje.year + 1, 2, 28)
        
        delta = proximo_aniversario - hoje
        return delta.days
    except:
        return None

def verificar_aniversario_hoje(data_nascimento_str):
    """Verifica se a data de nascimento é hoje"""
    if not data_nascimento_str:
        return False
    
    try:
        data_nasc = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
        hoje = date.today()
        
        return (data_nasc.month == hoje.month) and (data_nasc.day == hoje.day)
    except:
        return False
