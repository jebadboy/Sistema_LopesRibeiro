import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📄 Automação de Documentos</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 Gerador de Documentos", "⚙️ Gerenciar Modelos"])
    
    # --- ABA 1: GERADOR ---
    with tab1:
        st.markdown("### Gerar Novo Documento")
        
        col1, col2 = st.columns(2)
        with col1:
            # Selecionar Cliente
            df_clientes = db.sql_get("clientes", "nome")
            opcoes_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
            cliente_selecionado = st.selectbox("Selecione o Cliente", [""] + opcoes_clientes)
            
        with col2:
            # Selecionar Modelo
            df_modelos = db.sql_get("modelos_documentos", "titulo")
            opcoes_modelos = df_modelos['titulo'].tolist() if not df_modelos.empty else []
            modelo_selecionado = st.selectbox("Selecione o Modelo", [""] + opcoes_modelos)
            
        if cliente_selecionado and modelo_selecionado:
            # Buscar dados
            dados_cliente = df_clientes[df_clientes['nome'] == cliente_selecionado].iloc[0].to_dict()
            id_modelo = df_modelos[df_modelos['titulo'] == modelo_selecionado].iloc[0]['id']
            
            # Gerar Preview
            if st.button("Gerar Preview", type="primary"):
                texto_gerado = db.gerar_documento_final(id_modelo, dados_cliente)
                
                st.markdown("---")
                st.markdown("### 👁️ Visualização")
                st.text_area("Conteúdo Gerado (Copie e Cole no Word)", value=texto_gerado, height=400)
                st.success("Documento gerado com sucesso! Copie o texto acima.")

    # --- ABA 2: GERENCIAR MODELOS ---
    with tab2:
        st.markdown("### Meus Modelos")
        
        with st.expander("➕ Criar Novo Modelo"):
            with st.form("novo_modelo"):
                titulo = st.text_input("Título do Modelo (ex: Procuração Geral)")
                categoria = st.selectbox("Categoria", ["Procuração", "Contrato", "Petição", "Declaração", "Outros"])
                
                with st.expander("ℹ️ Ver códigos (variáveis) disponíveis"):
                    st.markdown("""
                    **Copie e cole estes códigos no seu texto:**
                    * `{nome}` : Nome do Cliente
                    * `{nacionalidade}` : Nacionalidade
                    * `{estado_civil}` : Estado Civil
                    * `{profissao}` : Profissão
                    * `{cpf}` : CPF/CNPJ
                    * `{rg}` : RG
                    * `{endereco}` : Endereço Completo
                    * `{cidade}` : Cidade
                    * `{estado}` : Estado
                    """)
                conteudo = st.text_area("Conteúdo do Modelo", height=300, placeholder="Eu, {nome}, portador do CPF {cpf}...")
                
                if st.form_submit_button("Salvar Modelo"):
                    if titulo and conteudo:
                        db.salvar_modelo_documento(titulo, categoria, conteudo)
                        st.success("Modelo salvo com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha título e conteúdo.")
        
        # Listar Modelos Existentes
        df_modelos = db.sql_get("modelos_documentos", "titulo")
        if not df_modelos.empty:
            st.dataframe(df_modelos[['titulo', 'categoria', 'criado_em']], use_container_width=True)
            
            # Opção de Excluir
            modelo_excluir = st.selectbox("Selecione para Excluir", [""] + df_modelos['titulo'].tolist())
            if modelo_excluir:
                if st.button("🗑️ Excluir Modelo", type="secondary"):
                    id_excluir = df_modelos[df_modelos['titulo'] == modelo_excluir].iloc[0]['id']
                    db.excluir_modelo_documento(id_excluir)
                    st.success("Modelo excluído.")
                    st.rerun()
        else:
            st.info("Nenhum modelo cadastrado.")
