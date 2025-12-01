# 🛡️ Guia de Recuperação do Sistema (Recovery Point)

Este documento descreve como restaurar o **Sistema Lopes & Ribeiro** para um ponto estável em caso de falhas críticas.

## 📅 Ponto de Recuperação Atual

**Versão:** Stable Release v1.0
**Status:** Funcional e Testado
**Data:** 01/12/2025

---

## 📂 Onde estão os backups?

O sistema gera backups automáticos em dois locais principais:

1. **Pasta `backups/`**: Contém arquivos `.zip` com o código-fonte e o banco de dados.
2. **Git (Controle de Versão)**: O histórico de alterações está salvo no repositório local.

---

## 🆘 Como Restaurar o Sistema

### Opção 1: Restaurar via Backup ZIP (Recomendado para usuários)

Se o sistema quebrou e você precisa voltar para a versão anterior:

1. Acesse a pasta `backups/` no diretório do projeto.
2. Localize o arquivo ZIP mais recente (ex: `backup_sistema_20251201_090000.zip`).
3. Descompacte o conteúdo.
4. Copie todos os arquivos descompactados e **substitua** os arquivos na pasta raiz do projeto (`g:\Meu Drive\automatizacao\Sistema_LopesRibeiro`).
5. Reinicie o sistema:

    ```bash
    streamlit run app.py
    ```

### Opção 2: Restaurar via Git (Para desenvolvedores)

Se você tem familiaridade com terminal:

1. Abra o terminal na pasta do projeto.
2. Verifique o status:

    ```bash
    git status
    ```

3. Para descartar alterações recentes e voltar ao último commit estável:

    ```bash
    git reset --hard HEAD
    ```

    *(Cuidado: Isso apaga qualquer alteração não salva)*

---

## 💾 Como Criar um Novo Ponto de Recuperação

Sempre que o sistema estiver estável, você pode criar um novo ponto de recuperação manualmente:

1. Execute o script de backup:

    ```bash
    python create_backup.py
    ```

2. Isso criará um novo arquivo ZIP na pasta `backups/` com a data e hora atuais.

---

## 🗄️ Recuperação Apenas do Banco de Dados

Se o problema for apenas dados corrompidos ou apagados acidentalmente:

1. Acesse a pasta `backups/`.
2. Procure por arquivos `.db` (ex: `backup_20251201.db`).
3. Renomeie o arquivo para `dados_escritorio.db`.
4. Mova-o para a pasta raiz, substituindo o arquivo atual.
