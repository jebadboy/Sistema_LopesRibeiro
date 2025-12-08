import streamlit as st
import os

def load_css():
    """Carrega o arquivo CSS global"""
    css_file = "styles.css"
    
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("Arquivo de estilos (styles.css) não encontrado.")
