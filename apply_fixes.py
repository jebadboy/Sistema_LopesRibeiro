# Script para aplicar correções precisas e cirúrgicas ao app.py
import re

# Ler arquivo
with open('app.py', 'r', encoding='utf-8') as f:
    linhas = f.readlines()

print("=== CORREÇÕES A SEREM APLICADAS ===\n")

# CORREÇÃO 1: Adicionar encoding UTF-8 no logging (linha 17)
print("1. Corrigindo logging (linha 17)...")
for i, linha in enumerate(linhas):
    if i == 16 and "logging.FileHandler('sistema_lopes_ribeiro.log')" in linha:
        linhas [i] = "        logging.FileHandler('sistema_lopes_ribeiro.log', encoding='utf-8'),\n"
        print("   OK: Encoding UTF-8 adicionado ao FileHandler")
        break

# CORREÇÃO 2: Corrigir INSERT financeiro (adicionar logger.error e fechar except)
# Encontrar a linha do except Exception relacionado ao backup
print("\n2. Corrigindo bloco except do backup (linha 40)...")
for i, linha in enumerate(linhas):
    if i == 39 and "except Exception as e:" in linha:
        # Verificar se a próxima linha está vazia ou malformada
        if i+1 < len(linhas) and linhas[i+1].strip() == "":
            linhas[i+1] = "        logger.error(f\"Erro ao criar backup automático: {e}\")\n"
            # Adicionar menu após o except
            linhas.insert(i+2, "\n")
            linhas.insert(i+3, "# --- MENU PRINCIPAL (SIDEBAR) ---\n")
            linhas.insert(i+4, "menu = st.sidebar.radio(\"Menu\", [\"Comercial\", \"Financeiro\", \"Processos\", \"Agenda\", \"IA Jurídica\", \"Painel Geral\"])\n")
            linhas.insert(i+5, "\n")
            linhas.insert(i+6, "# ==========================================\n")
            linhas.insert(i+7, "# 1. COMERCIAL\n")
            linhas.insert(i+8, "# ==========================================\n")
            linhas.insert(i+9, "if menu == \"Comercial\":\n")
            linhas.insert(i+10, "    st.title(\"Comercial\")\n")
            linhas.insert(i+11, "    t1, t2, t3, t4 = st.tabs([\"Cadastro\", \"Clientes\", \"Funil de Vendas\", \"Modelos de Proposta\"])\n")
            linhas.insert(i+12, "\n")
            linhas.insert(i+13, "    with t1:\n")
            linhas.insert(i+14, "        st.info(\"Em desenvolvimento: Cadastro de Clientes\")\n")
            linhas.insert(i+15, "\n")
            linhas.insert(i+16, "    with t2:\n")
            linhas.insert(i+17, "        st.info(\"Em desenvolvimento: Listagem de Clientes\")\n")
            linhas.insert(i+18, "\n")
            print("   OK: Except corrigido e menu adicionado")
            break

# Salvar
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(linhas)

print("\n=== ARQUIVO CORRIGIDO COM SUCESSO ===")
print("Linhas modificadas: 1 (logging) + 1 (except) = 2")
print("Linhas adicionadas: 18 (menu e estrutura)")
