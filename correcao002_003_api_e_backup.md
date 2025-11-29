# CORREÇÃO MANUAL #2 e #3: API Key + Backup Lock

# Arquivo detalhado com código correto para copiar/colar

## CORREÇÃO #2: Validação de API Key em utils.py

### Localização: utils.py, linhas 14-17

### ANTES

```python
import concurrent.futures

load_dotenv()
API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY")

def limpar_numeros(valor):
```

### DEPOIS (COPIE EXATAMENTE ASSIM)

```python
import concurrent.futures

load_dotenv()
API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY")

# Correção #2: Validação obrigatória de API Key no startup
if not API_KEY_GEMINI:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("GOOGLE_API_KEY não configurada!")
    raise ValueError("API Key do Google Gemini não encontrada no .env")

def limpar_numeros(valor):
```

---

## CORREÇÃO #3: Lock Thread-Safe em Backups - database.py

### Parte 1: Adicionar import

**Localização**: database.py, linha 1

#### ANTES

```python
import sqlite3
```

#### DEPOIS

```python
import threading  # ADICIONAR ESTA LINHA
import sqlite3
```

### Parte 2: Criar lock

**Localização**: database.py, após linha ~24 (após logger)

#### ADICIONAR APÓS

```python
logger = logging.getLogger(__name__)
```

#### NOVA LINHA

```python
# Correção #3: Lock thread-safe para backups
backup_lock = threading.Lock()
```

### Parte 3: Modificar função criar_backup()

**Localização**: database.py, função `criar_backup()` (~linha 47-61)

#### ANTES

```python
def criar_backup():
    """Cria backup manual do banco de dados."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    backup_name = f"{backup_dir}/backup_{timestamp}.db"
    try:
        shutil.copy(DB_NAME, backup_name)
        logger.info(f"Backup criado: {backup_name}")
        return f"Backup criado: {backup_name}"
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return f"Erro no backup: {e}"
```

#### DEPOIS (TODO O CÓDIGO dentro do with backup_lock)

```python
def criar_backup():
    """Cria backup manual do banco de dados com proteção thread-safe."""
    with backup_lock:  # ADICIONAR esta linha e indentar todo código abaixo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        backup_name = f"{backup_dir}/backup_{timestamp}.db"
        try:
            shutil.copy(DB_NAME, backup_name)
            logger.info(f"Backup criado: {backup_name}")
            return f"Backup criado: {backup_name}")
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return f"Erro no backup: {e}"
```

---

## CHECKLIST DE VERIFICAÇÃO

Após aplicar as correções, verifique:

### ✅ utils.py

1. [ ] `API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY")` definido ANTES do if
2. [ ] Bloco `if not API_KEY_GEMINI:` com raise ValueError
3. [ ] Import do logging dentro do if (para não dar circular import)

### ✅ database.py

1. [ ] `import threading` no topo
2. [ ] `backup_lock = threading.Lock()` após logger
3. [ ] `with backup_lock:` na primeira linha de criar_backup()
4. [ ] TODO o código da função indentado (4 espaços) dentro do with

### ✅ Teste rápido

```powershell
# No terminal:
python -m py_compile utils.py
python -m py_compile database.py

# Ambos devem compilar sem erros
```

---

## OBSERVAÇÃO IMPORTANTE

🔴 **ATENÇÃO À INDENTAÇÃO**: Python é sensível a espaços!

- Use **4 espaços** para cada nível de indentação
- O código dentro de `with backup_lock:` deve estar 4 espaços mais à direita
- Copie EXATAMENTE como mostrado acima

Se tiver dúvidas, consulte o arquivo `correcao001_sql_injection.py` como referência.
