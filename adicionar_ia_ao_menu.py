"""
Script para adicionar IA ao menu do app.py
"""
import re

# Ler arquivo
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Adicionar import do ia_juridica
content = content.replace(
    'from modules import clientes, financeiro, processos, dashboard, admin, relatorios, ajuda, agenda',
    'from modules import clientes, financeiro, processos, dashboard, admin, relatorios, ajuda, agenda, ia_juridica'
)

# Adicionar ao menu
old_menu = '''        menu_options = {
            "Painel Geral": dashboard,
            "Clientes (CRM)": clientes,
            "Processos": processos,
            "📅 Agenda": agenda,
            "Financeiro": financeiro,
            "Relatórios": relatorios,
            "📚 Ajuda": ajuda
        }'''

new_menu = '''        menu_options = {
            "Painel Geral": dashboard,
            "Clientes (CRM)": clientes,
            "Processos": processos,
            "📅 Agenda": agenda,
            "Financeiro": financeiro,
            "🤖 IA Jurídica": ia_juridica,
            "Relatórios": relatorios,
            "📚 Ajuda": ajuda
        }'''

content = content.replace(old_menu, new_menu)

# Salvar
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py atualizado com sucesso!")
print("✅ Módulo IA Jurídica adicionado ao menu")
