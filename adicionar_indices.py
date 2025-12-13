import database_adapter as adapter

with adapter.get_connection() as conn:
    cursor = conn.cursor()
    
    # Criar índices para acelerar buscas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cpf_cnpj ON clientes(cpf_cnpj)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_status ON clientes(status_cliente)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processos_cliente_nome ON processos(cliente_nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_financeiro_id_cliente ON financeiro(id_cliente)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agenda_id_processo ON agenda(id_processo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cliente_timeline_cliente_id ON cliente_timeline(cliente_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_publicos_id_processo ON tokens_publicos(id_processo)")
    
    conn.commit()
    print("✅ Índices criados!")