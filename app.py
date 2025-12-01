load_css()
db.init_db()
db.criar_backup()

# --- GESTÃO DE SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None

def login():
    st.markdown("<div style='text-align: center; margin-top: 50px;'><h1>⚖️ Lopes & Ribeiro</h1><p>Sistema de Gestão Jurídica</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            
            if submit:
                senha_hash = hashlib.sha256(password.encode()).hexdigest()
                # Verificar credenciais
                user_data = db.get_usuario_by_username(username)
                
                if user_data is not None:
                    stored_hash = user_data['password_hash']
                    if senha_hash == stored_hash and user_data['ativo'] == 1:
                        st.session_state.logged_in = True
                        st.session_state.user = user_data['nome']
                        st.session_state.role = user_data['role']
                        st.success("Login realizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Senha incorreta ou usuário inativo.")
                else:
                    st.error("Usuário não encontrado.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# --- APP PRINCIPAL ---
if not st.session_state.logged_in:
    login()
else:
    # --- MENU LATERAL ---
    with st.sidebar:
        st.title("Lopes & Ribeiro")
        st.caption(f"Olá, {st.session_state.user}")
        st.markdown("---")
        
        menu_options = {
            "Painel Geral": dashboard,
            "Clientes (CRM)": clientes,
            "Processos": processos,
            "📅 Agenda": agenda,
            "Financeiro": financeiro,
            "🤖 IA Jurídica": ia_juridica,
            "Relatórios": relatorios,
            "📚 Ajuda": ajuda
        }
        
        # Adicionar Admin apenas se for admin
        if st.session_state.role == 'admin':
            menu_options["Administração"] = admin
        
        if "nav_selection" not in st.session_state:
            st.session_state.nav_selection = "Painel Geral"
            
        selection = st.radio("Navegação", list(menu_options.keys()), key="nav_selection")
        
        st.markdown("---")
        if st.button("Sair / Logout", use_container_width=True):
            logout()
            
        st.caption("v2.2 - Agenda Integrada")

    # --- ROTEAMENTO COM ESCUDO DE ERROS ---
    if selection in menu_options:
        try:
            module = menu_options[selection]
            module.render()
        except Exception as e:
            st.error("Ocorreu um erro inesperado ao carregar este módulo.")
            st.warning(f"Detalhes do erro: {e}")
            # Em produção, você registraria isso em um log silencioso
            # logger.error(f"Erro no módulo {selection}: {e}")