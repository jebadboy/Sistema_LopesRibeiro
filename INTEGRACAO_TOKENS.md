# Guia Rápido - Integração Manual

## Arquivo 1: database.py

**Localização:** Linha ~182, dentro da função `init_db()`

**Adicionar após** `inicializar_tabelas_v2()`:

```python
# Inicializar tabela de tokens públicos
try:
    import token_manager
    token_manager.inicializar_tabela_tokens()
except Exception as e:
    logger.warning(f"Erro ao inicializar tokens públicos: {e}")
```

---

## Arquivo 2: modules/processos.py  

**Adicionar** no final da função que exibe detalhes do processo:

Veja código completo no [walkthrough.md](C:\\Users\\Micro\\.gemini\\antigravity\\brain\\29eeb403-3364-4559-beb1-e7d999c1a362\\walkthrough.md) seção "Passo 2"

---

## Testar

1. Restart o sistema: `streamlit run app.py`
2. Abra um processo
3. Clique em "Gerar Link Público"
4. Teste o link em: `streamlit run public_view.py`
