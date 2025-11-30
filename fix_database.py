"""
Script para aplicar correções críticas no database.py de forma segura
"""

# Ler o arquivo original
with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Correção 1: Adicionar tokens_publicos à TABELAS_VALIDAS
content = content.replace(
    "TABELAS_VALIDAS = [\n    'clientes', 'financeiro', 'processos', 'andamentos',\n    'agenda', 'documentos_processo', 'parcelamentos', 'modelos_proposta', 'usuarios', 'logs'\n]",
    "TABELAS_VALIDAS = [\n    'clientes', 'financeiro', 'processos', 'andamentos',\n    'agenda', 'documentos_processo', 'parcelamentos', 'modelos_proposta', 'usuarios', 'logs', 'tokens_publicos'\n]"
)

# Correção 2: Adicionar id_parceiro à tabela financeiro
old_financeiro = '''            # Tabela de Financeiro
            c.execute(\'\'\'
                CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    tipo TEXT CHECK(tipo IN ('Entrada', 'Saída')),
                    categoria TEXT,
                    descricao TEXT,
                    valor REAL NOT NULL,
                    responsavel TEXT,
                    status_pagamento TEXT CHECK(status_pagamento IN ('Pago', 'Pendente')) DEFAULT 'Pendente',
                    vencimento TEXT,
                    id_cliente INTEGER,
                    id_processo INTEGER,
                    percentual_parceria REAL DEFAULT 0.0,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id) ON DELETE SET NULL,
                    FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE SET NULL
                )
            \'\'\')'''

new_financeiro = '''            # Tabela de Financeiro
            c.execute(\'\'\'
                CREATE TABLE IF NOT EXISTS financeiro (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    tipo TEXT CHECK(tipo IN ('Entrada', 'Saída')),
                    categoria TEXT,
                    descricao TEXT,
                    valor REAL NOT NULL,
                    responsavel TEXT,
                    status_pagamento TEXT CHECK(status_pagamento IN ('Pago', 'Pendente')) DEFAULT 'Pendente',
                    vencimento TEXT,
                    id_cliente INTEGER,
                    id_processo INTEGER,
                    id_parceiro INTEGER,
                    percentual_parceria REAL DEFAULT 0.0,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id) ON DELETE SET NULL,
                    FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE SET NULL
                )
            \'\'\')'''

content = content.replace(old_financeiro, new_financeiro)

# Correção 3: Completar init_db com fechamento correto  
old_init = '''            # Tabela de Logs (Auditoria)
            c.execute(\'\'\'
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT,
                    acao TEXT,
                    tabela TEXT,
                    detalhes TEXT,
                    data_hora TEXT DEFAULT CURRENT_TIMESTAMP
                )
            \'\'\')
            
            # Migração para adicionar colunas em tabelas existentes
            try:
                c.execute("ALTER TABLE financeiro ADD COLUMN id_parceiro INTEGER")
            except:
                pass
            
            try:
                c.execute("ALTER TABLE financeiro ADD COLUMN percentual_parceria REAL DEFAULT 0.0")
            except:
                pass
            
            conn.commit()
            logger.info("Tabelas iniciadas")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        raise'''

new_init = '''            # Tabela de Logs (Auditoria)
            c.execute(\'\'\'
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT,
                    acao TEXT,
                    tabela TEXT,
                    detalhes TEXT,
                    data_hora TEXT DEFAULT CURRENT_TIMESTAMP
                )
            \'\'\')
            
            # Migração para adicionar colunas em tabelas existentes
            try:
                c.execute("ALTER TABLE financeiro ADD COLUMN id_parceiro INTEGER")
            except:
                pass
            
            try:
                c.execute("ALTER TABLE financeiro ADD COLUMN percentual_parceria REAL DEFAULT 0.0")
            except:
                pass
            
            conn.commit()
            logger.info("Tabelas principais inicializadas com sucesso")
        
        # Inicializar tabelas v2 (agenda, documentos, etc)
        inicializar_tabelas_v2()
        
        # Inicializar tabela de tokens públicos
        try:
            import token_manager
            token_manager.inicializar_tabela_tokens()
        except Exception as e:
            logger.warning(f"Erro ao inicializar tokens públicos: {e}")
        
        # Criar usuário admin padrão
        criar_usuario_admin_padrao()
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise RuntimeError(f"Falha na inicialização do banco: {e}")'''

content = content.replace(old_init, new_init)

# Salvar o arquivo corrigido
with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Correções aplicadas com sucesso!")
print("  - tokens_publicos adicionado a TABELAS_VALIDAS")
print("  - id_parceiro adicionado à tabela financeiro")
print("  - init_db() completado com integração do token_manager")
