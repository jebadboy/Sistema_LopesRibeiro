import streamlit as st
import database as db
import pandas as pd
import bcrypt
import re
import os
import time

def render():
    st.markdown("<h1 style='color: var(--text-main);'>⚙️ Administração</h1>", unsafe_allow_html=True)
    
    # Verificar permissões
    is_admin = st.session_state.role == 'admin'
    
    if is_admin:
        tab_users, tab_config, tab_audit = st.tabs(["👥 Usuários", "🏢 Configurações", "📝 Auditoria"])
        
        with tab_users:
            render_usuarios(is_admin=True)
            
        with tab_config:
            render_configuracoes()
            
        with tab_audit:
            render_auditoria()
    else:
        # Usuário comum vê apenas abas relevantes (apenas Usuários no momento per user request)
        # "a aba MEUPERFIL, se confunde com a aba usuarios, deveria ser excluida a aba perfil e tudo se concentrar na ba USUARIOS"
        render_usuarios(is_admin=False)

def render_auditoria():
    st.markdown("### 📝 Logs de Auditoria")
    st.caption("Histórico de ações importantes realizadas no sistema.")
    
    # Filtros
    c1, c2 = st.columns([2, 1])
    termo = c1.text_input("Filtrar por usuário ou ação", placeholder="Ex: admin, alteração de senha...")
    limit = c2.number_input("Limite de registros", min_value=10, max_value=500, value=50)
    
    query = "SELECT timestamp as Data, username as Usuário, action as Ação, details as Detalhes FROM audit_logs"
    params = []
    
    if termo:
        query += " WHERE username LIKE ? OR action LIKE ? OR details LIKE ?"
        term_like = f"%{termo}%"
        params = [term_like, term_like, term_like]
        
    query += f" ORDER BY id DESC LIMIT {limit}"
    
    df = db.sql_get_query(query, params)
    
    if not df.empty:
        # Formatar data se possível
        try:
            df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%d/%m/%Y %H:%M:%S')
        except:
            pass
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro de auditoria encontrado.")

def render_configuracoes():
    st.markdown("### 🏢 Dados do Escritório")
    # ... (Manter código existente de configurações, adicionando logs de auditoria nas ações)
    # Para brevidade, re-implementando com logs
    
    # Upload de Logo
    col_logo_curr, col_logo_up = st.columns([1, 2])
    logo_path = "LOGO.jpg"
    if os.path.exists(logo_path):
        col_logo_curr.image(logo_path, caption="Logo Atual", width=150)
    
    uploaded_logo = col_logo_up.file_uploader("Alterar Logotipo (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
    if uploaded_logo:
        try:
            with open(logo_path, "wb") as f:
                f.write(uploaded_logo.getbuffer())
            db.audit("config_update", "Atualizou o logotipo do escritório")
            st.success("Logotipo atualizado!")
        except Exception as e:
            st.error(f"Erro: {e}")

    with st.form("config_escritorio"):
        c1, c2 = st.columns(2)
        nome_escritorio = c1.text_input("Nome do Escritório", value=db.get_config('nome_escritorio', 'Lopes & Ribeiro Advogados'))
        nome_adv = c2.text_input("Nome do Advogado(a)", value=db.get_config('nome_advogado_relatorios', 'Dra. Sheila Lopes'))
        oab = st.text_input("OAB", value=db.get_config('oab', 'OAB/RJ nº 215691'))
        end = st.text_input("Endereço", value=db.get_config('endereco_escritorio', ''))
        tel = st.text_input("Telefone", value=db.get_config('telefone_escritorio', ''))
        email = st.text_input("Email", value=db.get_config('email_escritorio', ''))
        
        if st.form_submit_button("Salvar Configurações"):
            db.set_config('nome_escritorio', nome_escritorio)
            db.set_config('nome_advogado_relatorios', nome_adv)
            db.set_config('oab', oab)
            db.set_config('endereco_escritorio', end)
            db.set_config('telefone_escritorio', tel)
            db.set_config('email_escritorio', email)
            
            db.audit("config_update", f"Atualizou dados cadastrais do escritório")
            st.success("Salvo!")
            st.rerun()
    
    st.divider()
    
    # === INTEGRAÇÃO DATAJUD (CNJ) ===
    st.markdown("### 🔑 Integração DataJud (CNJ)")
    st.caption("Configure o token de API para buscar processos automaticamente pelo número CNJ")
    
    with st.expander("ℹ️ Como obter o token DataJud", expanded=False):
        st.markdown("""
        **Passo a passo:**
        1. Acesse: [https://datajud.cnj.jus.br](https://datajud.cnj.jus.br)
        2. Faça login ou cadastre-se
        3. Vá em "API Pública" → "Gerar Token"
        4. Copie o token gerado
        5. Cole no campo abaixo
        
        **Dicas:**
        - O token é válido por vários meses
        - Guarde o token em local seguro
        - Se expirar, basta gerar outro e atualizar aqui
        """)
    
    with st.form("config_datajud"):
        token_atual = db.get_config('datajud_token', '')
        
        novo_token = st.text_input(
            "Token de API DataJud",
            value=token_atual,
            type="password",
            help="Cole aqui o token obtido no portal DataJud do CNJ",
            placeholder="Seu token de API..."
        )
        
        col_save, col_test = st.columns([1, 1])
        
        salvar = col_save.form_submit_button("💾 Salvar Token", type="primary", use_container_width=True)
        testar = col_test.form_submit_button("🧪 Testar Conexão", use_container_width=True)
        
        if salvar:
            if novo_token and novo_token.strip():
                db.set_config('datajud_token', novo_token.strip())
                db.audit("config_update", "Atualizou token DataJud")
                st.success("✅ Token salvo com sucesso!")
                st.rerun()
            else:
                st.error("❌ Token não pode estar vazio")
                
        if testar:
            if not novo_token or not novo_token.strip():
                st.error("❌ Configure um token primeiro")
            else:
                with st.spinner("Testando conexão com DataJud..."):
                    import datajud
                    sucesso, mensagem = datajud.testar_conexao(novo_token.strip())
                    
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
                        
    st.divider()
    
    # === INTEGRAÇÃO GOOGLE GEMINI (IA) ===
    st.markdown("### 🧠 Integração IA (Google Gemini)")
    st.caption("Configure a chave de API para habilitar a inteligência artificial jurídica")
    
    with st.expander("ℹ️ Como obter a API Key", expanded=False):
        st.markdown("""
        **Passo a passo:**
        1. Acesse: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
        2. Clique em "Create API key"
        3. Copie a chave (começa com AIza...)
        4. Cole no campo abaixo
        """)
    
    with st.form("config_gemini"):
        gemini_key_atual = db.get_config('gemini_api_key', '')
        # Mascarar key atual se existir
        placeholder_key = f"{gemini_key_atual[:4]}...{gemini_key_atual[-4:]}" if len(gemini_key_atual) > 10 else ""
        
        nova_gemini_key = st.text_input(
            "Gemini API Key",
            value=gemini_key_atual,
            type="password",
            help="Sua chave de API do Google AI Studio",
            placeholder="AIza..."
        )
        
        c_save_g, c_test_g = st.columns([1, 1])
        
        if c_save_g.form_submit_button("💾 Salvar Chave IA", type="primary", use_container_width=True):
            if nova_gemini_key and len(nova_gemini_key) > 20:
                db.set_config('gemini_api_key', nova_gemini_key.strip())
                db.audit("config_update", "Atualizou API Key do Gemini")
                st.success("✅ Chave salva com sucesso! Reinicie a página para aplicar.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Chave inválida")
                
        if c_test_g.form_submit_button("🧪 Testar IA", use_container_width=True):
            if not nova_gemini_key:
                st.error("Salve a chave primeiro")
            else:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=nova_gemini_key.strip())
                    model = genai.GenerativeModel('gemini-2.5-flash-lite')
                    resp = model.generate_content("Teste de conexão ok?")
                    st.success(f"✅ Conexão bem sucedida!")
                except Exception as e:
                    st.error(f"❌ Falha na conexão: {e}")

def render_usuarios(is_admin):
    st.markdown("### 👤 Gestão de Usuários")
    
    # Se for Admin, vê formulário de criação
    if is_admin:
        with st.expander("➕ Novo Usuário", expanded=False):
            with st.form("novo_usuario"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome Completo")
                user = c2.text_input("Nome de Usuário (Login)")
                c3, c4 = st.columns(2)
                senha = c3.text_input("Senha Inicial", type="password")
                role = c4.selectbox("Perfil", ["advogado", "admin", "secretaria"])
                
                if st.form_submit_button("Criar Usuário"):
                    if not user or not senha:
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        try:
                            senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                            db.sql_run("INSERT INTO usuarios (username, password_hash, nome, role) VALUES (?, ?, ?, ?)", 
                                       (user, senha_hash, nome, role))
                            
                            db.audit("user_create", f"Criou usuário '{user}' com perfil '{role}'")
                            st.success(f"Usuário {user} criado!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # --- LISTA DE USUÁRIOS INTERATIVA ---
    # Carregar dados
    if is_admin:
        df = db.sql_get("usuarios")
    else:
        df = db.sql_get_query("SELECT * FROM usuarios WHERE username = ?", (st.session_state.username,))
        
    if not df.empty:
        # Preparar DataFrame para exibição/edição
        # Mantemos o ID para updates, mas não mostramos se não quiser
        if is_admin:
             df['Excluir'] = False # Inicializar coluna de checkbox
        
        # Colunas editáveis para Admin
        # Username agora é editável para correções
        disabled_cols = ["id", "criado_em"]
        if not is_admin:
             disabled_cols = ["id", "username", "criado_em", "role", "ativo", "nome", "Excluir"] # Usuário não edita nada
             
        st.write("#### Lista de Usuários")
        if is_admin:
            st.info("💡 **Dica:** Para excluir, marque a caixinha na primeira coluna **'Excluir?'**. Um botão de confirmação aparecerá.")
        
        column_order = ["Excluir", "id", "nome", "username", "role", "ativo", "criado_em"] if is_admin else ["id", "nome", "username", "role", "ativo", "criado_em"]

        column_config = {
            "id": st.column_config.NumberColumn("ID", width="small", disabled=True),
            "nome": st.column_config.TextColumn("Nome Completo", width="medium"),
            "username": st.column_config.TextColumn("Usuário (Login)", width="small", help="Clique para editar o login"),
            "role": st.column_config.SelectboxColumn("Perfil", options=["admin", "advogado", "secretaria"], width="medium"),
            "ativo": st.column_config.CheckboxColumn("Ativo?", width="small"),
            "Excluir": st.column_config.CheckboxColumn("Excluir?", width="small"),
            "criado_em": st.column_config.TextColumn("Criado em", width="medium", disabled=True),
            "password_hash": None, 
            "pergunta_secreta": None,
            "resposta_secreta_hash": None,
            "email": None,
            "reset_token": None,
            "reset_expiry": None
        }
        
        # Exibir Editor
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            column_order=column_order,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=disabled_cols,
            key="user_editor"
        )
        
        # --- PROCESSAMENTO DE MUDANÇAS (APENAS ADMIN) ---
        if is_admin:
            # 1. Processar Exclusões via Checkbox
            users_to_delete = edited_df[edited_df['Excluir'] == True]
            
            if not users_to_delete.empty:
                st.error(f"⚠️ Atenção! Você selecionou {len(users_to_delete)} usuário(s) para exclusão.")
                
                # Listar quem será excluido
                for idx, row in users_to_delete.iterrows():
                    st.write(f"- {row['nome']} ({row['username']})")
                
                col_conf_del, col_cancel_del = st.columns([1, 4])
                
                if col_conf_del.button("Confirmar Exclusão 🗑️", type="primary"):
                     # Validar auto-exclusão
                    my_id_query = db.sql_get_query("SELECT id FROM usuarios WHERE username = ?", (st.session_state.username,))
                    my_id = my_id_query.iloc[0]['id'] if not my_id_query.empty else None
                    
                    deleted_count = 0
                    for idx, row in users_to_delete.iterrows():
                        if row['id'] == my_id:
                            st.warning(f"Você não pode excluir a si mesmo ({row['username']}). Ignorado.")
                        else:
                            db.sql_run("DELETE FROM usuarios WHERE id = ?", (int(row['id']),))
                            db.audit("user_delete_grid", f"Excluiu usuário ID {row['id']} ({row['username']})")
                            deleted_count += 1
                    
                    if deleted_count > 0:
                        st.success(f"{deleted_count} usuário(s) excluído(s) com sucesso!")
                        time.sleep(1)
                        st.rerun()

            # 2. Processar Edições (Nome, Role, Ativo)
            # Detectar mudanças comparando df original com edited_df (exceto coluna Excluir)
            # Como st.data_editor retorna o estado final, podemos iterar sobre edited_df e comparar com o estado no banco?
            # Ou confiar no session_state 'edited_rows' que é mais leve.
            
            changes = st.session_state.user_editor
            if changes.get('edited_rows'):
                processed_any = False
                for idx, alterations in changes['edited_rows'].items():
                    # idx é o indice da linha visual. 
                    # Se houver filtro ou sort, cuidado. Mas aqui estamos carregando puro.
                    # Vamos pegar o ID baseado no indice do DF original carregado no inicio
                    if idx in df.index:
                        user_id = df.iloc[idx]['id']
                        
                        updates = []
                        params = []
                        audit_details = []
                        
                        for col, new_val in alterations.items():
                            if col == 'Excluir': continue # Ignorar checkbox de exclusão aqui
                            
                            if col == 'ativo':
                                new_val = 1 if new_val else 0
                                
                            updates.append(f"{col} = ?")
                            params.append(new_val)
                            audit_details.append(f"{col} -> {new_val}")
                        
                        if updates:
                            params.append(int(user_id))
                            query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
                            db.sql_run(query, tuple(params))
                            db.audit("user_update_grid", f"Alterou usuário ID {user_id}: {', '.join(audit_details)}")
                            processed_any = True
                
                if processed_any:
                    st.toast("Dados atualizados!", icon="💾")
                    # Rerun apenas se não estivermos no meio do fluxo de exclusão (que tem seu proprio rerun)
                    # Para evitar loop se o usuario marcar excluir e editar ao mesmo tempo, 
                    # idealmente processamos edits, depois deletes.
                    if users_to_delete.empty:
                        time.sleep(0.5)
                        st.rerun()
                
        st.divider()
        
        # --- ALTERAÇÃO DE SENHA (FORA DA GRID) ---
        st.write("#### 🔐 Alterar Senha de Usuário")
        
        col_sel_pass, col_new_pass, col_btn_pass = st.columns([2, 2, 1])
        
        # Opções
        user_list = df['username'].tolist()
        target_user = col_sel_pass.selectbox("Selecionar Usuário", user_list, key="sel_pass_reset")
        new_pass_val = col_new_pass.text_input("Nova Senha", type="password", key="new_pass_input", placeholder="Mínimo 6 caracteres")
        
        if col_btn_pass.button("Atualizar Senha", type="primary"):
            if len(new_pass_val) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                 # Hash
                 hashed = bcrypt.hashpw(new_pass_val.encode(), bcrypt.gensalt()).decode()
                 db.sql_run("UPDATE usuarios SET password_hash = ? WHERE username = ?", (hashed, target_user))
                 db.audit("user_pass_reset", f"Alterou senha de '{target_user}'")
                 st.success(f"Senha de {target_user} atualizada!")
