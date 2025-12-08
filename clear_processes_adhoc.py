import database as db
import logging

# Configure logging to see what happens
logging.basicConfig(level=logging.INFO)

def clear_processes():
    print("Iniciando limpeza da base de processos...")
    
    # 1. Limpar tabelas dependentes (Cascade as vezes nao funciona dependendo do driver/config)
    print("Limpando andamentos...")
    db.sql_run("DELETE FROM andamentos")
    
    print("Limpando partes do processo...")
    db.sql_run("DELETE FROM partes_processo")
    
    print("Limpando vínculos de agenda...")
    # Não deletamos a agenda, apenas desvinculamos? Ou deletamos eventos do processo?
    # Geralmente eventos de processo devem sumir.
    db.sql_run("DELETE FROM agenda WHERE id_processo IS NOT NULL")
    
    print("Limpando vínculos financeiros...")
    # Financeiro talvez não queira deletar o registro, apenas desvincular?
    # "Limpe todos os processos" -> Se o financeiro é "Honorário do processo X", sem processo ele fica orfão.
    # Vou optar por manter o financeiro mas setar id_processo = NULL para não perder histórico de caixa, 
    # ou deletar se for estritamente vinculado?
    # Pela segurança, vou manter o financeiro mas desvincular.
    db.sql_run("UPDATE financeiro SET id_processo = NULL WHERE id_processo IS NOT NULL")
    
    print("Limpando links públicos...")
    db.sql_run("DELETE FROM tokens_publicos")
    
    # 2. Limpar a tabela processos
    print("Excluindo processos...")
    db.sql_run("DELETE FROM processos")
    
    # Resetar Sequence (Opcional, sqlite)
    db.sql_run("DELETE FROM sqlite_sequence WHERE name='processos'")
    
    print("Limpeza concluída com sucesso!")

if __name__ == "__main__":
    try:
        clear_processes()
    except Exception as e:
        print(f"Erro: {e}")
