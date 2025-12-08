import streamlit as st
import database as db
import utils as ut
from datetime import datetime, date
import pandas as pd

def render():
    st.markdown("<h1 style='color: var(--text-main);'>🎂 Aniversários</h1>", unsafe_allow_html=True)
    
    # Tabs
    t1, t2, t3 = st.tabs(["🎉 Hoje e Próximos", "📅 Calendário Mensal", "⚙️ Configurações"])
    
    with t1:
        render_aniversariantes()
    
    with t2:
        render_calendario_mes()
    
    with t3:
        render_configuracoes()

def render_aniversariantes():
    """Mostra aniversariantes do dia e próximos dias"""
    
    # Aniversariantes de HOJE
    st.markdown("### 🎉 Aniversariantes de Hoje")
    
    aniv_hoje = get_aniversariantes_hoje()
    
    if not aniv_hoje.empty:
        st.success(f"🎊 Hoje temos **{len(aniv_hoje)}** aniversariante(s)!")
        
        for idx, cliente in aniv_hoje.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                
                idade = calcular_idade(cliente['data_nascimento']) if cliente['data_nascimento'] else None
                idade_texto = f"{idade} anos" if idade else "Idade não disponível"
                
                c1.markdown(f"### 🎂 {cliente['nome']}")
                c1.caption(f"**{idade_texto}** • {ut.formatar_celular(cliente['telefone'])}")
                
                # Botão WhatsApp
                if cliente['telefone']:
                    template = get_template_mensagem()
                    mensagem = formatar_mensagem_aniversario(cliente['nome'], idade, template)
                    link_whatsapp = gerar_link_whatsapp(cliente['telefone'], mensagem)
                    
                    c2.link_button(
                        "📱 WhatsApp",
                        link_whatsapp,
                        use_container_width=True,
                        type="primary"
                    )
                else:
                    c2.warning("Sem telefone")
                
                # Botão Ficha do Cliente
                if c3.button("📋 Ficha", key=f"ficha_hoje_{cliente['id']}", use_container_width=True, help="Visualizar no módulo Clientes"):
                    st.info("👉 Acesse 'Clientes (CRM)' no menu lateral para ver a ficha completa")
    else:
        st.info("Nenhum aniversariante hoje.")
    
    st.divider()
    
    # Próximos Aniversariantes
    st.markdown("### 📆 Próximos Aniversariantes (7 dias)")
    
    aniv_proximos = get_aniversariantes_semana()
    
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
                    
                    c3.link_button(
                        "📱 Enviar",
                        link_whatsapp,
                        use_container_width=True
                    )
                else:
                    c3.caption("Sem telefone")
                
                # Botão Ficha
                if c4.button("📋", key=f"ficha_prox_{cliente['id']}", use_container_width=True, help="Visualizar no módulo Clientes"):
                    st.info("👉 Acesse 'Clientes (CRM)' no menu lateral para ver a ficha completa")
    else:
        st.info("Nenhum aniversariante nos próximos 7 dias.")

def render_calendario_mes():
    """Mostra todos os aniversariantes do mês atual"""
    
    aniv_mes = get_aniversariantes_mes()
    
    if not aniv_mes.empty:
        st.success(f"📊 Total de **{len(aniv_mes)}** aniversariante(s) neste mês")
        
        # Agrupar por dia do mês
        aniv_mes['dia_mes'] = pd.to_datetime(aniv_mes['data_nascimento']).dt.day
        aniv_mes = aniv_mes.sort_values('dia_mes')
        
        for dia, grupo in aniv_mes.groupby('dia_mes'):
            st.markdown(f"#### 📅 Dia {int(dia)}")
            
            for idx, cliente in grupo.iterrows():
                idade = calcular_idade(cliente['data_nascimento'], proximo_aniversario=True)
                
                c1, c2 = st.columns([3, 1])
                c1.write(f"🎂 **{cliente['nome']}** ({idade} anos) • {ut.formatar_celular(cliente['telefone'])}")
                
                if cliente['telefone']:
                    template = get_template_mensagem()
                    mensagem = formatar_mensagem_aniversario(cliente['nome'], idade, template)
                    link_whatsapp = gerar_link_whatsapp(cliente['telefone'], mensagem)
                    c2.link_button("📱 WhatsApp", link_whatsapp, key=f"wpp_mes_{cliente['id']}")
                
            st.divider()
    else:
        st.info("Nenhum aniversariante neste mês.")

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

def gerar_link_whatsapp(telefone, mensagem):
    """Gera link do WhatsApp Web com mensagem pré-formatada"""
    import urllib.parse
    
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
