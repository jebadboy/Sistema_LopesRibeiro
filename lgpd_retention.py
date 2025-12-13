"""
Script de Verificação e Anonimização LGPD

Este script verifica dados que excederam o prazo de retenção
(conforme configuração lgpd_retencao_anos) e oferece opções para:
- Listar dados expirados
- Anonimizar dados de clientes inativos
- Gerar relatório de conformidade

Uso: python lgpd_retention.py [--check | --anonymize | --report]
"""

import argparse
import logging
from datetime import datetime, timedelta
import database as db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_retention_years() -> int:
    """Obtém prazo de retenção em anos da configuração"""
    try:
        anos = db.get_config('lgpd_retencao_anos', '5')
        return int(anos)
    except:
        return 5  # Default: 5 anos


def get_expired_clients():
    """
    Retorna clientes que excederam o prazo de retenção.
    Critério: clientes INATIVOS há mais de X anos.
    """
    anos = get_retention_years()
    data_limite = (datetime.now() - timedelta(days=anos*365)).strftime('%Y-%m-%d')
    
    query = """
        SELECT c.id, c.nome, c.cpf_cnpj, c.status_cliente, c.data_cadastro,
               MAX(f.data) as ultima_movimentacao
        FROM clientes c
        LEFT JOIN financeiro f ON f.id_cliente = c.id
        WHERE c.status_cliente = 'INATIVO'
        GROUP BY c.id
        HAVING (c.data_cadastro < ? OR c.data_cadastro IS NULL)
           AND (MAX(f.data) < ? OR MAX(f.data) IS NULL)
    """
    
    return db.sql_get_query(query, (data_limite, data_limite))


def get_expired_processes():
    """
    Retorna processos arquivados há mais de X anos.
    """
    anos = get_retention_years()
    data_limite = (datetime.now() - timedelta(days=anos*365)).strftime('%Y-%m-%d')
    
    query = """
        SELECT p.id, p.numero, p.cliente_nome, p.fase_processual, 
               MAX(a.data) as ultimo_andamento
        FROM processos p
        LEFT JOIN andamentos a ON a.id_processo = p.id
        WHERE p.fase_processual IN ('Arquivado', 'Baixado', 'Trânsito em Julgado')
        GROUP BY p.id
        HAVING (MAX(a.data) < ? OR MAX(a.data) IS NULL)
    """
    
    return db.sql_get_query(query, (data_limite,))


def anonymize_client(client_id: int, reason: str = "LGPD - Prazo de retenção excedido"):
    """
    Anonimiza dados de um cliente específico.
    
    Substitui dados pessoais por valores genéricos, mantendo ID
    para integridade referencial.
    """
    try:
        # Gerar identificador anônimo
        anon_id = f"ANONIMO_{client_id:06d}"
        
        # Atualizar dados do cliente
        db.sql_run("""
            UPDATE clientes SET
                nome = ?,
                cpf_cnpj = '***.***.***-**',
                email = NULL,
                telefone = NULL,
                telefone_fixo = NULL,
                endereco = NULL,
                cep = NULL,
                bairro = NULL,
                cidade = NULL,
                estado = NULL,
                obs = 'Dados anonimizados conforme LGPD',
                rg = NULL,
                data_nascimento = NULL,
                status_cliente = 'ANONIMIZADO'
            WHERE id = ?
        """, (anon_id, client_id))
        
        # Registrar auditoria
        db.audit(
            action="LGPD_ANONIMIZACAO",
            details=f"Cliente ID {client_id} anonimizado. Motivo: {reason}",
            username="Sistema LGPD"
        )
        
        logger.info(f"Cliente {client_id} anonimizado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao anonimizar cliente {client_id}: {e}")
        return False


def check_expired_data():
    """Verifica e lista dados expirados"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE DADOS EXPIRADOS (LGPD)")
    print(f"   Prazo de retenção: {get_retention_years()} anos")
    print("="*60)
    
    # Clientes expirados
    clientes = get_expired_clients()
    print(f"\n📋 Clientes inativos há mais de {get_retention_years()} anos: {len(clientes)}")
    
    if not clientes.empty:
        for _, c in clientes.head(10).iterrows():
            print(f"   - ID {c['id']}: {c['nome']} (desde {c['data_cadastro']})")
        if len(clientes) > 10:
            print(f"   ... e mais {len(clientes) - 10} clientes")
    
    # Processos expirados
    processos = get_expired_processes()
    print(f"\n📁 Processos arquivados há mais de {get_retention_years()} anos: {len(processos)}")
    
    if not processos.empty:
        for _, p in processos.head(10).iterrows():
            print(f"   - ID {p['id']}: {p['numero']} ({p['cliente_nome']})")
        if len(processos) > 10:
            print(f"   ... e mais {len(processos) - 10} processos")
    
    print("\n" + "="*60)
    return len(clientes) + len(processos)


def run_anonymization(dry_run: bool = True):
    """
    Executa anonimização de dados expirados.
    
    Args:
        dry_run: Se True, apenas simula (não executa)
    """
    clientes = get_expired_clients()
    
    if clientes.empty:
        print("✅ Nenhum dado expirado encontrado.")
        return
    
    print(f"\n{'[SIMULAÇÃO] ' if dry_run else ''}Anonimizando {len(clientes)} clientes...")
    
    success = 0
    for _, c in clientes.iterrows():
        if dry_run:
            print(f"   [DRY-RUN] Anonimizaria: {c['nome']} (ID {c['id']})")
            success += 1
        else:
            if anonymize_client(c['id']):
                success += 1
    
    print(f"\n{'[SIMULAÇÃO] ' if dry_run else ''}Resultado: {success}/{len(clientes)} processados")


def generate_report():
    """Gera relatório de conformidade LGPD"""
    print("\n" + "="*60)
    print("📊 RELATÓRIO DE CONFORMIDADE LGPD")
    print(f"   Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*60)
    
    # Total de clientes
    total_clientes = db.sql_get_query("SELECT COUNT(*) as total FROM clientes")
    print(f"\n📋 Total de clientes: {total_clientes.iloc[0]['total']}")
    
    # Clientes com consentimento
    com_lgpd = db.sql_get_query("SELECT COUNT(*) as total FROM clientes WHERE lgpd_consentimento = 1")
    print(f"   Com consentimento LGPD: {com_lgpd.iloc[0]['total']}")
    
    # Clientes anonimizados
    anonimizados = db.sql_get_query("SELECT COUNT(*) as total FROM clientes WHERE status_cliente = 'ANONIMIZADO'")
    print(f"   Anonimizados: {anonimizados.iloc[0]['total']}")
    
    # Logs de acesso (últimos 30 dias)
    logs = db.sql_get_query("""
        SELECT COUNT(*) as total FROM audit_logs 
        WHERE action LIKE 'ACESSO_DADOS%' 
        AND timestamp > datetime('now', '-30 days')
    """)
    print(f"\n🔍 Acessos a dados pessoais (30 dias): {logs.iloc[0]['total']}")
    
    # Dados expirados
    expirados = check_expired_data()
    print(f"\n⚠️ Dados pendentes de anonimização: {expirados}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerenciamento de Retenção LGPD")
    parser.add_argument('--check', action='store_true', help='Verificar dados expirados')
    parser.add_argument('--anonymize', action='store_true', help='Anonimizar dados expirados')
    parser.add_argument('--dry-run', action='store_true', help='Simular anonimização')
    parser.add_argument('--report', action='store_true', help='Gerar relatório de conformidade')
    
    args = parser.parse_args()
    
    # Inicializar banco
    db.init_db()
    
    if args.check:
        check_expired_data()
    elif args.anonymize:
        run_anonymization(dry_run=args.dry_run)
    elif args.report:
        generate_report()
    else:
        # Sem argumentos: mostra ajuda
        parser.print_help()
        print("\nExemplos:")
        print("  python lgpd_retention.py --check")
        print("  python lgpd_retention.py --anonymize --dry-run")
        print("  python lgpd_retention.py --report")
