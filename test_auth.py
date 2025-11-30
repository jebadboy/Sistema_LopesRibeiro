import database as db
import hashlib
import os

# Configurar ambiente de teste
db.DB_NAME = 'test_dados_escritorio_auth.db'
if os.path.exists(db.DB_NAME):
    os.remove(db.DB_NAME)

def test_auth_flow():
    print("Testando fluxo de autenticação...")
    
    # 1. Inicializar Banco (deve criar admin padrão)
    try:
        db.init_db()
        print("Banco inicializado.")
    except Exception as e:
        print(f"Erro ao inicializar: {e}")
        return False
        
    # 2. Verificar Admin Padrão
    df = db.sql_get("usuarios")
    print(f"\nUsuários encontrados: {len(df)}")
    if len(df) == 1 and df.iloc[0]['username'] == 'admin':
        print("Usuário admin padrão criado com sucesso.")
    else:
        print("FALHA: Usuário admin padrão não encontrado.")
        return False
        
    # 3. Testar Login (Simulação)
    username = "admin"
    password = "admin123"
    senha_hash = hashlib.sha256(password.encode()).hexdigest()
    
    user_data = df[df['username'] == username].iloc[0]
    if user_data['password_hash'] == senha_hash:
        print("Login simulado: SUCESSO")
    else:
        print("Login simulado: FALHA (Hash incorreto)")
        return False
        
    # 4. Testar Criação de Novo Usuário (CRUD Admin)
    print("\nTestando criação de usuário via SQL (simulando admin.py)...")
    novo_user = "advogado1"
    nova_senha = hashlib.sha256("senha123".encode()).hexdigest()
    
    try:
        db.sql_run("INSERT INTO usuarios (username, password_hash, nome, role) VALUES (?, ?, ?, ?)", 
                   (novo_user, nova_senha, "Advogado Teste", "advogado"))
        print("Novo usuário inserido.")
    except Exception as e:
        print(f"Erro ao inserir usuário: {e}")
        return False
        
    df_novo = db.sql_get("usuarios")
    if len(df_novo) == 2:
        print("CRUD Usuários: SUCESSO")
        return True
    else:
        print("CRUD Usuários: FALHA")
        return False

if __name__ == "__main__":
    test_auth_flow()
    
    # Limpar
    if os.path.exists(db.DB_NAME):
        os.remove(db.DB_NAME)
