import database as db
import sys

try:
    print("Testing db.get_config...")
    link_proc = db.get_config('link_modelo_procuracao')
    link_hipo = db.get_config('link_modelo_hipossuficiencia')
    print(f"Link Procuracao: {link_proc}")
    print(f"Link Hipo: {link_hipo}")
    print("db.get_config works!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
