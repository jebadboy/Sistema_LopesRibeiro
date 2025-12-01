import streamlit as st
import database as db
import pandas as pd
import hashlib

import os

def render():
    st.markdown("<h1 style='color: var(--text-main);'>⚙️ Administração</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👥 Usuários", "🏢 Configurações"])
    
    with tab1:
        render_usuarios()
    
    with tab2:
        st.markdown("### 🏢 Dados do Escritório")
        st.caption("Essas informações aparecerão automaticamente nos documentos gerados (Propostas, Procurações, etc).")
        
        # Upload de Logo
        st.markdown("#### Logotipo")
        col_logo_curr, col_logo_up = st.columns([1, 2])
        
        logo_path = "LOGO.jpg" # Padrão ou salvo
        if os.path.exists(logo_path):
            col_logo_curr.image(logo_path, caption="Logo Atual", width=150)
        else:
            col_logo_curr.info("Sem logo definido")
            
        uploaded_logo = col_logo_up.file_uploader("Alterar Logotipo (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_logo is not None:
            try:
                with open(logo_path, "wb") as f:
                    f.write(uploaded_logo.getbuffer())
                st.success("Logotipo atualizado com sucesso! Recarregue a página para ver.")
            except Exception as e:
                st.error(f"Erro ao salvar logo: {e}")
        
        st.markdown("---")
        
        with st.form("config_escritorio"):
            c1, c2 = st.columns(2)
            nome_escritorio = c1.text_input("Nome do Escritório", value=db.get_config('nome_escritorio', 'Lopes & Ribeiro Advogados'))
            nome_adv = c2.text_input("Nome do Advogado(a) (Para Relatórios)", value=db.get_config('nome_advogado_relatorios', 'Dra. Sheila Lopes'))
            
            oab = st.text_input("OAB", value=db.get_config('oab', 'OAB/RJ nº 215691'))
            
            end = st.text_input("Endereço Completo", value=db.get_config('endereco_escritorio', 'Rodovia Amaral Peixoto km 22, nº 5, São José do Imbassaí, Maricá/RJ'))
            
            c3, c4 = st.columns(2)
            tel = c3.text_input("Telefone / WhatsApp", value=db.get_config('telefone_escritorio', '(21) 97032-0748'))
            email = c4.text_input("Email de Contato", value=db.get_config('email_escritorio', 'sheilaadv.contato@gmail.com'))
            
            st.markdown("---")
            st.markdown("### 📄 Links de Modelos (Google Drive)")
            l1, l2 = st.columns(2)
            link_proc = l1.text_input("Link Modelo Procuração", value=db.get_config('link_modelo_procuracao', ''))
            link_hipo = l2.text_input("Link Modelo Hipossuficiência", value=db.get_config('link_modelo_hipossuficiencia', ''))
            
            if st.form_submit_button("Salvar Configurações", type="primary"):
                try:
                    db.set_config('nome_escritorio', nome_escritorio)
                    db.set_config('nome_advogado_relatorios', nome_adv)
                    db.set_config('oab', oab)
                    db.set_config('endereco_escritorio', end)
                    db.set_config('telefone_escritorio', tel)
                    db.set_config('email_escritorio', email)
                    db.set_config('link_modelo_procuracao', link_proc)
                    db.set_config('link_modelo_hipossuficiencia', link_hipo)
                    st.success("Configurações atualizadas com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

def render_usuarios():
    st.markdown("### Gestão de Usuários")
    
    # Formulário de Novo Usuário
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
                    st.error("Usuário e Senha são obrigatórios.")
                else:
                    try:
                        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
                        db.sql_run("INSERT INTO usuarios (username, password_hash, nome, role) VALUES (?, ?, ?, ?)", 
                                   (user, senha_hash, nome, role))
                        st.success(f"Usuário {user} criado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar usuário: {e}")

    # Listagem de Usuários
    df = db.sql_get("usuarios")
    if not df.empty:
        # Ocultar hash da senha
        df_show = df[['id', 'nome', 'username', 'role', 'ativo', 'criado_em']].copy()
        
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        
        # Edição simples (Reset de Senha / Status)
        st.markdown("#### Editar Usuário")
        col_sel, col_acao = st.columns([2, 1])
        
        user_id = col_sel.selectbox("Selecione o Usuário", df['username'].tolist())
        usuario = df[df['username'] == user_id].iloc[0]
        
        with st.form("editar_usuario"):
            st.write(f"Editando: **{usuario['nome']}** ({usuario['role']})")
            nova_senha = st.text_input("Nova Senha (deixe em branco para manter)", type="password")
            novo_status = st.checkbox("Ativo", value=bool(usuario['ativo']))
            
            if st.form_submit_button("Salvar Alterações"):
                try:
                    if nova_senha:
                        senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
                        db.sql_run("UPDATE usuarios SET password_hash=?, ativo=? WHERE id=?", 
                                   (senha_hash, int(novo_status), int(usuario['id'])))
                        st.success("Senha e status atualizados.")
                    else:
                        db.sql_run("UPDATE usuarios SET ativo=? WHERE id=?", 
                                   (int(novo_status), int(usuario['id'])))
                        st.success("Status atualizado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")
