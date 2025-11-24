"""
Testes unitários para validações críticas do sistema Lopes & Ribeiro

Para executar:
    pytest test_validations.py -v

Para executar com cobertura:
    pytest test_validations.py --cov=. --cov-report=html
"""

import pytest
import sys
import os

# Adicionar o diretório pai ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import utils as ut
import database as db


class TestValidacaoCPF:
    """Testes para validação matemática de CPF"""
    
    def test_cpf_valido(self):
        """Testa CPFs válidos"""
        assert ut.validar_cpf_matematico("111.111.111-11") == False  # CPF com todos dígitos iguais
        assert ut.validar_cpf_matematico("123.456.789-09") == True   # CPF válido
        assert ut.validar_cpf_matematico("12345678909") == True      # CPF válido sem formatação
    
    def test_cpf_invalido_formato(self):
        """Testa CPFs com formato inválido"""
        assert ut.validar_cpf_matematico("123") == False
        assert ut.validar_cpf_matematico("") == False
        assert ut.validar_cpf_matematico("abc") == False
    
    def test_cpf_todos_digitos_iguais(self):
        """Testa CPFs com todos os dígitos iguais (inválidos)"""
        assert ut.validar_cpf_matematico("000.000.000-00") == False
        assert ut.validar_cpf_matematico("111.111.111-11") == False
        assert ut.validar_cpf_matematico("999.999.999-99") == False
    
    def test_cpf_digitos_verificadores(self):
        """Testa validação dos dígitos verificadores"""
        assert ut.validar_cpf_matematico("123.456.789-10") == False  # Dígito verificador errado
        assert ut.validar_cpf_matematico("123.456.789-00") == False  # Dígito verificador errado


class TestValidacaoEmail:
    """Testes para validação de email"""
    
    def test_email_valido(self):
        """Testa emails válidos"""
        assert ut.validar_email("teste@exemplo.com") == True
        assert ut.validar_email("usuario.nome@empresa.com.br") == True
        assert ut.validar_email("email123@dominio.org") == True
    
    def test_email_invalido(self):
        """Testa emails inválidos"""
        assert ut.validar_email("") == False
        assert ut.validar_email("semdominio") == False
        assert ut.validar_email("@semlocal.com") == False
        assert ut.validar_email("teste@") == False
        assert ut.validar_email("teste @exemplo.com") == False  # Espaço
    
    def test_email_none(self):
        """Testa email None"""
        assert ut.validar_email(None) == False


class TestValidacaoTelefone:
    """Testes para validação de telefone brasileiro"""
    
    def test_celular_valido(self):
        """Testa celulares válidos"""
        assert ut.validar_telefone("11987654321") == True    # SP
        assert ut.validar_telefone("21987654321") == True    # RJ
        assert ut.validar_telefone("(11) 98765-4321") == True # Formatado
    
    def test_fixo_valido(self):
        """Testa telefones fixos válidos"""
        assert ut.validar_telefone("1132123456") == True     # SP fixo
        assert ut.validar_telefone("(11) 3212-3456") == True # Formatado
    
    def test_telefone_invalido(self):
        """Testa telefones inválidos"""
        assert ut.validar_telefone("123") == False           # Muito curto
        assert ut.validar_telefone("00987654321") == False   # DDD inválido
        assert ut.validar_telefone("11887654321") == False   # Celular sem 9
        assert ut.validar_telefone("11987654321") == True    # Celular válido
        assert ut.validar_telefone("1192123456") == False    # Fixo com 9 no início
    
    def test_ddd_invalido(self):
        """Testa DDDs inválidos"""
        assert ut.validar_telefone("00987654321") == False
        assert ut.validar_telefone("90987654321") == False   # DDD 90 não existe


class TestFormatadores:
    """Testes para funções de formatação"""
    
    def test_limpar_numeros(self):
        """Testa remoção de caracteres não numéricos"""
        assert ut.limpar_numeros("123.456.789-09") == "12345678909"
        assert ut.limpar_numeros("(11) 98765-4321") == "11987654321"
        assert ut.limpar_numeros("abc123def456") == "123456"
        assert ut.limpar_numeros(None) == ""
    
    def test_formatar_cpf(self):
        """Testa formatação de CPF"""
        assert ut.formatar_cpf("12345678909") == "123.456.789-09"
        assert ut.formatar_cpf("123.456.789-09") == "123.456.789-09"  # Já formatado
        assert ut.formatar_cpf("123") == "123"  # Inválido, retorna como está
    
    def test_formatar_celular(self):
        """Testa formatação de telefone"""
        assert ut.formatar_celular("11987654321") == "(11) 98765-4321"
        assert ut.formatar_celular("1132123456") == "(11) 3212-3456"
        assert ut.formatar_celular("123") == "123"  # Inválido, retorna como está
    
    def test_formatar_moeda(self):
        """Testa formatação de valores monetários"""
        assert ut.formatar_moeda(1234.56) == "R$ 1.234,56"
        assert ut.formatar_moeda(0) == "R$ 0,00"
        assert ut.formatar_moeda("abc") == "R$ 0,00"  # Valor inválido


class TestFuncoesAuxiliares:
    """Testes para funções auxiliares"""
    
    def test_safe_float(self):
        """Testa conversão segura para float"""
        assert ut.safe_float("123.45") == 123.45
        assert ut.safe_float(100) == 100.0
        assert ut.safe_float("") == 0.0
        assert ut.safe_float(None) == 0.0
        assert ut.safe_float("abc") == 0.0
    
    def test_safe_int(self):
        """Testa conversão segura para int"""
        assert ut.safe_int("123") == 123
        assert ut.safe_int(100.5) == 100
        assert ut.safe_int("") == 1  # Retorna 1 por padrão (para parcelas)
        assert ut.safe_int(None) == 1
        assert ut.safe_int("abc") == 1


class TestDatabaseHelpers:
    """Testes para funções helper CRUD do database"""
    
    def test_tabelas_validas(self):
        """Testa constante de tabelas válidas"""
        assert 'clientes' in db.TABELAS_VALIDAS
        assert 'financeiro' in db.TABELAS_VALIDAS
        assert 'processos' in db.TABELAS_VALIDAS
        assert 'andamentos' in db.TABELAS_VALIDAS
    
    def test_sql_get_tabela_invalida(self):
        """Testa acesso a tabela inválida"""
        with pytest.raises(ValueError, match="Tabela inválida"):
            db.sql_get("tabela_inexistente")


# Configuração do pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
