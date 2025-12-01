# 🐘 Guia de Configuração do Supabase

Siga estes passos para criar seu banco de dados na nuvem e pegar a chave de acesso.

## 1. Criar Projeto
1.  Acesse [supabase.com](https://supabase.com/) e faça login.
2.  Clique em **"New Project"**.
3.  Escolha sua organização.
4.  Preencha:
    *   **Name:** `Sistema_LopesRibeiro`
    *   **Database Password:** Crie uma senha forte (e **ANOTE-A**, você vai precisar!).
    *   **Region:** Escolha `Sao Paulo` (South America) para ser mais rápido.
5.  Clique em **"Create new project"**.
6.  Aguarde alguns minutos enquanto o banco é criado.

## 2. Pegar a URL de Conexão
1.  No painel do seu projeto, vá no menu lateral esquerdo e clique em **"Project Settings"** (ícone de engrenagem ⚙️).
2.  Clique na aba **"Database"**.
3.  Role até a seção **"Connection string"**.
4.  Clique na aba **"URI"**.
5.  Copie o link que aparece. Ele será parecido com isto:
    `postgresql://postgres.xxxx:[SUA-SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres`

## 3. Me envie a URL (com segurança)
Cole a URL aqui no chat, mas **substitua sua senha real** por `******` se preferir, ou me mande ela completa que eu te ajudo a configurar o segredo.

> **Dica:** Se você copiar a URL direto do site, ela vem com `[YOUR-PASSWORD]`. Lembre-se de trocar isso pela senha que você criou no passo 1!
