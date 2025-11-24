# Instruções para Instalação de Dependências

## Dependências do Projeto

```bash
pip install streamlit pandas openpyxl google-generativeai python-docx PyPDF2 requests pytest pytest-cov
```

## Dependências Individuais

- `streamlit` - Framework web para interface
- `pandas` - Manipulação de dados
- `openpyxl` - Exportação para Excel
- `google-generativeai` - IA Gemini
- `python-docx` - Geração de documentos Word
- `PyPDF2` - Leitura de PDFs
- `requests` - Requisições HTTP (ViaCEP)
- `pytest` - Testes unitários
- `pytest-cov` - Cobertura de testes

## Executar Testes

```bash
# Executar todos os testes
pytest test_validations.py -v

# Executar com cobertura
pytest test_validations.py --cov=. --cov-report=html

# Executar teste específico
pytest test_validations.py::TestValidacaoCPF::test_cpf_valido -v
```

## Executar Aplicação

```bash
streamlit run app.py
```
