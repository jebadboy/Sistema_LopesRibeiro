"""
Script de migração completa para PostgreSQL
Cria todas as tabelas do sistema no Supabase
"""
import os
from urllib.parse import quote_plus

# Configurar connection string
password = "Sh@220681"
encoded_password = quote_plus(password)
DATABASE_URL = f'postgresql://postgres:{encoded_password}@db.yczfxlqgkibpvemcfdbi.supabase.co:5432/postgres'
os.environ['DATABASE_URL'] = DATABASE_URL

from database_adapter import db_adapter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_all_tables():
    """Cria todas as tabelas do sistema no PostgreSQL"""
    
    logger.info("Criando tabelas no PostgreSQL...")
    
    with db_adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabela de Usuários
        logger.info("Criando tabela usuarios...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT,
                role VARCHAR(20) DEFAULT 'advogado',
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Tabela de Clientes
        logger.info("Criando tabela clientes...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                tipo_pessoa TEXT DEFAULT 'Física',
                cpf_cnpj TEXT,
                email TEXT,
                telefone TEXT,
                telefone_fixo TEXT,
                profissao TEXT,
                estado_civil TEXT,
                cep TEXT,
                endereco TEXT,
                numero_casa TEXT,
                complemento TEXT,
                bairro TEXT,
                cidade TEXT,
                estado TEXT,
                obs TEXT,
                status_cliente TEXT DEFAULT 'EM NEGOCIAÇÃO',
                link_drive TEXT,
                data_cadastro TEXT,
                proposta_valor REAL,
                proposta_entrada REAL,
                proposta_parcelas INTEGER,
                proposta_objeto TEXT,
                proposta_pagamento TEXT
            )
        ''')
        
        # 3. Tabela de Processos
        logger.info("Criando tabela processos...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processos (
                id SERIAL PRIMARY KEY,
                cliente_nome TEXT,
                acao TEXT,
                proximo_prazo TEXT,
                responsavel TEXT,
                status TEXT DEFAULT 'Ativo'
            )
        ''')
        
        # 4. Tabela de Andamentos
        logger.info("Criando tabela andamentos...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS andamentos (
                id SERIAL PRIMARY KEY,
                id_processo INTEGER NOT NULL,
                data TEXT,
                descricao TEXT,
                responsavel TEXT,
                FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE CASCADE
            )
        ''')
        
        # 5. Tabela Financeiro
        logger.info("Criando tabela financeiro...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financeiro (
                id SERIAL PRIMARY KEY,
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
                mes_referencia TEXT,
                ano_referencia INTEGER,
                comprovante_link TEXT,
                recorrente INTEGER DEFAULT 0,
                forma_pagamento TEXT,
                recorrencia TEXT,
                FOREIGN KEY (id_cliente) REFERENCES clientes(id) ON DELETE SET NULL,
                FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE SET NULL
            )
        ''')
        
        # 6. Tabela de Logs
        logger.info("Criando tabela logs...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                usuario TEXT,
                acao TEXT,
                tabela TEXT,
                detalhes TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 7. Tabela Agenda
        logger.info("Criando tabela agenda...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id SERIAL PRIMARY KEY,
                tipo TEXT CHECK(tipo IN ('prazo', 'audiencia', 'tarefa')),
                titulo TEXT NOT NULL,
                descricao TEXT,
                data_evento TEXT,
                responsavel TEXT,
                id_processo INTEGER,
                status TEXT DEFAULT 'pendente',
                google_calendar_id TEXT,
                cor TEXT,
                prioridade TEXT CHECK(prioridade IN ('baixa', 'media', 'alta', 'urgente')),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_processo) REFERENCES processos(id)
            )
        ''')
        
        # 8. Tabela Documentos do Processo
        logger.info("Criando tabela documentos_processo...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documentos_processo (
                id SERIAL PRIMARY KEY,
                id_processo INTEGER NOT NULL,
                tipo_documento TEXT CHECK(tipo_documento IN ('peticao_inicial', 'procuracao', 'sentenca', 'acordao', 'outro')),
                nome_documento TEXT,
                link_drive TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_processo) REFERENCES processos(id)
            )
        ''')
        
        # 9. Tabela Parcelamentos
        logger.info("Criando tabela parcelamentos...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parcelamentos (
                id SERIAL PRIMARY KEY,
                id_lancamento_financeiro INTEGER NOT NULL,
                numero_parcela INTEGER,
                total_parcelas INTEGER,
                valor_parcela REAL,
                vencimento TEXT,
                status_parcela TEXT DEFAULT 'pendente',
                pago_em TEXT,
                FOREIGN KEY (id_lancamento_financeiro) REFERENCES financeiro(id)
            )
        ''')
        
        # 10. Tabela Modelos de Proposta
        logger.info("Criando tabela modelos_proposta...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos_proposta (
                id SERIAL PRIMARY KEY,
                nome_modelo TEXT UNIQUE NOT NULL,
                area_atuacao TEXT,
                descricao_padrao TEXT,
                valor_sugerido REAL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 11. Tabela Tokens Públicos
        logger.info("Criando tabela tokens_publicos...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens_publicos (
                id SERIAL PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                id_processo INTEGER NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expira_em TIMESTAMP,
                ultimo_acesso TIMESTAMP,
                revogado INTEGER DEFAULT 0,
                descricao TEXT,
                FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        logger.info("Todas as tabelas criadas com sucesso!")
        
        # Criar usuário admin padrão
        logger.info("Criando usuário admin padrão...")
        try:
            import hashlib
            senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, nome, role) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
                ("admin", senha_hash, "Administrador", "admin")
            )
            conn.commit()
            logger.info("Usuário admin criado/verificado")
        except Exception as e:
            logger.warning(f"Admin já existe ou erro: {e}")
        
        # Listar tabelas criadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        logger.info(f"\nTabelas no banco ({len(tables)}):")
        for table in tables:
            logger.info(f"  - {table['table_name']}")

if __name__ == "__main__":
    print("=" * 60)
    print("CRIAÇÃO DE SCHEMA NO POSTGRESQL (SUPABASE)")
    print("=" * 60)
    
    try:
        create_all_tables()
        print("\n" + "=" * 60)
        print("✓ SUCESSO! Todas as tabelas foram criadas no PostgreSQL")
        print("=" * 60)
        print("\nPróximo passo: Migrar dados do SQLite para PostgreSQL")
        
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
