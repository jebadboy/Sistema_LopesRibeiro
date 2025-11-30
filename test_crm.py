import database as db
import sqlite3
import os

# Configurar ambiente de teste
db.DB_NAME = 'test_dados_escritorio.db'
if os.path.exists(db.DB_NAME):
    os.remove(db.DB_NAME)

def test_init_db():
    print("Testando inicialização do banco de dados...")
    try:
        db.init_db()
        print("Banco de dados inicializado com sucesso.")
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")
        return False
    
    # Verificar se a coluna tipo_pessoa existe na tabela clientes
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(clientes)")
        columns = [col[1] for col in c.fetchall()]
        if 'tipo_pessoa' in columns:
            print("Coluna 'tipo_pessoa' encontrada na tabela 'clientes'.")
        else:
            print("ERRO: Coluna 'tipo_pessoa' NÃO encontrada na tabela 'clientes'.")
            return False
            
    return True

def test_crud_cliente():
    print("\nTestando CRUD de clientes...")
    
    # Inserir Pessoa Física
    cliente_pf = {
        'nome': 'João Silva',
        'tipo_pessoa': 'Física',
        'cpf_cnpj': '12345678901',
        'status_cliente': 'ATIVO'
    }
    
    try:
        id_pf = db.crud_insert('clientes', cliente_pf, 'Teste PF')
        print(f"Cliente PF inserido com ID: {id_pf}")
    except Exception as e:
        print(f"Erro ao inserir Cliente PF: {e}")
        return False

    # Inserir Pessoa Jurídica
    cliente_pj = {
        'nome': 'Empresa XYZ Ltda',
        'tipo_pessoa': 'Jurídica',
        'cpf_cnpj': '12345678000199',
        'status_cliente': 'EM NEGOCIAÇÃO'
    }
    
    try:
        id_pj = db.crud_insert('clientes', cliente_pj, 'Teste PJ')
        print(f"Cliente PJ inserido com ID: {id_pj}")
    except Exception as e:
        print(f"Erro ao inserir Cliente PJ: {e}")
        return False
        
    # Verificar inserção
    df = db.sql_get('clientes')
    print(f"\nClientes cadastrados:\n{df[['nome', 'tipo_pessoa', 'cpf_cnpj', 'status_cliente']]}")
    
    if len(df) == 2:
        print("Teste CRUD Clientes: SUCESSO")
        return True
    else:
        print("Teste CRUD Clientes: FALHA (Número incorreto de registros)")
        return False

if __name__ == "__main__":
    if test_init_db():
        test_crud_cliente()
    
    # Limpar
    if os.path.exists(db.DB_NAME):
        os.remove(db.DB_NAME)
