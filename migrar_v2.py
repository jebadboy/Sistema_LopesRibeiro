"""
Script de migração para inicializar as novas tabelas e colunas do sistema v2.
Execute este script antes de rodar o app.py pela primeira vez após a atualização.
"""

import database as db

def main():
    print("=" * 60)
    print(" SISTEMA LOPES RIBEIRO - MIGRAÇÃO PARA V2")
    print("=" * 60)
    print()
    
    # Criar backup antes de tudo
    print("► Criando backup de segurança...")
    resultado_backup = db.criar_backup()
    print(f"  {resultado_backup}")
    print()
    
    # Inicializar novas tabelas e colunas
    print("► Inicializando tabelas v2...")
    try:
        db.inicializar_tabelas_v2()
        print("  ✓ Tabelas criadas/atualizadas com sucesso!")
    except Exception as e:
        print(f"  ✗ Erro ao inicializar tabelas: {e}")
        return
    
    print()
    print("=" * 60)
    print(" MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print()
    print("Novas funcionalidades disponíveis:")
    print("  • Gestão de agenda (prazos, audiências, tarefas)")
    print("  • Timeline de andamentos processuais")
    print("  • Documentos chave vinculados a processos")
    print("  • Sistema de parcelamentos")
    print("  • Modelos de proposta")
    print("  • Cálculo automático de repasse de parceria")
    print("  • Relatórios de inadimplência e comissões")
    print()
    print("Você já pode executar o sistema:")
    print("  streamlit run app.py")
    print()

if __name__ == "__main__":
    main()
