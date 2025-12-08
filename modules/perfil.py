import streamlit as st
import database as db
import utils as ut
import bcrypt

def render():
    st.markdown("<h1 style='color: var(--text-main);'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    
    # Informações do Usuário
    user_data = db.get_usuario_by_username(st.session_state.user_data['username']) if 'user_data' in st.session_state else None
    
    # Verificando sessão

    
    if 'username' not in st.session_state:
        st.error("Erro de sessão: Username não encontrado. Por favor, faça login novamente.")
        return

    username = st.session_state.username
    usuario_row = db.get_usuario_by_username(username)
    
    if not usuario_row:
        st.error("Usuário não encontrado.")
        return
        
    # Converter Row para dict para permitir uso de .get()
    usuario = dict(usuario_row)

    tab1, tab2 = st.tabs(["🔒 Alterar Senha", "🛡️ Segurança & Recuperação"])
    
    with tab1:
        st.write("### Alterar Senha de Acesso")
        with st.form("form_alterar_senha"):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.form_submit_button("Atualizar Senha", type="primary"):
                # Verificar senha atual
                stored_hash = usuario['password_hash']
                senha_valida = False
                try:
                    if stored_hash.startswith('$2b$'):
                        senha_valida = bcrypt.checkpw(senha_atual.encode(), stored_hash.encode())
                    else:
                        import hashlib
                        senha_valida = hashlib.sha256(senha_atual.encode()).hexdigest() == stored_hash
                except:
                    pass
                
                if not senha_valida:
                    st.error("A senha atual está incorreta.")
                elif nova_senha != confirma_senha:
                    st.error("As novas senhas não coincidem.")
                elif len(nova_senha) < 6:
                    st.error("A nova senha deve ter pelo menos 6 caracteres.")
                else:
                    # Atualizar
                    novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                    db.sql_run("UPDATE usuarios SET password_hash = ? WHERE id = ?", (novo_hash, usuario['id']))
                    st.success("✅ Senha atualizada com sucesso!")
                    
    with tab2:
        st.write("### 🛡️ Segurança & Recuperação")
        
        # --- Email de Recuperação ---
        st.write("#### 📧 E-mail de Recuperação")
        st.caption("Usado para receber códigos de redefinição de senha.")
        
        email_atual = usuario.get('email')
        if email_atual:
            st.success(f"E-mail cadastrado: **{email_atual}**")
        else:
            st.warning("⚠️ Nenhum e-mail cadastrado. Você não poderá recuperar sua senha se esquecê-la.")
            
        with st.form("form_email"):
            novo_email = st.text_input("Novo E-mail", value=email_atual if email_atual else "")
            
            if st.form_submit_button("Salvar E-mail"):
                if not ut.validar_email(novo_email):
                    st.error("E-mail inválido.")
                else:
                    db.sql_run("UPDATE usuarios SET email = ? WHERE id = ?", (novo_email, usuario['id']))
                    st.success("✅ E-mail atualizado!")
                    st.rerun()
                    
        st.divider()

        st.write("#### 🔐 Pergunta de Segurança (Método Alternativo)")
        st.markdown("Configure uma pergunta de segurança para recuperar sua senha caso a esqueça.")
        
        # Verificar se já tem pergunta definida
        tem_pergunta = bool(usuario.get('pergunta_secreta'))
        
        if tem_pergunta:
            st.info(f"✅ Você já tem uma pergunta configurada: **{usuario['pergunta_secreta']}**")
            st.write("Para alterar, preencha abaixo:")
        else:
            st.warning("⚠️ Você ainda não configurou uma pergunta de segurança.")
        
        with st.form("form_seguranca"):
            pergunta = st.selectbox(
                "Escolha uma pergunta",
                [
                    "Qual o nome do seu primeiro animal de estimação?",
                    "Qual o nome da cidade onde você nasceu?",
                    "Qual o nome da sua escola primária?",
                    "Qual o sobrenome de solteira da sua mãe?",
                    "Qual é o seu livro favorito?",
                    "Qual era o apelido do seu melhor amigo na infância?"
                ]
            )
            
            # Opção de pergunta personalizada
            usar_personalizada = st.checkbox("Criar minha própria pergunta")
            if usar_personalizada:
                pergunta = st.text_input("Sua pergunta personalizada")
            
            resposta = st.text_input("Sua resposta (será salva de forma segura)", type="password", help="A resposta não diferencia maiúsculas de minúsculas.")
            
            senha_confirm = st.text_input("Confirme sua senha atual para salvar", type="password")
            
            if st.form_submit_button("Salvar Configurações de Segurança"):
                # Verificar senha
                stored_hash = usuario['password_hash']
                senha_valida = False
                try:
                   if stored_hash.startswith('$2b$'):
                       senha_valida = bcrypt.checkpw(senha_confirm.encode(), stored_hash.encode())
                   else:
                       import hashlib
                       senha_valida = hashlib.sha256(senha_confirm.encode()).hexdigest() == stored_hash
                except:
                   pass
                
                if not senha_valida:
                   st.error("Senha atual incorreta. Não foi possível salvar.")
                elif not pergunta or not resposta:
                    st.error("Preencha a pergunta e a resposta.")
                else:
                    # Hash da resposta (normalizada para lower e strip)
                    resposta_limpa = resposta.strip().lower()
                    resposta_hash = bcrypt.hashpw(resposta_limpa.encode(), bcrypt.gensalt()).decode()
                    
                    db.sql_run(
                        "UPDATE usuarios SET pergunta_secreta = ?, resposta_secreta_hash = ? WHERE id = ?",
                        (pergunta, resposta_hash, usuario['id'])
                    )
                    st.success("✅ Configurações de segurança atualizadas!")
                    st.rerun()
