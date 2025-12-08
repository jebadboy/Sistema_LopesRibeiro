# 🚀 Guia de Deploy no Render (Gratuito & Recomendado)

Como o **Streamlit Cloud** está bloqueando e o **Railway** é pago, a melhor opção gratuita e compatível com o nosso sistema (Streamlit + Supabase) é o **Render**.

O Render possui um plano "Web Service" gratuito que suporta Python e mantém a conexão ativa (necessário para o Streamlit), diferente da Vercel que derruba a conexão.

## 📋 Pré-requisitos

1. Seu código no **GitHub**.
2. Sua URL de conexão do **Supabase** (que você já tem).
3. Conta no [Render.com](https://render.com/).

---

## 🛠️ Passo 1: Criar Web Service no Render

1. Acesse o [Dashboard do Render](https://dashboard.render.com/).
2. Clique em **"New +"** e selecione **"Web Service"**.
3. Conecte sua conta do GitHub e selecione o repositório `Sistema_LopesRibeiro`.
4. Preencha os campos:
    * **Name:** `sistema-lopes-ribeiro` (ou outro de sua preferência)
    * **Region:** Escolha a mais próxima (ex: Ohio ou Frankfurt - infelizmente não tem BR no free).
    * **Branch:** `main`
    * **Runtime:** `Python 3`
    * **Build Command:** `pip install -r requirements.txt`
    * **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
    * **Instance Type:** Selecione **"Free"**.

---

## 🔑 Passo 2: Configurar Variáveis de Ambiente

Role para baixo até a seção **"Environment Variables"** e adicione:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.9.12` (ou `3.10.0`) |
| `DATABASE_URL` | Cole sua URL do Supabase aqui (`postgresql://...`) |
| `GEMINI_API_KEY` | Sua chave da IA (se estiver usando) |

> **Importante:** A variável `DATABASE_URL` é o que diz ao sistema para usar o Supabase em vez do arquivo local.

---

## 🚀 Passo 3: Finalizar Deploy

1. Clique em **"Create Web Service"**.
2. Aguarde o processo de build (pode levar alguns minutos na primeira vez).
3. Acompanhe os logs. Se aparecer "You can now view your Streamlit app in your browser", deu certo!
4. O link do seu sistema estará no topo da página (ex: `https://sistema-lopes-ribeiro.onrender.com`).

---

## ⚠️ Limitações do Plano Gratuito

* **Spin Down:** Se ninguém acessar o sistema por 15 minutos, ele "dorme". O próximo acesso vai demorar uns 50 segundos para carregar. Para uso interno do escritório, isso geralmente não é problema.
* **Performance:** É um pouco mais lento que o pago, mas suficiente para uso normal.

---

## ❓ Por que não Vercel?

A Vercel é excelente para sites estáticos (Next.js, React), mas **péssima para Streamlit**.

1. **Websockets:** O Streamlit precisa de uma conexão constante. A Vercel corta conexões após 10-60 segundos, fazendo o app reiniciar na cara do usuário.
2. **Estado:** A Vercel não mantém a memória do servidor. Cada clique pode cair em um servidor diferente, perdendo o login e as variáveis do sistema.
