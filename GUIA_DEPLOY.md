# 🚀 Guia de Deploy - Lopes & Ribeiro System

## Passo 1: Subir para o GitHub

1. Abra o terminal no VS Code (Ctrl + ')
2. Execute os comandos:

```bash
git add .
git commit -m "Preparando sistema para deploy na nuvem"
git push origin main
```

---

## Passo 2: Deploy no Streamlit Cloud

### 2.1 Criar Conta
1. Acesse: https://streamlit.io/cloud
2. Clique em **"Sign up"**
3. Escolha **"Continue with GitHub"**
4. Autorize o Streamlit a acessar seus repositórios

### 2.2 Fazer Deploy
1. No painel do Streamlit Cloud, clique em **"New app"**
2. Preencha:
   - **Repository:** `jebadboy/Sistema_LopesRibeiro`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Clique em **"Advanced settings"**
4. Em **"Secrets"**, adicione:
   ```toml
   GOOGLE_API_KEY = "SUA_CHAVE_DO_GEMINI_AQUI"
   ```
5. Clique em **"Deploy!"**

---

## Passo 3: Aguardar (2-5 minutos)

O Streamlit Cloud vai:
- ✅ Instalar as dependências (`requirements.txt`)
- ✅ Configurar o ambiente
- ✅ Iniciar o app

Você receberá uma URL tipo:
```
https://lopesribeiro.streamlit.app
```

---

## ⚠️ IMPORTANTE: Banco de Dados na Nuvem

**PROBLEMA:** O SQLite atual não persiste dados na nuvem. A cada restart, os dados são perdidos.

**SOLUÇÃO (Opcional para Produção):**
Use um banco PostgreSQL gratuito:
- **Opção 1:** Neon (https://neon.tech) - 500MB grátis
- **Opção 2:** Supabase (https://supabase.com) - 500MB grátis

**Se quiser migrar para PostgreSQL, me avise que eu adapto o código!**

---

## 📱 Acessar de Qualquer Dispositivo

Depois do deploy, basta:
1. Abrir o navegador (PC/Tablet/Celular)
2. Acessar a URL do Streamlit Cloud
3. Usar normalmente!

**Não precisa instalar nada nos dispositivos.**

---

## 🔒 Segurança

- ✅ HTTPS automático (conexão segura)
- ✅ Chave API protegida (não fica no código)
- ⚠️ Qualquer pessoa com a URL pode acessar

**Para adicionar login/senha:**
- Posso implementar autenticação simples (usuário/senha)
- Ou usar Google Login

---

## 🆘 Problemas Comuns

### "ModuleNotFoundError"
→ Falta alguma biblioteca no `requirements.txt`

### "Secrets não encontrados"
→ Adicionar `GOOGLE_API_KEY` nos Secrets do Streamlit Cloud

### "App reiniciando sempre"
→ Verificar logs no painel do Streamlit Cloud

---

**Precisa de ajuda em algum passo? Me chame!**
