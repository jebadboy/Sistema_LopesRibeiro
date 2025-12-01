import streamlit as st

def render():
    """Módulo de Ajuda e Documentação do Sistema"""
    
    st.markdown("<h1 style='color: var(--text-main);'>📚 Central de Ajuda</h1>", unsafe_allow_html=True)
    st.markdown("Encontre orientações, guias e respostas para suas dúvidas sobre o sistema.")
    
    # Busca
    col1, col2 = st.columns([3, 1])
    with col1:
        busca = st.text_input("🔍 Buscar ajuda...", placeholder="Digite sua dúvida...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎥 Tour Guiado", use_container_width=True):
            st.info("🎬 Tour interativo em desenvolvimento!")
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Início Rápido", 
        "📖 Guias por Módulo", 
        "❓ Perguntas Frequentes", 
        "🔧 Solucionando Problemas"
    ])
    
    with tab1:
        render_quick_start()
    
    with tab2:
        render_module_guides()
    
    with tab3:
        render_faq(busca)
    
    with tab4:
        render_troubleshooting()

def render_quick_start():
    """Guia de início rápido"""
    st.markdown("### 🎯 Primeiros Passos")
    
    st.markdown("""
    Bem-vindo ao **Sistema Lopes & Ribeiro**! Este guia vai te ajudar a começar rapidamente.
    
    #### 1️⃣ Login no Sistema
    - **Usuário padrão:** `admin`
    - **Senha padrão:** `admin`
    - ⚠️ **Importante:** Altere a senha após o primeiro acesso em *Administração*
    
    #### 2️⃣ Navegação
    Use o **menu lateral** para acessar os módulos:
    - 📊 **Painel Geral** - Visão geral e KPIs
    - 👥 **Clientes (CRM)** - Gestão de clientes
    - ⚖️ **Processos** - Controle de processos jurídicos
    - 💰 **Financeiro** - Entradas, saídas e controle financeiro
    - 📈 **Relatórios** - Análises e dashboards
    - 🤖 **IA Jurídica** - Assistente inteligente e análise de documentos
    - 🔐 **Administração** - Usuários e configurações (apenas admin)
    
    #### 3️⃣ Fluxo de Trabalho Recomendado
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        **1. Cadastrar Cliente**
        
        Em *Clientes*, cadastre:
        - Dados pessoais
        - Contato
        - Status do cliente
        - Proposta comercial
        """)
    
    with col2:
        st.success("""
        **2. Criar Processo**
        
        Em *Processos*, registre:
        - Ação judicial
        - Responsável
        - Prazos importantes
        - Andamentos
        """)
    
    with col3:
        st.warning("""
        **3. Registrar Financeiro**
        
        Em *Financeiro*, lance:
        - Honorários (Entrada)
        - Despesas (Saída)
        - Forma de pagamento
        """)
    
    st.divider()
    
    st.markdown("""
    #### 💡 Dicas Importantes
    - 🔄 **Sincronização**: Alterações são salvas automaticamente
    - 📱 **Mobile**: Sistema funciona em celular e tablet
    - 🔒 **Segurança**: Sempre faça logout ao terminar
    - 💾 **Backup**: Faça backup regular em *Administração*
    """)

def render_module_guides():
    """Guias detalhados por módulo"""
    
    module = st.selectbox(
        "Selecione o módulo:",
        ["Dashboard", "Clientes (CRM)", "Processos", "Financeiro", "Relatórios", "IA Jurídica", "Administração"]
    )
    
    if module == "Dashboard":
        render_guide_dashboard()
    elif module == "Clientes (CRM)":
        render_guide_clientes()
    elif module == "Processos":
        render_guide_processos()
    elif module == "Financeiro":
        render_guide_financeiro()
    elif module == "Relatórios":
        render_guide_relatorios()
    elif module == "IA Jurídica":
        render_guide_ia()
    elif module == "Administração":
        render_guide_admin()

def render_guide_dashboard():
    st.markdown("### 📊 Painel Geral (Dashboard)")
    
    st.markdown("""
    O Dashboard oferece uma **visão geral** do escritório em tempo real.
    
    #### 📈 KPIs Disponíveis
    
    1. **Saldo Realizado**
       - Total de entradas - Total de saídas
       - Mostra o fluxo de caixa efetivo
       
    2. **A Receber**
       - Valores pendentes de entrada
       - Monitore inadimplência
       
    3. **Clientes Ativos**
       - Total de clientes com status "ATIVO"
       
    4. **Processos Ativos**
       - Total de processos em andamento
    
    #### 📊 Gráficos
    
    - **Entradas vs Saídas**: Comparativo mensal
    - **Clientes por Status**: Distribuição do funil comercial
    
    > **💡 Dica**: Use o Dashboard para reuniões de planejamento
    """)

def render_guide_clientes():
    st.markdown("### 👥 Clientes (CRM)")
    
    with st.expander("➕ Como Cadastrar um Novo Cliente"):
        st.markdown("""
        1. Clique em **"Novo Cliente"**
        2. Preencha os dados obrigatórios:
           - Nome completo
           - CPF/CNPJ
           - Telefone de contato
        3. Adicione informações complementares:
           - Endereço completo
           - E-mail
           - Profissão/Estado Civil
        4. Defina o **Status do Cliente**:
           - EM NEGOCIAÇÃO
           - ATIVO
           - INATIVO
           - PERDIDO
        5. Clique em **"Salvar Cliente"**
        """)
    
    with st.expander("💼 Gerenciando Propostas"):
        st.markdown("""
        **No cadastro do cliente, você pode:**
        
        - Definir valor da proposta
        - Registrar valor de entrada
        - Especificar número de parcelas
        - Descrever objeto da ação
        - Definir forma de pagamento
        
        > **💡 Dica**: Use a aba "Propostas" para ver todas as propostas abertas
        """)
    
    with st.expander("🔍 Busca e Filtros"):
        st.markdown("""
        - **Buscar por nome**: Digite no campo de busca
        - **Filtrar por status**: Use o seletor de status
        - **Ver detalhes**: Clique no cliente para expandir
        """)

def render_guide_processos():
    st.markdown("### ⚖️ Processos Jurídicos")
    
    with st.expander("➕ Criar Novo Processo"):
        st.markdown("""
        1. Vá em **"Processos"** > **"Novo Processo"**
        2. Preencha:
           - Nome do cliente
           - Tipo de ação
           - Próximo prazo fatal
           - Responsável (advogado)
        3. Clique em **"Cadastrar Processo"**
        """)
    
    with st.expander("📝 Registrar Andamentos"):
        st.markdown("""
        **Para cada movimentação processual:**
        
        1. Acesse o processo
        2. Aba **"Andamentos"**
        3. Clique em **"Novo Andamento"**
        4. Preencha:
           - Data do andamento
           - Descrição detalhada
           - Responsável
        5. Salvar
        
        > Andamentos ficam em ordem cronológica decrescente
        """)
    
    with st.expander("🔗 Links Públicos"):
        st.markdown("""
        **Compartilhe o andamento do processo com o cliente:**
        
        1. Acesse o processo
        2. Aba **"Link Público"**
        3. Clique em **"Gerar Novo Link"**
        4. Configure:
           - Validade (dias)
           - Descrição (opcional)
        5. Copie e envie o link ao cliente
        
        ⚠️ **Segurança**: Links expiram automaticamente
        """)

def render_guide_financeiro():
    st.markdown("### 💰 Módulo Financeiro")
    
    st.markdown("""
    O novo módulo financeiro foi totalmente reformulado para oferecer **inteligência e agilidade**.
    """)
    
    with st.expander("📊 Dashboard Financeiro"):
        st.markdown("""
        No topo da tela, você encontra os **Big Numbers**:
        - **Saldo do Mês**: Quanto sobrou no caixa (Entradas Pagas - Saídas Pagas).
        - **Previsão**: Quanto você deve fechar o mês (considerando o que ainda vai vencer).
        - **Inadimplência**: Total de valores atrasados.
        
        O gráfico de **Fluxo de Caixa** mostra a evolução dos últimos 6 meses.
        """)
    
    with st.expander("➕ Lançamento Inteligente"):
        st.markdown("""
        O novo formulário se adapta ao que você precisa:
        
        1. **Parcelamento Automático**:
           - Selecione "Entrada"
           - Defina o número de parcelas (ex: 12x)
           - O sistema cria 12 lançamentos futuros automaticamente!
           
        2. **Classificação Simplificada**:
           - **Custo do Escritório**: Aluguel, luz, software (Despesas Fixas).
           - **Adiantamento Cliente**: Custas pagas pelo escritório para reembolso (não afeta seu lucro).
        """)
    
    with st.expander("💳 Controle de Pagamentos"):
        st.markdown("""
        - **Status**: Pago ou Pendente
        - **Filtrar por status** para ver inadimplência
        - **Vincular ao cliente** para relatórios de rentabilidade
        """)

def render_guide_relatorios():
    st.markdown("### 📈 Relatórios e Análises")
    
    st.markdown("""
    Agora você conta com relatórios de nível de consultoria financeira.
    
    #### 📅 Funcionalidades Gerais
    - **Filtros de Data**: Selecione qualquer período (Início e Fim) para análise.
    - **Exportação Excel**: Botão "📥 Baixar Excel" em todas as tabelas.
    """)
    
    with st.expander("📈 DRE Gerencial"):
        st.markdown("""
        O **Demonstrativo de Resultado** mostra a saúde real do escritório:
        
        1. **Receita Bruta**: Tudo que entrou.
        2. **(-) Despesas Variáveis**: Impostos e Comissões.
        3. **(=) Margem de Contribuição**: O que sobra para pagar a estrutura.
        4. **(-) Despesas Fixas**: Aluguel, pessoal, etc.
        5. **(=) Lucro Líquido**: O dinheiro limpo no bolso.
        
        *Visualize no gráfico de cascata (waterfall).*
        """)
    
    with st.expander("💎 Rentabilidade por Cliente"):
        st.markdown("""
        Descubra quais clientes dão lucro e quais dão prejuízo.
        
        - **Receita**: Honorários pagos pelo cliente.
        - **Despesa**: Custos que você teve com ele (e não foram reembolsados).
        - **Margem %**: A eficiência do contrato.
        """)
    
    with st.expander("💰 Financeiro e Inadimplência"):
        st.markdown("""
        - **Fluxo de Caixa**: Gráfico de entradas vs saídas
        - **Inadimplência**: Lista de clientes devedores com **Link direto para WhatsApp** de cobrança.
        """)
    
    with st.expander("⚖️ Operacional e Comercial"):
        st.markdown("""
        - **Produtividade**: Processos por advogado.
        - **Prazos Fatais**: Alertas para os próximos 15 dias.
        - **Funil de Vendas**: Quantos clientes estão em negociação.
        """)

def render_guide_ia():
    st.markdown("### 🤖 IA Jurídica Inteligente")
    
    st.markdown("""
    O módulo de IA Jurídica atua como um **assistente virtual** para agilizar sua rotina, powered by Google Gemini.
    """)
    
    with st.expander("💬 Chat Assistente"):
        st.markdown("""
        Converse naturalmente com a IA para:
        - Tirar dúvidas jurídicas
        - Pedir resumos de teses
        - Solicitar modelos de peças
        
        **✨ Novidade:** Agora você pode baixar a resposta da IA!
        1. Faça sua pergunta
        2. Aguarde a resposta
        3. Clique no botão **"📥 Baixar Parecer em Word (.docx)"**
        4. O arquivo vem formatado com cabeçalho do escritório, pronto para edição.
        """)
        
    with st.expander("📄 Análise de Documentos"):
        st.markdown("""
        **Revise contratos e peças em segundos:**
        
        1. Cole o texto ou faça upload (PDF/DOCX/TXT)
        2. Clique em **Analisar Documento**
        3. A IA aponta riscos, cláusulas abusivas e pontos de atenção
        4. **Exporte o relatório** em Word para enviar ao cliente
        """)
        
    with st.expander("💡 Sugestões Inteligentes"):
        st.markdown("""
        **Está travado em um caso?**
        
        - Selecione um processo ativo
        - A IA analisa os dados do caso (ação, status, observações)
        - Receba 5 sugestões práticas de próximas ações
        - Baixe as sugestões em Word para anexar ao planejamento do caso
        """)

def render_guide_admin():
    st.markdown("### 🔐 Administração do Sistema")
    
    st.warning("⚠️ **Acesso restrito**: Apenas usuários com perfil 'admin'")
    
    with st.expander("👤 Gerenciar Usuários"):
        st.markdown("""
        **Criar novo usuário:**
        1. Aba "Usuários"
        2. Preencher username e senha
        3. Escolher perfil (admin ou advogado)
        4. Salvar
        
        **Perfis disponíveis:**
        - **admin**: Acesso total
        - **advogado**: Sem acesso a Administração
        """)
    
    with st.expander("💾 Backup do Banco"):
        st.markdown("""
        **Recomendação**: Fazer backup **semanal**
        
        1. Aba "Backup"
        2. Clicar em "Criar Backup"
        3. Arquivo salvo em `/backups/`
        
        > Arquivos .db contêm todos os dados
        """)

def render_faq(busca=""):
    """Perguntas Frequentes"""
    st.markdown("### ❓ Perguntas Frequentes")
    
    faqs = {
        "Como alterar minha senha?": """
        1. Vá em **Administração** (apenas admin pode)
        2. Aba **Usuários**
        3. Selecione seu usuário
        4. Digite a nova senha
        5. Clique em **Atualizar**
        """,
        
        "Como exportar relatórios?": """
        Atualmente, use o **recurso de impressão** do navegador:
        - Abra o relatório desejado
        - Pressione `Ctrl + P` (Windows) ou `Cmd + P` (Mac)
        - Salve como PDF
        """,
        
        "Posso acessar de vários dispositivos?": """
        ✅ **Sim!** O sistema é 100% web.
        - Acesse de PC, notebook, tablet ou celular
        - Basta ter internet e navegador
        - Mesma URL em todos os dispositivos
        """,
        
        "Como vincular processo ao cliente?": """
        Ao criar o processo, digite o **nome do cliente** 
        exatamente como cadastrado. O sistema fará a vinculação
        automaticamente para relatórios.
        """,
        
        "Cliente pode ver o andamento do processo?": """
        ✅ **Sim!** Use o recurso de **Links Públicos**:
        1. Acesse o processo
        2. Gere um link público
        3. Envie ao cliente
        
        O cliente verá todos os andamentos sem precisar login.
        """,
        
        "Como funciona a inadimplência?": """
        O sistema calcula automaticamente:
        - Lançamentos do tipo **Entrada**
        - Com status **Pendente**
        - Com vencimento **anterior a hoje**
        
        Veja no módulo **Relatórios** > Aba Financeiro
        """,
        
        "Posso ter mais de um escritório?": """
        O sistema é **mono-tenant** (um escritório por instalação).
        Para múltiplos escritórios, seria necessário criar
        instâncias separadas do sistema.
        """,
        
        "Os dados são seguros?": """
        ✅ **Sim!**
        - Conexão HTTPS criptografada
        - Senhas com hash SHA-256
        - Backup automático disponível
        - Logs de auditoria de todas as ações
        """,
        
        "Como salvar a resposta da IA?": """
        Em todas as funcionalidades da IA (Chat, Análise, Sugestões),
        existe um botão **"📥 Baixar Parecer em Word (.docx)"**.
        Basta clicar para baixar o arquivo editável.
        """
    }
    
    # Filtrar por busca
    if busca:
        faqs_filtradas = {k: v for k, v in faqs.items() if busca.lower() in k.lower() or busca.lower() in v.lower()}
    else:
        faqs_filtradas = faqs
    
    if not faqs_filtradas:
        st.info("🔍 Nenhuma FAQ encontrada para sua busca. Tente outros termos.")
    else:
        for pergunta, resposta in faqs_filtradas.items():
            with st.expander(f"❓ {pergunta}"):
                st.markdown(resposta)

def render_troubleshooting():
    """Solucionando Problemas"""
    st.markdown("### 🔧 Solucionando Problemas")
    
    st.markdown("""
    Encontrou algum problema? Veja as soluções abaixo:
    """)
    
    with st.expander("🚫 Erro ao fazer login"):
        st.markdown("""
        **Possíveis causas:**
        
        1. **Senha incorreta**
           - Verifique Caps Lock
           - Senha padrão: `admin`
        
        2. **Usuário desativado**
           - Contate o administrador
           - Verificar status em Administração > Usuários
        
        3. **Banco de dados corrompido**
           - Restaurar backup mais recente
           - Recriar usuário admin
        """)
    
    with st.expander("💾 Dados não estão salvando"):
        st.markdown("""
        **Verificar:**
        
        - Internet está conectada?
        - Não atualize a página enquanto salva
        - Verifique se todos os campos obrigatórios estão preenchidos
        - Veja o log de erros (ícone de erro no canto superior direito)
        """)
    
    with st.expander("📊 Gráficos não aparecem"):
        st.markdown("""
        **Soluções:**
        
        1. Limpe o cache do navegador
        2. Atualize a página (F5)
        3. Verifique se há dados cadastrados
        4. Tente outro navegador (Chrome recomendado)
        """)
    
    with st.expander("🔗 Link público não funciona"):
        st.markdown("""
        **Verificar:**
        
        - Link está dentro do prazo de validade?
        - Copie o link completo (começa com https://)
        - Teste em navegador anônimo
        - Token pode ter sido revogado
        """)
    
    with st.expander("📱 Problemas no celular"):
        st.markdown("""
        **Otimize a experiência mobile:**
        
        - Use Chrome ou Safari
        - Ative modo Desktop se estiver muito comprimido
        - Gire para modo paisagem em tabelas grandes
        - Adicione à tela inicial para acesso rápido
        """)
    
    st.divider()
    
    st.info("""
    ### 🆘 Ainda com problemas?
    
    **Entre em contato com o suporte:**
    - 📧 Email: suporte@lopesribeiroadvogados.com
    - 📱 WhatsApp: (XX) 9XXXX-XXXX
    - 📝 Descreva o problema em detalhes
    - 📸 Envie capturas de tela se possível
    """)
    
    st.success("""
    **💡 Dica**: Antes de reportar, tente:
    1. Atualizar a página (F5)
    2. Limpar cache do navegador
    3. Fazer logout e login novamente
    """)
