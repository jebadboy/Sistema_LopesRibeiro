"""
Módulo de Gerenciamento do Google Drive

Interface visual para:
- Listar arquivos por cliente/processo
- Download de documentos
- Upload manual de arquivos
- Preview de PDFs
"""

import streamlit as st
import database as db
import google_drive as gd
from datetime import datetime
import os
import tempfile


def render():
    st.markdown("## 📁 Google Drive")
    st.caption("Gestão de documentos no Google Drive da equipe")
    
    # Verificar conexão
    service = gd.autenticar()
    if not service:
        st.error("❌ Não foi possível conectar ao Google Drive")
        st.info("""
        **Possíveis causas:**
        - Arquivo `service_account.json` não encontrado
        - Token OAuth expirado
        - Credenciais inválidas
        
        Contate o administrador para configurar a integração.
        """)
        return
    
    st.success("✅ Conectado ao Google Drive")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📂 Navegação", "⬆️ Upload", "⚙️ Configurações"])
    
    with tab1:
        render_navegacao(service)
    
    with tab2:
        render_upload(service)
    
    with tab3:
        render_config()


def render_navegacao(service):
    """Navegação e listagem de arquivos"""
    st.markdown("### 📂 Arquivos no Drive")
    
    # Seletor de contexto
    col1, col2 = st.columns(2)
    
    with col1:
        # Listar clientes
        clientes = db.sql_get("clientes")
        cliente_opts = ["-- Selecione --"] + clientes['nome'].tolist() if not clientes.empty else ["-- Sem clientes --"]
        cliente_sel = st.selectbox("Filtrar por Cliente", cliente_opts)
    
    with col2:
        # Listar processos do cliente selecionado
        if cliente_sel and cliente_sel != "-- Selecione --" and cliente_sel != "-- Sem clientes --":
            processos = db.sql_get_query(
                "SELECT numero, acao FROM processos WHERE cliente_nome = ?",
                (cliente_sel,)
            )
            proc_opts = ["Todos"] + [f"{r['numero']} - {r['acao'][:30]}" for _, r in processos.iterrows()] if not processos.empty else ["-- Sem processos --"]
            proc_sel = st.selectbox("Filtrar por Processo", proc_opts)
        else:
            proc_sel = None
    
    # Pasta a listar
    pasta_id = gd.PASTA_ALVO_ID  # Pasta raiz configurada
    
    # Se cliente selecionado, buscar pasta do cliente
    if cliente_sel and cliente_sel != "-- Selecione --" and cliente_sel != "-- Sem clientes --":
        pasta_cliente = gd.find_folder(service, cliente_sel, pasta_id)
        if pasta_cliente:
            pasta_id = pasta_cliente
            st.info(f"📁 Pasta do cliente: **{cliente_sel}**")
        else:
            st.warning(f"Pasta do cliente '{cliente_sel}' não encontrada no Drive. Será criada no primeiro upload.")
    
    # Listar arquivos
    if pasta_id:
        arquivos = gd.listar_arquivos(service, pasta_id)
        
        if arquivos:
            st.markdown(f"**{len(arquivos)} arquivo(s) encontrado(s)**")
            
            for arq in arquivos:
                with st.container(border=True):
                    col_icon, col_info, col_actions = st.columns([1, 4, 2])
                    
                    with col_icon:
                        # Ícone por tipo
                        mime = arq.get('mimeType', '')
                        if 'folder' in mime:
                            st.markdown("📁")
                        elif 'pdf' in mime:
                            st.markdown("📄")
                        elif 'image' in mime:
                            st.markdown("🖼️")
                        elif 'spreadsheet' in mime or 'excel' in mime:
                            st.markdown("📊")
                        elif 'document' in mime or 'word' in mime:
                            st.markdown("📝")
                        else:
                            st.markdown("📎")
                    
                    with col_info:
                        st.markdown(f"**{arq['name']}**")
                        created = arq.get('createdTime', '')[:10] if arq.get('createdTime') else ''
                        st.caption(f"Criado: {created}")
                    
                    with col_actions:
                        # Link para abrir no Drive
                        if arq.get('webViewLink'):
                            st.link_button("🔗 Abrir", arq['webViewLink'], use_container_width=True)
                        
                        # Botão de download (para pastas, entrar nela)
                        if 'folder' in mime:
                            if st.button("📂 Abrir", key=f"open_{arq['id']}", use_container_width=True):
                                st.session_state.drive_pasta_atual = arq['id']
                                st.rerun()
        else:
            st.info("📭 Nenhum arquivo encontrado nesta pasta.")
    
    # Botão para voltar à pasta raiz
    if st.session_state.get('drive_pasta_atual') and st.session_state.drive_pasta_atual != gd.PASTA_ALVO_ID:
        if st.button("⬆️ Voltar para pasta raiz"):
            st.session_state.drive_pasta_atual = gd.PASTA_ALVO_ID
            st.rerun()


def render_upload(service):
    """Upload de arquivos para o Drive"""
    st.markdown("### ⬆️ Upload de Arquivo")
    
    # Seletor de destino
    col1, col2 = st.columns(2)
    
    with col1:
        clientes = db.sql_get("clientes")
        cliente_opts = ["-- Pasta Raiz --"] + clientes['nome'].tolist() if not clientes.empty else ["-- Pasta Raiz --"]
        cliente_dest = st.selectbox("Pasta de Destino (Cliente)", cliente_opts, key="upload_cliente")
    
    with col2:
        if cliente_dest and cliente_dest != "-- Pasta Raiz --":
            processos = db.sql_get_query(
                "SELECT numero, acao FROM processos WHERE cliente_nome = ?",
                (cliente_dest,)
            )
            proc_opts = ["-- Pasta do Cliente --"] + [r['numero'] for _, r in processos.iterrows()] if not processos.empty else ["-- Pasta do Cliente --"]
            proc_dest = st.selectbox("Subpasta (Processo)", proc_opts, key="upload_proc")
        else:
            proc_dest = None
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Selecione o arquivo",
        type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'txt'],
        key="drive_uploader"
    )
    
    if uploaded_file:
        st.info(f"📎 Arquivo selecionado: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("📤 Enviar para o Drive", type="primary", use_container_width=True):
            with st.spinner("Enviando arquivo..."):
                try:
                    # Determinar pasta de destino
                    pasta_destino = gd.PASTA_ALVO_ID
                    
                    if cliente_dest and cliente_dest != "-- Pasta Raiz --":
                        # Criar/encontrar pasta do cliente
                        pasta_cliente = gd.find_folder(service, cliente_dest, pasta_destino)
                        if not pasta_cliente:
                            pasta_cliente = gd.create_folder(service, cliente_dest, pasta_destino)
                        pasta_destino = pasta_cliente
                        
                        # Se tem processo, criar subpasta
                        if proc_dest and proc_dest != "-- Pasta do Cliente --":
                            pasta_proc = gd.find_folder(service, proc_dest, pasta_destino)
                            if not pasta_proc:
                                pasta_proc = gd.create_folder(service, proc_dest, pasta_destino)
                            pasta_destino = pasta_proc
                    
                    # Salvar arquivo temporário
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    # Upload
                    file_id, link = gd.upload_file(service, tmp_path, pasta_destino)
                    
                    # Remover temp
                    os.unlink(tmp_path)
                    
                    if file_id:
                        st.success(f"✅ Arquivo enviado com sucesso!")
                        st.markdown(f"🔗 [Abrir no Drive]({link})")
                        
                        # Registrar no audit
                        db.audit(f"Upload Drive: {uploaded_file.name}")
                    else:
                        st.error("❌ Falha no upload. Verifique as permissões.")
                        
                except Exception as e:
                    st.error(f"❌ Erro: {e}")


def render_config():
    """Configurações do Drive"""
    st.markdown("### ⚙️ Configurações")
    
    # Mostrar pasta raiz configurada
    st.info(f"📁 Pasta raiz configurada: `{gd.PASTA_ALVO_ID}`")
    
    # Opção para alterar (apenas admin)
    if st.session_state.get('role') == 'admin':
        with st.expander("Alterar Pasta Raiz"):
            nova_pasta = st.text_input(
                "ID da nova pasta raiz",
                value=gd.PASTA_ALVO_ID,
                help="Encontre o ID na URL da pasta no Google Drive"
            )
            
            if st.button("Salvar"):
                db.set_config('drive_pasta_raiz', nova_pasta)
                st.success("Configuração salva! Reinicie o sistema para aplicar.")
    
    # Status da conexão
    st.markdown("### 📊 Status")
    
    service = gd.autenticar()
    if service:
        st.success("✅ Autenticação OK")
        
        # Tentar listar pasta raiz
        try:
            arquivos = gd.listar_arquivos(service, gd.PASTA_ALVO_ID)
            st.success(f"✅ Pasta raiz acessível ({len(arquivos)} itens)")
        except Exception as e:
            st.warning(f"⚠️ Pasta raiz não acessível: {e}")
    else:
        st.error("❌ Autenticação falhou")
        
        # Dicas de debug
        st.markdown("""
        **Verificações:**
        - [ ] Arquivo `service_account.json` existe
        - [ ] Pasta compartilhada com a Service Account
        - [ ] Escopos corretos (drive)
        """)
