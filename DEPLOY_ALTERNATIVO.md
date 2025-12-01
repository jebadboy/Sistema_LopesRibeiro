# 🚀 Deploy no Railway.app - Passo a Passo

## Opção 1: Railway.app (MAIS FÁCIL)

### 1. Criar Conta
- Acesse: https://railway.app
- Clique em "Start a New Project"
- Login com GitHub

### 2. Deploy Automático
1. Clique em "Deploy from GitHub repo"
2. Selecione: `jebadboy/Sistema_LopesRibeiro`
3. Railway detecta automaticamente que é Python

### 3. Adicionar Variáveis de Ambiente
1. No dashboard do Railway, clique no seu projeto
2. Vá em "Variables"
3. Adicione:
   ```
   DATABASE_URL = postgresql://postgres:Sh%40220681@db.yczfxlqgkibpvemcfdbi.supabase.co:5432/postgres
   ```

### 4. Aguardar Deploy (2-3 minutos)

### 5. Acessar
Railway vai gerar uma URL tipo:
```
https://seu-app.up.railway.app
```

---

## Opção 2: Render.com

### Vantagens
- ✅ Gratuito
- ✅ SSL automático
- ✅ Deploy via GitHub

### Passos

1. **Criar conta:** https://render.com
2. **New Web Service**
3. **Conectar repositório GitHub**
4. **Configurar:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
5. **Adicionar variável:**
   - `DATABASE_URL` com a connection string

---

## Opção 3: Hugging Face Spaces

### Vantagens
- ✅ 100% gratuito
- ✅ Especializado em ML/Python apps
- ✅ Streamlit nativo

### Passos

1. Acesse: https://huggingface.co/spaces
2. Crie novo Space
3. Escolha "Streamlit" como SDK
4. Upload dos arquivos ou conecte GitHub
5. Adicione secrets em Settings

---

## Opção 4: Fly.io

### Vantagens
- ✅ Gratuito até 3 apps
- ✅ Rápido e confiável

### Criar arquivo fly.toml:

```toml
app = "sistema-lopes-ribeiro"

[build]
  builder = "paketobuildpacks/builder:base"

[[services]]
  internal_port = 8501
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

### Deploy:
```bash
flyctl launch
flyctl secrets set DATABASE_URL="postgresql://..."
flyctl deploy
```

---

## 🎯 MINHA RECOMENDAÇÃO: Railway

**Por quê?**
1. Mais simples de configurar
2. Gratuito e confiável
3. Deploy automático do GitHub
4. Suporte PostgreSQL nativo
5. SSL/HTTPS incluído

**Em 5 minutos está no ar!**

---

## ⚡ Teste Local Primeiro

Antes de fazer deploy, teste localmente com PostgreSQL:

```bash
# No terminal
set DATABASE_URL=postgresql://postgres:Sh%%40220681@db.yczfxlqgkibpvemcfdbi.supabase.co:5432/postgres
streamlit run app.py
```

Se funcionar local, vai funcionar no deploy!

---

## 🆘 Qual erro está dando no Streamlit Cloud?

Me conta o erro que posso te ajudar a resolver também!
