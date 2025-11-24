import re

# Ler app.py original
with open('app.py', 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Dividir em linhas para análise
linhas = conteudo.split('\n')

# Identificar a linha onde começa o bloco orfao (linha 40, indice 39)
# e onde ele termina (linha 85, indice 84)

# Criar novo conteudo removendo linhas 40-85 (indices 39-84)
novas_linhas = linhas[:39] + linhas[85:]

# No lugar do bloco removido, adicionar menu
menu_codigo = """
# --- MENU PRINCIPAL (SIDEBAR) ---
menu = st.sidebar.radio("Menu", ["Comercial", "Financeiro", "Processos", "Agenda", "IA Jurídica", "Painel Geral"])

# ==========================================
# 1. COMERCIAL
# ==========================================
if menu == "Comercial":
    st.title("Comercial")
    t1, t2, t3, t4 = st.tabs(["Cadastro", "Clientes", "Funil de Vendas", "Modelos de Proposta"])
    
    with t1:
        st.info("Em desenvolvimento: Cadastro de Clientes")
    
    with t2:
        st.info("Em desenvolvimento: Listagem de Clientes")
    
    with t3:"""

# Inserir menu logo após a linha 39
linhas_final = novas_linhas[:39] + menu_codigo.strip().split('\n') + ['\n'] + novas_linhas[39:]

# Salvar
with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(linhas_final))

print("Arquivo app.py corrigido com sucesso!")
print(f"Linhas removidas: 46 (bloco orfao)")
print(f"Linhas adicionadas: {len(menu_codigo.strip().split(chr(10)))}")
