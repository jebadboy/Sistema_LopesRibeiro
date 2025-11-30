# 🚀 Guia de Publicação do Sistema Lopes & Ribeiro

## 📋 Índice
1. [Opções de Deploy](#opções-de-deploy)
2. [Opção Recomendada: Streamlit Cloud](#opção-1-streamlit-cloud-recomendado)
3. [Opção Alternativa: ngrok](#opção-2-ngrok-acesso-temporário)
4. [Configurações Importantes](#configurações-importantes)

---

## Opções de Deploy

| Opção | Custo | Dificuldade | Permanente | Recomendado |
|-------|-------|-------------|------------|-------------|
| **Streamlit Cloud** | Gratuito | ⭐ Fácil | ✅ Sim | ✅ **SIM** |
| **ngrok** | Gratuito | ⭐ Muito Fácil | ❌ Não | Para testes |
| **VPS** | $6-12/mês | ⭐⭐⭐ Difícil | ✅ Sim | Prod. |

---

## Opção 1: Streamlit Cloud (RECOMENDADO) 🌟

### ✅ Vantagens
- **100% GRATUITO** para projetos privados
- Acesso de qualquer lugar (PC, celular, tablet)
- URL personalizada: `https://seu-app.streamlit.app`
- Deploy automático via GitHub
- SSL/HTTPS incluído

### 📝 Passo a Passo

#### 1. Preparar o Projeto

**a) Verificar `requirements.txt`:**
```txt
streamlit
pandas
plotly
openpyxl
google-generativeai
```

**b) Criar `.streamlit/config.toml`:**
```toml
[theme]
primaryColor = "#0066cc"
backgroundColor = "#ffffff"

[server]
headless = true
port = 8501
```

**c) Atualizar `.gitignore`:**
```
*.db
*.log
__pycache__/
.env
backups/
```

#### 2. Subir para GitHub

```bash
cd "H:\Meu Drive\automatizacao\Sistema_LopesRibeiro"
git add .
git commit -m "Preparando para deploy"
git push origin main
```

#### 3. Deploy no Streamlit Cloud

1. Acesse https://streamlit.io/cloud
2. Clique em "Sign in with GitHub"
3. Clique em "New app"
4. Selecione:
   - Repository: `jebadboy/Sistema_LopesRibeiro`
   - Branch: `main`
   - Main file: `app.py`
5. Clique em "Deploy!"

**🎉 Pronto! Aguarde 2-5 minutos**

Você receberá uma URL como:
```
https://sistema-lopes-ribeiro.streamlit.app
```

---

## Opção 2: ngrok (Acesso Temporário) ⚡

### Para testes rápidos ou demonstrações

#### 1. Instalar ngrok
Baixe em: https://ngrok.com/download

#### 2. Configurar token
```bash
ngrok config add-authtoken SEU_TOKEN
```

#### 3. Iniciar sistema local
```bash
streamlit run app.py
```

#### 4. Em outro terminal, criar túnel
```bash
ngrok http 8501
```

#### 5. Acessar URL fornecida
```
https://xxxx.ngrok-free.app
```

⚠️ **Limitações:**
- URL muda a cada reinício
- Não é permanente

---

##Configurações Importantes ⚙️

### ⚠️ Banco de Dados em Produção

**PROBLEMA:** SQLite não persiste dados na nuvem (Streamlit Cloud reinicia diariamente)

**SOLUÇÕES:**

**Opção A - Continuar com SQLite (Simples)**
- Aceitar que dados são temporários
- Fazer backup manual regularmente
- Ideal para testes

**Opção B - Migrar para PostgreSQL (Recomendado)**
- Use serviço gratuito:
  - **Supabase** (500MB grátis)
  - **Neon** (500MB grátis)
- Dados permanentes
- Ideal para produção

### 🔒 Proteger Acesso

O sistema já tem login integrado (admin/admin123).

**Para produção:**
1. Mude a senha padrão
2. Considere adicionar autenticação do Google

---

## 📱 Acesso nos Dispositivos

### PC/Laptop
Abra qualquer navegador e acesse a URL

### Celular/Tablet
1. Abra no navegador (Chrome/Safari)
2. Menu > "Adicionar à tela inicial"
3. Ícone aparecerá como um app!

---

## ✅ Checklist de Deploy

- [ ] `requirements.txt` completo
- [ ] `.gitignore` configurado
- [ ] Código no GitHub
- [ ] Deploy no Streamlit Cloud
- [ ] Teste de acesso

---

## 🆘 Problemas Comuns

**"ModuleNotFoundError"**
→ Adicione a biblioteca em `requirements.txt`

**App reiniciando**
→ Verifique logs no Streamlit Cloud

**Banco de dados vazio após reiniciar**
→ Normal com SQLite. Migre para PostgreSQL

---

**🎉 Sistema publicado com sucesso!**

Para PostgreSQL ou customizações, me avise!
