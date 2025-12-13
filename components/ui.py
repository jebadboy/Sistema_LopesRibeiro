"""
Componentes de UI - Sprint 4

- load_css(): Carrega estilos globais
- toggle_theme(): Alterna entre tema claro/escuro
- get_theme(): Retorna tema atual
"""

import streamlit as st
import os

# CSS para tema escuro
DARK_THEME_CSS = """
<style>
    /* Tema Escuro */
    [data-theme="dark"] {
        --bg-primary: #1a1a2e;
        --bg-secondary: #16213e;
        --text-primary: #eaeaea;
        --text-secondary: #a0a0a0;
        --border-color: #2d3748;
    }
    
    .dark-mode {
        background-color: #1a1a2e !important;
        color: #eaeaea !important;
    }
    
    .dark-mode .stApp {
        background-color: #1a1a2e;
    }
    
    .dark-mode .stSidebar {
        background-color: #16213e !important;
    }
    
    .dark-mode .stTextInput > div > div > input {
        background-color: #2d3748 !important;
        color: #eaeaea !important;
        border-color: #4a5568 !important;
    }
    
    .dark-mode .stButton > button {
        background-color: #4a5568 !important;
        color: #eaeaea !important;
    }
    
    .dark-mode .stButton > button:hover {
        background-color: #5a6578 !important;
    }
    
    .dark-mode .stMarkdown, .dark-mode p, .dark-mode span {
        color: #eaeaea !important;
    }
    
    .dark-mode .metric-card {
        background-color: #16213e !important;
        color: #eaeaea !important;
    }
    
    .dark-mode .card-title {
        color: #a0a0a0 !important;
    }
    
    .dark-mode .card-value {
        color: #eaeaea !important;
    }
</style>
"""

def load_css():
    """Carrega o arquivo CSS global e aplica tema se necessário"""
    css_file = "styles.css"
    
    # Carregar CSS base
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Aplicar tema escuro se ativo
    if get_theme() == "dark":
        st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
        st.markdown('<div class="dark-mode">', unsafe_allow_html=True)

def get_theme() -> str:
    """Retorna tema atual (light ou dark)"""
    return st.session_state.get('theme', 'light')

def toggle_theme():
    """Alterna entre tema claro e escuro"""
    current = get_theme()
    new_theme = 'dark' if current == 'light' else 'light'
    st.session_state.theme = new_theme
    return new_theme

def render_theme_toggle():
    """Renderiza toggle de tema na sidebar"""
    current = get_theme()
    icon = "🌙" if current == "light" else "☀️"
    label = "Modo Escuro" if current == "light" else "Modo Claro"
    
    if st.button(f"{icon} {label}", key="theme_toggle", use_container_width=True):
        toggle_theme()
        st.rerun()

def toast_success(message: str):
    """Exibe toast de sucesso"""
    st.toast(f"✅ {message}", icon="✅")

def toast_error(message: str):
    """Exibe toast de erro"""
    st.toast(f"❌ {message}", icon="❌")

def toast_warning(message: str):
    """Exibe toast de aviso"""
    st.toast(f"⚠️ {message}", icon="⚠️")

def toast_info(message: str):
    """Exibe toast informativo"""
    st.toast(f"ℹ️ {message}", icon="ℹ️")

