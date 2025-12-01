# 🚀 Guia de Deploy no Railway (Recomendado)

Este guia explica como publicar o **Sistema Lopes & Ribeiro** no Railway, garantindo que o banco de dados e as integrações (Google Calendar, IA) funcionem perfeitamente.

## 📋 Pré-requisitos
1.  Conta no [GitHub](https://github.com/) (onde está seu código).
2.  Conta no [Railway](https://railway.app/) (pode logar com GitHub).
3.  Arquivo `credentials.json` do Google Cloud (você já tem).

---

## 🛠️ Passo 1: Preparar o Repositório

Certifique-se de que todas as alterações recentes foram enviadas para o GitHub:

```bash
git add .
git commit -m "Configuração para Railway com persistência"
git push origin main
```

---

## ☁️ Passo 2: Criar Projeto no Railway

1.  Acesse [Railway Dashboard](https://railway.app/dashboard).
2.  Clique em **"New Project"** > **"Deploy from GitHub repo"**.
3.  Selecione o repositório `Sistema_LopesRibeiro`.
4.  Clique em **"Deploy Now"**.

> ⚠️ **Atenção:** O primeiro deploy vai falhar ou ficar incompleto porque faltam as variáveis de ambiente. Isso é normal!

---

## 📦 Passo 3: Configurar Persistência (Volume)

Para que o banco de dados não seja apagado quando o sistema reiniciar:

1.  No painel do seu projeto no Railway, clique no "card" do serviço.
2.  Vá na aba **"Volumes"**.
3.  Clique em **"Add Volume"**.
4.  Mount Path: `/app/data`
5.  Clique em **"Add"**.

---

## 🔑 Passo 4: Configurar Variáveis de Ambiente

Vá na aba **"Variables"** e adicione as seguintes chaves:

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `PORT` | `8501` | Porta do Streamlit |
| `DB_PATH` | `/app/data/dados_escritorio.db` | Caminho do banco no volume |
| `DATA_DIR` | `/app/data` | Pasta para salvar tokens |
| `GEMINI_API_KEY` | `(Sua chave do Gemini)` | Copie do seu `.env` local |
| `GOOGLE_CREDENTIALS_BASE64` | `(Ver passo abaixo)` | Credenciais do Google |

### 🔐 Como gerar o `GOOGLE_CREDENTIALS_BASE64`

Para não colocar o arquivo `credentials.json` no GitHub, vamos transformá-lo em um código seguro.

1.  No seu computador local, abra o terminal na pasta do projeto.
2.  Execute este comando Python para gerar o código:

```python
import base64
with open('credentials.json', 'rb') as f:
    print(base64.b64encode(f.read()).decode('utf-8'))
```

3.  Copie o código enorme que aparecerá.
4.  Cole no Railway como valor da variável `GOOGLE_CREDENTIALS_BASE64`.

---

## 🚀 Passo 5: Finalizar

1.  Após configurar as variáveis e o volume, o Railway deve reiniciar o deploy automaticamente.
2.  Se não reiniciar, vá na aba **"Deployments"** e clique em **"Redeploy"**.
3.  Aguarde ficar "Active" (verde).
4.  Vá na aba **"Settings"** > **"Networking"** e clique em **"Generate Domain"**.
5.  **Pronto!** Acesse seu sistema pela URL gerada (ex: `sistema-lopes-ribeiro-production.up.railway.app`).

---

## 🔄 Como Atualizar Depois?

Sempre que você fizer alterações no código e der `git push`, o Railway atualizará o sistema automaticamente em alguns minutos, mantendo seus dados salvos no volume.
