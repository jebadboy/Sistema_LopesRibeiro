# Arquivo MANUAL de instruções para for remoção completa do módulo IA
# Devido a problemas com edições automáticas, aplique manualmente:

# ==================================================
# PASSO 1: app.py - Remover menu "IA Jurídica"
# ==================================================

# Localização: Linha ~76
# SUBSTITUIR:
#     menu = st.radio("📋 Menu Principal", 
#                     ["Clientes", "Financeiro", "Processos", "Agenda", "IA Jurídica", "Painel Geral"])
#
# POR:
#     menu = st.radio("📋 Menu Principal", 
#                     ["Clientes", "Financeiro", "Processos", "Agenda", "Painel Geral"])

# ==================================================
# PASSO 2: app.py - Remover seção elif IA Jurídica
# ==================================================

# Localização: Linhas ~527-547
# APAGUE todo o bloco:
# elif menu == "IA Jurídica":
#     st.title("🤖 Assistente Jurídico (Gemini)")
#     
#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []
#     
#     for msg in st.session_state.chat_history:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])
#             
#     if prompt := st.chat_input("Digite sua dúvida jurídica..."):
#         st.session_state.chat_history.append({"role": "user", "content": prompt})
#         with st.chat_message("user"):
#             st.markdown(prompt)
#             
#         with st.chat_message("assistant"):
#             with st.spinner("Pensando..."):
#                 resp = ut.consultar_ia(prompt)
#                 st.markdown(resp)
#                 st.session_state.chat_history.append({"role": "assistant", "content": resp})

# ==================================================
# PASSO 3: utils.py - Remover imports e dependências IA
# ==================================================

# Localização: Início do arquivo (linhas ~2, ~8, ~14)
# APAGUE estas linhas:
# import google.generativeai as genai
# from dotenv import load_dotenv
# import concurrent.futures

# APAGUE também (linhas ~16-17):
# load_dotenv()
# API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY")

# ==================================================
# PASSO 4: utils.py - Remover funções de IA
# ==================================================

# Localização: Linhas ~163-186
# APAGUE toda a função obter_modelo_ativo():
# def obter_modelo_ativo():
#     try:
#         genai.configure(api_key=API_KEY_GEMINI)
#         return 'gemini-flash-latest'
#     except: return 'gemini-flash-latest'

# Localização: Linhas ~163-186
# APAGUE toda a função consultar_ia():
# def consultar_ia(prompt, timeout=30):
#     ... (toda a função até o return final)

# ==================================================
# PASSO 5: requirements.txt - Remover dependências
# ==================================================

# APAGUE estas linhas (se existirem):
# google-generativeai
# python-dotenv

# ==================================================
# PASSO 6: Testar
# ==================================================

# Execute:
# python -c "import app; print('OK')"

# Se funcionar, faça commit:
# git add .
# git commit -m "Removido módulo IA Jurídica manualmente"

print("Instruções de remoção manual criadas.")
print("Aplique cada passo com cuidado no seu editor de código.")
