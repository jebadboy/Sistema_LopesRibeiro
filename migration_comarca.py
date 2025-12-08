import database as db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    print("Iniciando migração de Comarca...")
    
    # 1. Adicionar coluna 'comarca' em 'processos'
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se coluna já existe
            cursor.execute("PRAGMA table_info(processos)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'comarca' not in columns:
                print("Adicionando coluna 'comarca'...")
                cursor.execute("ALTER TABLE processos ADD COLUMN comarca TEXT")
                conn.commit()
                print("Sucesso!")
            else:
                print("Coluna 'comarca' já existe.")
                
    except Exception as e:
        print(f"Erro na migração: {e}")

if __name__ == "__main__":
    db.init_db()
    migrate()
