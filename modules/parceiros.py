import streamlit as st
import database as db
import pandas as pd
from datetime import datetime
import utils as ut
import re

def render():
    st.markdown("<h1 style='color: var(--text-main);'>🤝 Gestão de Parceiros</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Parceiros", "➕ Novo Parceiro"])
    
    with tab1:
        render_lista_parceiros()
        
    with tab2:
        render_novo_parceiro()

def render_lista_parceiros():
    df = db.sql_get("parceiros")
    
    if df.empty:
        st.info("Nenhum parceiro cadastrado.")
        return
        
    for index, row in df.iterrows():
        with st.expander(f"{row['nome']} ({row['email'] or 'Sem email'})"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**CPF/CNPJ:** {row['cpf_cnpj']}")
                st.write(f"**Telefone:** {row['telefone']}")
                st.write(f"**Chave PIX:** {row['chave_pix']}")
            with c2:
                st.write(f"**Dados Bancários:** {row['dados_bancarios']}")
                st.write(f"**Status:** {'Ativo' if row['ativo'] else 'Inativo'}")
                
            if st.button("🗑️ Excluir", key=f"del_parc_{row['id']}"):
                db.crud_delete("parceiros", "id = ?", (row['id'],), f"Exclusão de parceiro {row['nome']}")
                st.rerun()

def render_novo_parceiro():
    st.markdown("### Cadastrar Novo Parceiro")
    
    with st.form("form_novo_parceiro"):
        nome = st.text_input("Nome Completo *")
        c1, c2 = st.columns(2)
        cpf_cnpj = c1.text_input("CPF/CNPJ")
        email = c2.text_input("Email")
        
        c3, c4 = st.columns(2)
        telefone = c3.text_input("Telefone")
        chave_pix = c4.text_input("Chave PIX")
        
        dados_bancarios = st.text_area("Dados Bancários (Banco, Agência, Conta)")
        
        submitted = st.form_submit_button("Salvar Parceiro", type="primary")
        
        if submitted:
            if not nome:
                st.error("Nome é obrigatório.")
            elif email and not ut.validar_email(email):
                st.error("E-mail inválido.")
            else:
                # Formatações
                cpf_cnpj_fmt = ut.formatar_documento(cpf_cnpj)
                telefone_fmt = ut.formatar_celular(telefone)
                
                dados = {
                    "nome": nome,
                    "cpf_cnpj": cpf_cnpj_fmt,
                    "email": email,
                    "telefone": telefone_fmt,
                    "chave_pix": chave_pix,
                    "dados_bancarios": dados_bancarios,
                    "ativo": 1
                }
                db.crud_insert("parceiros", dados, f"Novo parceiro: {nome}")
                st.success("Parceiro cadastrado com sucesso!")
                st.rerun()
