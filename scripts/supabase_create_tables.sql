-- ============================================
-- SCRIPT DE CRIAÇÃO DE TABELAS - SUPABASE
-- Sistema Jurídico Lopes & Ribeiro
-- ============================================
-- Execute este script no SQL Editor do Supabase
-- Acesse: supabase.com -> seu projeto -> SQL Editor -> New Query
-- Cole este conteúdo e clique em "Run"
-- ============================================

-- 1. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nome TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pergunta_secreta TEXT,
    resposta_secreta_hash TEXT,
    email TEXT,
    reset_token TEXT,
    reset_expiry TEXT
);

-- 2. Tabela de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
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
    proposta_pagamento TEXT,
    status_proposta TEXT,
    tipo_pessoa TEXT,
    proposta_data_pagamento TEXT,
    link_procuracao TEXT,
    link_hipossuficiencia TEXT,
    nacionalidade TEXT,
    rg TEXT,
    orgao_emissor TEXT,
    data_nascimento TEXT
);

-- 3. Tabela de Processos
CREATE TABLE IF NOT EXISTS processos (
    id SERIAL PRIMARY KEY,
    numero TEXT,
    cliente_nome TEXT,
    area TEXT,
    acao TEXT,
    vara TEXT,
    status TEXT DEFAULT 'Ativo',
    proximo_prazo TEXT,
    responsavel TEXT,
    status_processo TEXT,
    parceiro_nome TEXT,
    parceiro_percentual REAL,
    pasta_drive_link TEXT,
    tipo_honorario TEXT,
    fase_processual TEXT,
    id_cliente INTEGER REFERENCES clientes(id),
    valor_causa REAL,
    data_distribuicao TEXT,
    link_drive TEXT,
    comarca TEXT,
    obs TEXT
);

-- 4. Tabela de Financeiro
CREATE TABLE IF NOT EXISTS financeiro (
    id SERIAL PRIMARY KEY,
    data TEXT NOT NULL,
    tipo TEXT NOT NULL,
    categoria TEXT,
    descricao TEXT,
    valor REAL NOT NULL,
    status_pagamento TEXT DEFAULT 'Pendente',
    vencimento TEXT,
    id_cliente INTEGER REFERENCES clientes(id),
    id_processo INTEGER REFERENCES processos(id),
    meio_pagamento TEXT,
    comprovante_link TEXT,
    obs TEXT,
    cliente TEXT,
    status TEXT,
    data_pagamento TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabela de Andamentos
CREATE TABLE IF NOT EXISTS andamentos (
    id SERIAL PRIMARY KEY,
    id_processo INTEGER NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    tipo TEXT,
    responsavel TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Tabela de Parcelas
CREATE TABLE IF NOT EXISTS parcelas (
    id SERIAL PRIMARY KEY,
    id_lancamento_financeiro INTEGER NOT NULL REFERENCES financeiro(id) ON DELETE CASCADE,
    numero_parcela INTEGER NOT NULL,
    total_parcelas INTEGER NOT NULL,
    valor_parcela REAL NOT NULL,
    vencimento TEXT NOT NULL,
    status_parcela TEXT DEFAULT 'pendente',
    pago_em TEXT,
    obs TEXT
);

-- 7. Tabela de Agenda
CREATE TABLE IF NOT EXISTS agenda (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    descricao TEXT,
    data_evento TEXT NOT NULL,
    hora_evento TEXT,
    tipo_evento TEXT,
    id_processo INTEGER REFERENCES processos(id),
    id_cliente INTEGER REFERENCES clientes(id),
    google_event_id TEXT,
    status TEXT DEFAULT 'pendente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Tabela de Configurações
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Tabela de Timeline do Cliente
CREATE TABLE IF NOT EXISTS cliente_timeline (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_evento TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    icone TEXT,
    data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Tabela de Documentos Drive
CREATE TABLE IF NOT EXISTS documentos_drive (
    id SERIAL PRIMARY KEY,
    nome_arquivo TEXT NOT NULL,
    tipo_arquivo TEXT,
    drive_id TEXT,
    web_link TEXT,
    id_cliente INTEGER REFERENCES clientes(id),
    id_processo INTEGER REFERENCES processos(id),
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    obs TEXT
);

-- 11. Tabela Modelos de Proposta
CREATE TABLE IF NOT EXISTS modelos_proposta (
    id SERIAL PRIMARY KEY,
    nome_modelo TEXT UNIQUE NOT NULL,
    area_atuacao TEXT,
    titulo TEXT,
    descricao TEXT,
    lido INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Tabela Configurações de Aniversários
CREATE TABLE IF NOT EXISTS config_aniversarios (
    id SERIAL PRIMARY KEY,
    dias_antecedencia INTEGER DEFAULT 7,
    template_mensagem TEXT,
    ativo INTEGER DEFAULT 1
);

-- 13. Tabela Histórico de IA
CREATE TABLE IF NOT EXISTS ai_historico (
    id SERIAL PRIMARY KEY,
    usuario TEXT,
    tipo TEXT,
    input TEXT,
    output TEXT,
    data_hora TEXT,
    processo_id INTEGER
);

-- 14. Tabela de Logs de Auditoria
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    action TEXT,
    tabela TEXT,
    registro_id INTEGER,
    campo TEXT,
    valor_anterior TEXT,
    valor_novo TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Tabela Partes do Processo
CREATE TABLE IF NOT EXISTS partes_processo (
    id SERIAL PRIMARY KEY,
    id_processo INTEGER REFERENCES processos(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    tipo TEXT,
    cpf_cnpj TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Tabela Modelos de Documentos
CREATE TABLE IF NOT EXISTS modelos_documentos (
    id SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    categoria TEXT,
    conteudo TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Tabela Tokens Públicos
CREATE TABLE IF NOT EXISTS tokens_publicos (
    id SERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    id_processo INTEGER NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_expiracao TEXT,
    ativo INTEGER DEFAULT 1,
    acessos INTEGER DEFAULT 0,
    ultimo_acesso TEXT
);

-- 18. Tabela de Notificações
CREATE TABLE IF NOT EXISTS notificacoes (
    id SERIAL PRIMARY KEY,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    mensagem TEXT,
    link_acao TEXT,
    prioridade TEXT DEFAULT 'media',
    lida INTEGER DEFAULT 0,
    arquivada INTEGER DEFAULT 0,
    usuario_destino TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. Tabela Alertas Email
CREATE TABLE IF NOT EXISTS alertas_email (
    id SERIAL PRIMARY KEY,
    remetente TEXT,
    assunto TEXT,
    corpo TEXT,
    tipo TEXT,
    numero_processo TEXT,
    valor_detectado REAL,
    processado INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. Tabela Rate Limiter
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    identifier TEXT NOT NULL,
    username TEXT,
    success INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 21. Tabela Transações Bancárias
CREATE TABLE IF NOT EXISTS transacoes_bancarias (
    id SERIAL PRIMARY KEY,
    bank_id TEXT,
    fit_id TEXT UNIQUE,
    tipo TEXT,
    data_transacao TEXT,
    valor REAL,
    descricao TEXT,
    categoria TEXT,
    conciliado INTEGER DEFAULT 0,
    id_financeiro INTEGER REFERENCES financeiro(id),
    arquivo_origem TEXT,
    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INSERIR USUÁRIO ADMIN PADRÃO
-- Senha: admin123 (hash bcrypt)
-- ============================================
INSERT INTO usuarios (username, password_hash, nome, role, ativo)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.V5YZkq9aoy0V5m',
    'Administrador',
    'admin',
    1
) ON CONFLICT (username) DO NOTHING;

-- ============================================
-- FIM DO SCRIPT
-- ============================================
