import streamlit as st
import hashlib
import bcrypt
import base64
import time
import os
from datetime import datetime, timedelta
import database as db
from modules import dashboard, clientes, processos, agenda, financeiro, ia_juridica, relatorios, ajuda, admin, conciliacao_bancaria, parceiros, propostas, ai_proactive, aniversarios, automacao_financeiro, alertas_email, notifications, drive
from components.ui import load_css
import rate_limiter as rl
import lgpd_logger

# LGPD: Aplicar mascaramento automático em TODOS os logs do sistema
# Isso protege CPF, CNPJ, emails, telefones, senhas
lgpd_logger.patch_all_loggers()

# Page Config
st.set_page_config(
    page_title="Lopes & Ribeiro - Sistema Jurídico",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()
db.init_db()
db.criar_backup()
ai_proactive.inicializar()
automacao_financeiro.inicializar()  # Sprint 2: Automação Financeiro ↔ Processos

# === VERIFICAR SE É ACESSO PÚBLICO (SEM LOGIN) ===
query_params = st.query_params
if "token" in query_params:
    # Renderizar visualização pública
    import public_view  # Importa e executa o módulo
    st.stop()  # Para aqui, não continua para tela de login

# --- GESTÃO DE SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None
# login_attempts removido - agora usa rate_limiter com persistência em banco

def is_bcrypt_hash(hash_string):
    """Detecta se o hash é bcrypt (começa com $2b$)"""
    return hash_string.startswith('$2b$') if hash_string else False

def verify_password(password, stored_hash):
    """Verifica senha com suporte híbrido SHA-256/bcrypt"""
    if is_bcrypt_hash(stored_hash):
        # Verificar com bcrypt
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except:
            return False
    else:
        # Verificar com SHA-256 (legacy)
        senha_hash = hashlib.sha256(password.encode()).hexdigest()
        return senha_hash == stored_hash

def upgrade_to_bcrypt(username, password):
    """Converte senha SHA-256 para bcrypt"""
    try:
        senha_bcrypt = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.sql_run("UPDATE usuarios SET password_hash = ? WHERE username = ?", 
                   (senha_bcrypt, username))
        return True
    except Exception as e:
        print(f"Erro ao atualizar hash: {e}")
        return False

def login():
    # Modern SaaS Login Header
    logo_path = "LOGO.jpg"
    
    if os.path.exists(logo_path):
        # Centralização robusta via HTML/CSS (funciona em mobile/desktop)
        try:
            with open(logo_path, "rb") as img_file:
                 img_b64 = base64.b64encode(img_file.read()).decode()
            
            st.markdown(
                f"""
                <div style='text-align: center; margin-bottom: 20px;'>
                    <img src='data:image/jpeg;base64,{img_b64}' width='120' style='border-radius: 10px;'>
                </div>
                """, 
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Erro ao carregar logo: {e}")
        
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 40px;'>
                <h1 style="font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">Lopes & Ribeiro</h1>
                <p style="font-size: 1.125rem; color: #64748b;">Acesse seu painel jurídico inteligente</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 80px; margin-bottom: 40px;'>
                <div style="font-size: 4rem; margin-bottom: 1rem;">⚖️</div>
                <h1 style="font-weight: 800; color: #0f172a; margin-bottom: 0.5rem;">Lopes & Ribeiro</h1>
                <p style="font-size: 1.125rem; color: #64748b;">Acesse seu painel jurídico inteligente</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # State para controlar tela de login / recuperação
    if 'show_recovery' not in st.session_state: st.session_state.show_recovery = False
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        
        if st.session_state.show_recovery:
            # --- TELA DE RECUPERAÇÃO ---
            with st.container():
                st.markdown("### 🔐 Recuperação de Senha")
                
                step = 1
                if 'rec_user' in st.session_state: step = 2
                if 'rec_verifying_code' in st.session_state: step = 2.5 # Verificando código email
                if 'rec_verified' in st.session_state: step = 3
                
                if step == 1:
                    username_rec = st.text_input("Digite seu usuário para continuar")
                    if st.button("Buscar"):
                        user_data = db.get_usuario_by_username(username_rec)
                        if user_data:
                            st.session_state.rec_user = user_data
                            st.rerun()
                        else:
                            st.error("Usuário não encontrado.")
                        
                    st.markdown("---")
                    if st.button("Voltar ao Login"):
                        st.session_state.show_recovery = False
                        st.rerun()
                            
                elif step == 2:
                    user_data = st.session_state.rec_user
                    
                    st.write(f"Olá, **{user_data['nome']}**")
                    st.write("Escolha um método de recuperação:")
                    
                    has_email = bool(user_data.get('email'))
                    has_question = bool(user_data.get('pergunta_secreta'))
                    
                    col_metodo1, col_metodo2 = st.columns(2)
                    
                    use_email = False
                    use_question = False
                    
                    with col_metodo1:
                        if has_email:
                            if st.button("📧 Enviar E-mail"):
                                import utils_email
                                import random
                                
                                # Gerar código e salvar
                                codigo = str(random.randint(100000, 999999))
                                expiry = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
                                
                                db.sql_run("UPDATE usuarios SET reset_token = ?, reset_expiry = ? WHERE id = ?", (codigo, expiry, user_data['id']))
                                
                                # Enviar email
                                sucesso, erro = utils_email.enviar_codigo_recuperacao(user_data['email'], codigo)
                                
                                if sucesso:
                                    st.success(f"Código enviado para {user_data['email']}")
                                    st.session_state.rec_verifying_code = True
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao enviar email: {erro}")
                        else:
                            st.warning("Sem e-mail cadastrado.")
                            
                    with col_metodo2:
                        if has_question:
                            if st.button("❓ Pergunta Secreta"):
                                st.session_state.rec_using_question = True
                                st.rerun()
                        else:
                            st.warning("Sem pergunta secreta.")
                            
                    if not has_email and not has_question:
                        st.error("Nenhum método de recuperação configurado. Contate o administrador.")
                        
                    if st.button("Voltar"):
                        del st.session_state.rec_user
                        st.rerun()
                
                elif step == 2.5: # Validar Código de Email
                    st.info(f"Um código foi enviado para o email cadastrado.")
                    codigo_input = st.text_input("Digite o código de 6 dígitos")
                    
                    if st.button("Verificar Código"):
                        # Verificar no banco
                        fresh_user = db.get_usuario_by_username(st.session_state.rec_user['username'])
                        token = fresh_user.get('reset_token')
                        expiry = fresh_user.get('reset_expiry')
                        
                        if not token or not expiry:
                            st.error("Solicitação inválida ou expirada.")
                        elif datetime.now() > datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S"):
                            st.error("O código expirou.")
                        elif codigo_input == token:
                            st.session_state.rec_verified = True
                            st.rerun()
                        else:
                            st.error("Código incorreto.")
                            
                    if st.button("Voltar"):
                        if 'rec_verifying_code' in st.session_state: del st.session_state.rec_verifying_code
                        st.rerun()

                elif 'rec_using_question' in st.session_state: # Validar Pergunta (Estado especial)
                     # ... Logica da pergunta secreta (mantida do anterior, adaptador aqui)
                    user_data = st.session_state.rec_user
                    st.info(f"Pergunta: **{user_data['pergunta_secreta']}**")
                    resposta = st.text_input("Sua resposta", type="password")
                    
                    if st.button("Verificar Resposta"):
                        sent_hash = user_data.get('resposta_secreta_hash')
                        valid = False
                        try:
                            valid = bcrypt.checkpw(resposta.strip().lower().encode(), sent_hash.encode())
                        except:
                            pass
                            
                        if valid:
                            st.session_state.rec_verified = True
                            if 'rec_using_question' in st.session_state: del st.session_state.rec_using_question
                            st.rerun()
                        else:
                            st.error("Resposta incorreta.")
                    
                    if st.button("Voltar aos Métodos"):
                         del st.session_state.rec_using_question
                         st.rerun()

                elif step == 3:
                    st.success("Identidade confirmada! Defina sua nova senha.")
                    new_pass = st.text_input("Nova Senha", type="password")
                    conf_pass = st.text_input("Confirmar Senha", type="password")
                    
                    if st.button("Redefinir Senha"):
                        if new_pass != conf_pass:
                            st.error("As senhas não coincidem.")
                        elif len(new_pass) < 6:
                            st.error("A senha deve ter no mínimo 6 caracteres.")
                        else:
                            # Atualizar senha e limpar token
                            senha_hash = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                            db.sql_run("UPDATE usuarios SET password_hash = ?, reset_token = NULL WHERE id = ?", (senha_hash, st.session_state.rec_user['id']))
                            st.success("Senha atualizada com sucesso! Faça login.")
                            
                            # Limpar sessão de recuperação
                            keys_to_clear = ['rec_user', 'rec_verified', 'show_recovery', 'rec_verifying_code', 'rec_using_question']
                            for k in keys_to_clear:
                                if k in st.session_state: del st.session_state[k]
                            time.sleep(2)
                            st.rerun()

        else:
            # --- TELA DE LOGIN ---
            with st.form("login_form"):
                username = st.text_input(
                    "Usuário",
                    placeholder="Digite seu usuário",
                    help="Use seu nome de usuário cadastrado no sistema"
                )
                password = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="••••••••",
                    help="Digite sua senha de acesso"
                )
                submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")
                
                if submit:
                    # 1. Validação de campos vazios
                    if not username or not password:
                        st.error("❌ Por favor, preencha todos os campos")
                        st.stop()
                    
                    # 2. RATE LIMITING - Obter IP do cliente
                    ip_address = rl.get_client_ip()
                    
                    # 3. Verificar rate limit
                    limiter = rl.get_rate_limiter()
                    check = limiter.check_login_attempts(ip_address, username)
                    
                    if not check['allowed']:
                        st.error(check['message'])
                        st.caption(f"Tente novamente após: {check['reset_at'].strftime('%H:%M')}")
                        
                        # Log de auditoria
                        db.audit('login_blocked', {
                            'username': username,
                            'ip': ip_address,
                            'reason': 'rate_limit_exceeded',
                            'reset_at': check['reset_at'].isoformat()
                        })
                        st.stop()
                    
                    # Mostrar aviso se poucas tentativas restantes
                    if check['message']:
                        st.warning(check['message'])
                    
                    # 4. Verificar credenciais
                    user_data = db.get_usuario_by_username(username)
                    
                    if user_data and user_data['ativo'] == 1:
                        stored_hash = user_data['password_hash']
                        
                        # Verificar senha (híbrido: SHA-256 ou bcrypt)
                        if verify_password(password, stored_hash):
                            # ✅ LOGIN BEM-SUCEDIDO
                            limiter.record_login_attempt(ip_address, username, success=True)
                            
                            # Converter para bcrypt se ainda estiver em SHA-256
                            if not is_bcrypt_hash(stored_hash):
                                upgrade_to_bcrypt(username, password)
                            
                            # Configurar sessão
                            st.session_state.logged_in = True
                            st.session_state.user = user_data['nome']
                            st.session_state.username = user_data['username']
                            st.session_state.role = user_data['role']
                            
                            # Log de auditoria
                            db.audit('login_success', {
                                'username': username,
                                'ip': ip_address,
                                'role': user_data['role']
                            })
                            
                            st.success("✅ Login realizado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            # ❌ SENHA INCORRETA
                            limiter.record_login_attempt(ip_address, username, success=False)
                            
                            # Verificar quantas tentativas restam
                            check_remaining = limiter.check_login_attempts(ip_address, username)
                            
                            if check_remaining['remaining'] > 0:
                                st.error(f"❌ Usuário ou senha inválidos")
                                st.caption(check_remaining['message'])
                            else:
                                st.error("🚫 Muitas tentativas. Conta bloqueada temporariamente.")
                            
                            # Log de auditoria
                            db.audit('login_failed', {
                                'username': username,
                                'ip': ip_address,
                                'remaining': check_remaining['remaining']
                            })
                    else:
                        # USUÁRIO NÃO ENCONTRADO OU INATIVO
                        # Ainda aplicar rate limiting para dificultar enumeração de usernames
                        limiter.record_login_attempt(ip_address, username, success=False)
                        
                        check_remaining = limiter.check_login_attempts(ip_address, username)
                        
                        if check_remaining['remaining'] > 0:
                            st.error(f"❌ Usuário ou senha inválidos")
                            st.caption(check_remaining['message'])
                        else:
                            st.error("🚫 Muitas tentativas. Bloqueado por 15 minutos")
                        
                        # Log de auditoria
                        db.audit('login_failed', {
                            'username': username,
                            'ip': ip_address,
                            'reason': 'user_not_found_or_inactive'
                        })
            
            # Link de recuperação de senha
            st.markdown("<div style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
            if st.button("Esqueci minha senha", type="secondary", use_container_width=False):
                st.session_state.show_recovery = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# --- APP PRINCIPAL ---
if not st.session_state.logged_in:
    login()
else:
    # --- ALERTA DE ANIVERSARIANTES DO DIA ---
    if 'aniversario_mostrado_hoje' not in st.session_state:
        st.session_state.aniversario_mostrado_hoje = None
    
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Verificar se já mostrou hoje
    if st.session_state.aniversario_mostrado_hoje != data_hoje:
        try:
            aniv_hoje = aniversarios.get_aniversariantes_hoje()
            if not aniv_hoje.empty:
                # Criar dialog de aniversariantes
                @st.dialog("🎂 Aniversariantes de Hoje!")
                def mostrar_aniversariantes():
                    st.balloons()
                    for idx, cliente in aniv_hoje.iterrows():
                        idade = aniversarios.calcular_idade(cliente['data_nascimento']) if cliente['data_nascimento'] else None
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if idade:
                                st.markdown(f"### 🎉 {cliente['nome']} ({idade} anos)")
                            else:
                                st.markdown(f"### 🎉 {cliente['nome']}")
                        
                        with col2:
                            if cliente.get('telefone'):
                                template = aniversarios.get_template_mensagem()
                                mensagem = aniversarios.formatar_mensagem_aniversario(cliente['nome'], idade, template)
                                link_whatsapp = aniversarios.gerar_link_whatsapp(cliente['telefone'], mensagem)
                                st.link_button("📱 Parabéns", link_whatsapp, use_container_width=True)
                        
                        st.divider()
                    
                    if st.button("Fechar", type="primary", use_container_width=True):
                        st.session_state.aniversario_mostrado_hoje = data_hoje
                        st.rerun()
                
                # Marcar como mostrado e exibir popup
                st.session_state.aniversario_mostrado_hoje = data_hoje
                mostrar_aniversariantes()
        except Exception as e:
            # Silenciar erros para não quebrar o app
            pass
    # Função para renderizar o chat (reutilizável)
    def render_copilot_chat(container_context, is_popover=False):
        with container_context:
            # Verificar Insights
            insights = db.sql_get_query("SELECT * FROM ai_insights WHERE lido = 0 ORDER BY id DESC LIMIT 3")
            if not insights.empty:
                st.caption("🔔 Novos Insights")
                for _, row in insights.iterrows():
                    st.info(f"**{row['titulo']}**\n\n{row['descricao']}")
                    if st.button("Marcar como lido", key=f"read_{row['id']}_{'pop' if is_popover else 'side'}"):
                        db.sql_run("UPDATE ai_insights SET lido = 1 WHERE id = ?", (row['id'],))
                        st.rerun()
            else:
                st.caption("Nenhum novo alerta.")
            
            st.divider()
            
            # Chat Rápido
            if "sidebar_chat" not in st.session_state:
                st.session_state.sidebar_chat = []
                
            # Container para mensagens (para scroll)
            # No popover, definimos uma altura fixa para o chat não crescer infinitamente
            height = 300 if is_popover else 400
            chat_container = st.container(height=height)
            
            with chat_container:
                for msg in st.session_state.sidebar_chat:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
            
            # Input do usuário
            key_suffix = "pop" if is_popover else "side"
            
            if is_popover:
                # No popover, usamos text_input + button para evitar problemas de layout do chat_input
                with st.form(key=f"chat_form_{key_suffix}", clear_on_submit=True):
                    cols = st.columns([4, 1])
                    prompt = cols[0].text_input("Mensagem", label_visibility="collapsed", placeholder="Digite sua dúvida...")
                    enviar = cols[1].form_submit_button("➤")
                    
                if enviar and prompt:
                    processar_chat(prompt, chat_container)
            else:
                # Na sidebar, usamos o chat_input padrão
                if prompt := st.chat_input("Pergunte ao Copiloto...", key=f"chat_input_{key_suffix}"):
                    processar_chat(prompt, chat_container)

    def processar_chat(prompt, container):
        # Adicionar mensagem do usuário
        st.session_state.sidebar_chat.append({"role": "user", "content": prompt})
        with container:
            with st.chat_message("user"):
                st.write(prompt)
        
        # Obter resposta da IA
        with container:
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        response = ai_proactive.get_copilot_response(prompt)
                        st.write(response)
                        # Adicionar resposta ao histórico
                        st.session_state.sidebar_chat.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")

    # --- MENU LATERAL ---
    with st.sidebar:
        # Logo e Título (Moderno SaaS)
        if os.path.exists("LOGO.jpg"):
            try:
                with open("LOGO.jpg", "rb") as img_file:
                     logo_b64 = base64.b64encode(img_file.read()).decode()
                st.markdown(
                    f"""
                    <div style="text-align: center; margin-bottom: 10px;">
                        <img src="data:image/jpeg;base64,{logo_b64}" width="80" style="border-radius: 5px;">
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            except:
                st.image("LOGO.jpg", width=80)
        else:
            st.image("LOGO.jpg", width=80)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="margin: 0; font-weight: 700; color: #0f172a;">Lopes & Ribeiro</h2>
                <p style="font-size: 0.875rem; color: #64748b;">Sistema de Gestão Jurídica</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        st.markdown(f"<div style='background-color: #f1f5f9; padding: 0.75rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: center;'><span style='font-size: 0.875rem; color: #475569; font-weight: 500;'>Olá, {st.session_state.user}</span></div>", unsafe_allow_html=True)
        
        # === BUSCA GLOBAL UNIFICADA ===
        termo_busca = st.text_input(
            "🔍 Busca Global",
            placeholder="Cliente, processo, financeiro...",
            key="busca_global_input",
            label_visibility="collapsed"
        )
        
        if termo_busca and len(termo_busca) >= 3:
            resultados = db.busca_global(termo_busca, limite=10)
            
            if resultados['total'] > 0:
                with st.expander(f"📋 {resultados['total']} resultado(s)", expanded=True):
                    # Clientes
                    if not resultados['clientes'].empty:
                        st.caption("👤 **Clientes**")
                        for _, row in resultados['clientes'].iterrows():
                            telefone = row.get('telefone', '')[:15] if row.get('telefone') else ''
                            label = f"{row['nome']}"
                            if telefone:
                                label += f" ({telefone})"
                            if st.button(label, key=f"bg_cli_{row['id']}", use_container_width=True):
                                st.session_state.cliente_selecionado = row['id']
                                st.session_state.nav_selection = "Clientes (CRM)"
                                st.rerun()
                    
                    # Processos
                    if not resultados['processos'].empty:
                        st.caption("📁 **Processos**")
                        for _, row in resultados['processos'].iterrows():
                            acao = row['acao'][:25] + "..." if len(str(row['acao'])) > 25 else row['acao']
                            label = f"{row['cliente_nome']} - {acao}"
                            if st.button(label, key=f"bg_proc_{row['id']}", use_container_width=True):
                                st.session_state.processo_id = row['id']
                                st.session_state.nav_selection = "Processos"
                                st.rerun()
                    
                    # Financeiro
                    if not resultados['financeiro'].empty:
                        st.caption("💰 **Financeiro**")
                        for _, row in resultados['financeiro'].iterrows():
                            desc = row['descricao'][:20] + "..." if len(str(row['descricao'])) > 20 else row['descricao']
                            valor = f"R$ {row['valor']:,.2f}" if row['valor'] else ""
                            st.markdown(f"• {desc} **{valor}**")
            elif termo_busca:
                st.caption("🔍 Nenhum resultado encontrado.")
        
        st.markdown("---")
        
        # Definição dos Módulos Disponíveis

        all_modules = {
            "Painel Geral": dashboard,
            "Clientes (CRM)": clientes,
            "Processos": processos,
            "📅 Agenda": agenda,
            "🎂 Aniversários": aniversarios,
            "Financeiro": financeiro,
            "🤝 Parceiros": parceiros,
            "💰 Propostas": propostas,
            "🏦 Conciliação Bancária": conciliacao_bancaria,
            "🤖 IA Jurídica": ia_juridica,
            "📧 Alertas E-mail": alertas_email,
            "Relatórios": relatorios,
            "📁 Google Drive": drive,
            "📚 Ajuda": ajuda
        }
        
        # Filtro de Permissões
        role = st.session_state.role
        menu_options = {}
        
        # Regras de Visibilidade
        # Módulos Básicos (Todos acessam)
        modulos_basicos = ["Painel Geral", "Clientes (CRM)", "Processos", "📅 Agenda", "🎂 Aniversários", "📚 Ajuda"]
        for mod in modulos_basicos:
            if mod in all_modules:
                menu_options[mod] = all_modules[mod]
                
        # Módulos Financeiros/Estratégicos (Bloqueados para Secretaria)
        if role != 'secretaria':
            # Advogados e Admins veem
            menu_options["Financeiro"] = financeiro
            menu_options["🏦 Conciliação Bancária"] = conciliacao_bancaria
            menu_options["Relatórios"] = relatorios
            menu_options["🤝 Parceiros"] = parceiros
            menu_options["💰 Propostas"] = propostas
            menu_options["🤖 IA Jurídica"] = ia_juridica
        else:
            # Secretaria vê Propostas e Parceiros e IA
             menu_options["💰 Propostas"] = propostas
             menu_options["🤝 Parceiros"] = parceiros
             menu_options["🤖 IA Jurídica"] = ia_juridica
             
        # Administração (Sempre visível, mas conteúdo interno muda)
        menu_options["Administração"] = admin
        
        # Processar navegação pendente (evita erro de modificação após widget ser instanciado)
        if "next_nav" in st.session_state and st.session_state.next_nav:
            st.session_state.nav_selection = st.session_state.next_nav
            st.session_state.next_nav = None  # Limpar flag
        
        if "nav_selection" not in st.session_state:
            st.session_state.nav_selection = "Painel Geral"
            
        selection = st.radio("Navegação", list(menu_options.keys()), key="nav_selection")
        
        st.markdown("---")
        
        # --- COPILOTO IA (SIDEBAR) ---
        with st.expander("🤖 Copiloto IA (Sidebar)", expanded=False):
            render_copilot_chat(st.container(), is_popover=False)
        
        # --- CENTRO DE NOTIFICAÇÕES (FASE 3) ---
        notif_count = int(notifications.contar_nao_lidas(st.session_state.get('username')) or 0)
        notif_label = f"🔔 Notificações ({notif_count})" if notif_count > 0 else "🔔 Notificações"
        with st.expander(notif_label, expanded=bool(notif_count > 0)):
            notifications.render_centro_notificacoes()

        st.markdown("---")
        
        # --- TOGGLE DE TEMA (Sprint 4) ---
        from components.ui import render_theme_toggle
        render_theme_toggle()

        if st.button("🚪 Sair / Logout", use_container_width=True):
            logout()
            
        st.caption("v4.0.0 - Sprint 4 UX")

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

    # --- BOTÃO FLUTUANTE (FAB) ---
    with st.popover("🤖", help="Copiloto IA"):
        st.markdown("### 🤖 Copiloto Inteligente")
        render_copilot_chat(st.container(), is_popover=True)