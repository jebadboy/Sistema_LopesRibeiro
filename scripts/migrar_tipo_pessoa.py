# Migração: Corrigir Typo "Juríddica" → "Jurídica"

"""
Script de migração para corrigir typo em registros existentes de clientes.

PROBLEMA: Constante OPCOES_TIPO_PESSOA tinha typo "Juríddica" (2 'd's)
IMPACTO: Todos os cadastros de pessoa jurídica salvaram valor incorreto
SOLUÇÃO: UPDATE em massa + prevenção futura

IMPORTANTE: Funciona com PostgreSQL (Supabase) e SQLite
"""

import os
import sys
from datetime import datetime

# Importar módulos do sistema
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
import database as db
import database_adapter as adapter  # Para detectar tipo de banco


def fazer_backup_postgres():
    """Não faz backup automático no Postgres (usa Supabase backup)"""
    print("ℹ️  PostgreSQL detectado - backups gerenciados pelo Supabase")
    print("   Certifique-se de ter backups recentes antes de continuar")
    return None

def fazer_backup_sqlite():
    """Cria backup do SQLite antes da migração"""
    import shutil
    
    # Detectar qual arquivo .db está sendo usado
    db_files = [
        "dados_escritorio.db",
        "sistema.db", 
        "database.db"
    ]
    
    db_path = None
    for db_file in db_files:
        test_path = f"h:/Meu Drive/automatizacao/Sistema_LopesRibeiro/{db_file}"
        if os.path.exists(test_path):
            db_path = test_path
            break
    
    if not db_path:
        print("⚠️  Nenhum banco SQLite encontrado")
        return None
    
    backup_path = f"backups/migracao_tipo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    os.makedirs("backups", exist_ok=True)
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup SQLite criado: {backup_path}")
    return backup_path

def corrigir_typo():
    """Corrige o typo Juríddica → Jurídica"""
    
    print("🔍 Iniciando migração...")
    print("=" * 60)
    
    # 1. Detectar tipo de banco
    is_postgres = adapter.USE_POSTGRES  # Usar variável do adapter
    print(f"📊 Banco detectado: {'PostgreSQL (Supabase)' if is_postgres else 'SQLite'}")
    
    # 2. Backup (apenas SQLite)
    if is_postgres:
        backup_path = fazer_backup_postgres()
        resposta = input("\n⚠️  Continuar sem backup local? (s/N): ")
        if resposta.lower() != 's':
            print("❌ Migração cancelada pelo usuário")
            return
    else:
        backup_path = fazer_backup_sqlite()
    
    try:
        # 3. Verificar quantos registros afetados
        if is_postgres:
            query_count = "SELECT COUNT(*) FROM clientes WHERE tipo_pessoa = 'Juríddica'"
        else:
            query_count = "SELECT COUNT(*) as count FROM clientes WHERE tipo_pessoa = 'Juríddica'"
        
        result = db.sql_get_query(query_count)
        
        if result.empty:
            total_afetados = 0
        else:
            total_afetados = int(result.iloc[0]['count'] if 'count' in result.columns else result.iloc[0][0])
        
        if total_afetados == 0:
            print("✅ Nenhum registro com typo encontrado. Banco já está correto!")
            return
        
        print(f"⚠️  Encontrados {total_afetados} registros com typo 'Juríddica'")
        print()
        
        # Confirmar
        resposta = input(f"Atualizar {total_afetados} registro(s)? (s/N): ")
        if resposta.lower() != 's':
            print("❌ Migração cancelada pelo usuário")
            return
        
        # 4. Executar UPDATE
        update_query = """
            UPDATE clientes 
            SET tipo_pessoa = 'Jurídica' 
            WHERE tipo_pessoa = 'Juríddica'
        """
        
        db.sql_run(update_query)
        
        # 5. Verificar resultado
        result_after = db.sql_get_query("SELECT COUNT(*) as count FROM clientes WHERE tipo_pessoa = 'Jurídica'")
        total_corrigidos = int(result_after.iloc[0]['count'] if not result_after.empty else 0)
        
        print()
        print("=" * 60)
        print(f"✅ Migração concluída!")
        print(f"   - Registros corrigidos: {total_afetados}")
        print(f"   - Total de 'Jurídica' agora: {total_corrigidos}")
        if backup_path:
            print(f"   - Backup salvo em: {backup_path}")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Erro na migração: {e}")
        if backup_path:
            print(f"   Backup disponível em: {backup_path}")
        print("=" * 60)
        raise

def verificar_correcao():
    """Verifica se a correção foi aplicada com sucesso"""
    
    try:
        result_typo = db.sql_get_query("SELECT COUNT(*) as count FROM clientes WHERE tipo_pessoa = 'Juríddica'")
        com_typo = int(result_typo.iloc[0]['count'] if not result_typo.empty else 0)
        
        result_correto = db.sql_get_query("SELECT COUNT(*) as count FROM clientes WHERE tipo_pessoa = 'Jurídica'")
        corretos = int(result_correto.iloc[0]['count'] if not result_correto.empty else 0)
        
        print("\n📊 Verificação Final:")
        print(f"   - Com typo 'Juríddica': {com_typo}")
        print(f"   - Corretos 'Jurídica': {corretos}")
        
        if com_typo == 0:
            print("   ✅ Migração OK! Todos os registros estão corretos.")
        else:
            print("   ⚠️  Ainda existem registros com typo!")
            
    except Exception as e:
        print(f"\n⚠️  Erro na verificação: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRAÇÃO: Corrigir Typo 'Juríddica' → 'Jurídica'")
    print("=" * 60)
    print()
    
    corrigir_typo()
    verificar_correcao()
    
    print()
    print("=" * 60)
    print("IMPORTANTE: Código em clientes.py já está correto:")
    print("  ✅ OPCOES_TIPO_PESSOA = ['Física', 'Jurídica']")
    print("=" * 60)

