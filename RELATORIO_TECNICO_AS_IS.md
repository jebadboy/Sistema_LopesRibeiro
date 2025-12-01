# Relatório Técnico de Situação Atual (AS-IS) - Versão 2.0 Planning

**Data:** 01/12/2025
**Responsável:** Arquiteto de Software Sênior (Antigravity)
**Escopo:** Análise dos arquivos `@app.py`, `@database.py`, `@utils.py` e estrutura de módulos.

---

## 1. Inventário de Funcionalidades

O sistema é uma aplicação web modular construída em **Streamlit**, focada na gestão jurídica de um escritório de advocacia.

### 🔐 Autenticação e Sessão (`app.py`)

* **Login:** Autenticação via Username/Senha com hash SHA-256.
* **Controle de Acesso:** Perfis de usuário ('admin', 'user', 'advogado', 'secretaria').
* **Logout:** Encerramento de sessão e limpeza de estado.

### 📂 Módulo Clientes (CRM) (`modules/clientes.py`)

* **Cadastro:** Criação de Pessoa Física (CPF) ou Jurídica (CNPJ).
* **Validação:** Verificação matemática de CPF/CNPJ e duplicidade no banco.
* **Endereço:** Busca automática de endereço via API ViaCEP.
* **Gestão:** Listagem, busca (Nome/CPF), edição de dados cadastrais.
* **Propostas:** Registro de valores, parcelamento e forma de pagamento.
* **Documentação:**
  * Geração automática de **Propostas**, **Procurações**, **Declarações de Hipossuficiência** e **Contratos** em Word (`.docx`).
  * Integração de links para pastas do Google Drive.
  * Acesso a modelos de referência.

### 💰 Módulo Financeiro (`modules/financeiro.py` - Inferred & DB)

* **Lançamentos:** Registro de Entradas e Saídas.
* **Vínculos:** Associação de lançamentos a Clientes e Processos.
* **Parcelamento:** Gestão de parcelas (tabela `parcelamentos`).
* **Relatórios:** DRE e Rentabilidade (funções em `database.py`).
* **KPIs:** Cálculo de Saldo, Contas a Receber (função `kpis` em `database.py`).

### ⚖️ Módulo Processos (`modules/processos.py` - Inferred & DB)

* **Cadastro:** Registro de processos com número, partes, vara e comarca.
* **Andamentos:** Histórico de movimentações processuais.
* **Agenda:** Controle de prazos e audiências vinculados ao processo.
* **Documentos:** Gestão de links para peças processuais (Petição Inicial, Sentença, etc.).

### ⚙️ Administração (`modules/admin.py`)

* **Usuários:** Criação e edição de usuários e senhas.
* **Configuração do Escritório:** Definição de dados globais (Nome do Advogado, OAB, Endereço) usados na geração de documentos.
* **Links de Modelos:** Configuração centralizada de links para modelos no Drive.

---

## 2. Mapa de Interconexões

O sistema opera em uma arquitetura monolítica modularizada, onde `app.py` atua como o controlador central.

* **Fluxo de Dados:**
  * **Clientes ↔ Financeiro:** A tabela `financeiro` possui chave estrangeira `id_cliente`. O sistema permite lançar honorários vinculados diretamente a um cliente cadastrado.
  * **Clientes ↔ Processos:** A tabela `processos` possui chave estrangeira `id_cliente`. Um processo não existe sem um cliente vinculado.
  * **Processos ↔ Financeiro:** A tabela `financeiro` possui chave estrangeira `id_processo`, permitindo custas e honorários sucumbenciais atrelados a um processo específico.
  * **Processos ↔ Agenda:** A tabela `agenda` é vinculada a `processos` (`id_processo`), centralizando prazos por caso.
  * **Admin ↔ Geração de Docs:** O módulo `utils.py` consome a tabela `config` (gerida pelo Admin) para preencher cabeçalhos e rodapés de documentos automaticamente.

---

## 3. Estrutura de Dados (O "Cérebro")

O banco de dados é **SQLite** (`dados_escritorio.db`). Abaixo, o esquema atual (`init_db` e `inicializar_tabelas_v2`):

### Tabelas Principais

1. **`clientes`**
    * **Colunas:** `id`, `nome`, `cpf_cnpj`, `email`, `telefone`, `endereco`, `status_cliente` (EM NEGOCIAÇÃO, ATIVO, INATIVO), `link_drive`, `proposta_valor`, `proposta_parcelas`, `link_procuracao`, `link_hipossuficiencia`, etc.
2. **`processos`**
    * **Colunas:** `id`, `numero_processo`, `cliente` (texto redundante?), `parte_contraria`, `vara`, `comarca`, `status`, `fase_processual`, `valor_causa`, `id_cliente` (FK).
3. **`financeiro`**
    * **Colunas:** `id`, `data`, `tipo` (Entrada/Saída), `categoria`, `descricao`, `valor`, `vencimento`, `status_pagamento`, `id_cliente` (FK), `id_processo` (FK), `percentual_parceria`.
4. **`andamentos`**
    * **Colunas:** `id`, `id_processo` (FK), `data`, `descricao`, `responsavel`.

### Tabelas V2 (Novas Funcionalidades)

5. **`agenda`**: `id`, `tipo` (prazo, audiencia), `data_evento`, `id_processo` (FK), `google_calendar_id`.
6. **`documentos_processo`**: `id`, `id_processo` (FK), `tipo_documento`, `link_drive`.
7. **`parcelamentos`**: `id`, `id_lancamento_financeiro` (FK), `numero_parcela`, `valor_parcela`, `vencimento`.
8. **`modelos_proposta`**: `id`, `nome_modelo`, `descricao_padrao` (com placeholders), `valor_sugerido`.
9. **`usuarios`**: `id`, `username`, `password_hash`, `role`, `ativo`.
10. **`config`**: `chave` (PK), `valor` (Armazena configurações globais Key-Value).

---

## 4. Bibliotecas e Dependências

O sistema depende das seguintes bibliotecas externas (identificadas em `utils.py` e `app.py`):

* **`streamlit`**: Framework principal de Interface de Usuário (Frontend/Backend).
* **`sqlite3`** (Nativa): Motor de Banco de Dados.
* **`pandas`**: Manipulação de dados, geração de DataFrames para visualização e relatórios (DRE, KPIs).
* **`requests`**: Requisições HTTP, utilizada para consultar a API de CEP (ViaCEP).
* **`python-docx`**: Geração e manipulação de documentos Word (`.docx`) para propostas e contratos.
* **`PyPDF2`**: Manipulação de PDFs (importada, uso potencial em módulos de documentos).
* **`hashlib`** (Nativa): Criptografia de senhas (SHA-256).
* **`re`** (Nativa): Expressões regulares para validação de CPF, CNPJ, Email e Telefones.
* **`logging`** (Nativa): Sistema de logs (`sistema_lopes_ribeiro.log`).

---

**Conclusão:** O sistema possui uma base sólida para um MVP, com estrutura de dados relacional bem definida. A versão 2.0 deve focar na otimização da interface, refatoração de código redundante (ex: formatação repetida) e expansão das funcionalidades de automação (Agenda e Documentos).
