import database as db

print("Verificando campos de configuração...")

# 1. Definir links de teste
link_proc = "https://drive.google.com/test_proc"
link_hipo = "https://drive.google.com/test_hipo"

print(f"Definindo link_modelo_procuracao = {link_proc}")
db.set_config('link_modelo_procuracao', link_proc)

print(f"Definindo link_modelo_hipossuficiencia = {link_hipo}")
db.set_config('link_modelo_hipossuficiencia', link_hipo)

# 2. Ler links
recuperado_proc = db.get_config('link_modelo_procuracao')
recuperado_hipo = db.get_config('link_modelo_hipossuficiencia')

print(f"Recuperado Procuração: {recuperado_proc}")
print(f"Recuperado Hipo: {recuperado_hipo}")

if recuperado_proc == link_proc and recuperado_hipo == link_hipo:
    print("SUCESSO: Configurações salvas e recuperadas corretamente.")
else:
    print("FALHA: Erro na persistência das configurações.")

# 3. Limpar (opcional, mas bom para não sujar o banco real com lixo)
# db.set_config('link_modelo_procuracao', '')
# db.set_config('link_modelo_hipossuficiencia', '')
