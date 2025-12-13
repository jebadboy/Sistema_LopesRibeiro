"""
LGPD Logger - Proteção Automática de Dados Sensíveis em Logs

Este módulo substitui o logging padrão por uma versão que automaticamente
mascara dados sensíveis (CPF, CNPJ, email, telefone, etc.) antes de gravar logs.

Conformidade LGPD:
- Art. 46: Tratamento adequado de dados pessoais
- Art. 48: Comunicação de incidentes de segurança
- Art. 50: Controladores devem adotar medidas de segurança

Uso:
    # Em vez de:
    import logging
    logger = logging.getLogger(__name__)
    
    # Use:
    import lgpd_logger
    logger = lgpd_logger.setup_lgpd_logger(__name__)
    
    # Agora CPFs, emails, etc serão mascarados automaticamente:
    logger.info(f"Cliente 123.456.789-00 cadastrado")
    # Output: "Cliente ***.***.***.** cadastrado"
"""

import logging
import re
from typing import Pattern, Tuple, List

class LGPDFormatter(logging.Formatter):
    """
    Formatter que automaticamente mascara dados sensíveis.
    
    Padrões mascarados:
    - CPF: 123.456.789-00 → ***.***.***.** 
    - CNPJ: 12.345.678/0001-00 → **.***.***/****-**
    - Email: nome@dominio.com → ***@***.***
    - Telefone: (21) 98765-4321 → (**) ****-****
    - Cartão: 1234 5678 9012 3456 → **** **** **** ****
    - Senha/Token: qualquer string após "senha:", "password:", "token:" → ****
    """
    
    # Padrões regex para detectar dados sensíveis
    PATTERNS: List[Tuple[str, Pattern, str]] = [
        # CPF (com ou sem formatação)
        ('cpf', re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'), '***.***.***.** '),
        
        # CNPJ (com ou sem formatação)
        ('cnpj', re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b'), '**.***.***/****-**'),
        
        # Email
        ('email', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '***@***.**'),
        
        # Telefone brasileiro (com ou sem DDD)
        ('telefone', re.compile(r'\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}|\b9?\d{4}-?\d{4}\b'), '(**) ****-****'),
        
        # Cartão de crédito
        ('cartao', re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '**** **** **** ****'),
        
        # CEP
        ('cep', re.compile(r'\b\d{5}-?\d{3}\b'), '*****-***'),
        
        # Senhas/Tokens (após keywords, inclui =)
        ('senha', re.compile(r'(senha|password|token|api_key|secret)[\s:=]+[^\s,}]+', re.IGNORECASE), r'\1: ****'),
        
        # Chaves de criptografia (qualquer string longa base64-like)
        ('chave', re.compile(r'\b[A-Za-z0-9+/]{32,}={0,2}\b'), '****[KEY_REDACTED]****'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formata o log e aplica máscaras em dados sensíveis.
        
        Args:
            record: Registro de log do Python
            
        Returns:
            String formatada com dados sensíveis mascarados
        """
        # Formatar o log normalmente primeiro
        msg = super().format(record)
        
        # Aplicar máscaras para cada padrão
        for pattern_name, regex, mask in self.PATTERNS:
            msg = regex.sub(mask, msg)
        
        return msg

def setup_lgpd_logger(
    name: str, 
    level: int = logging.INFO,
    format_string: str = None
) -> logging.Logger:
    """
    Cria logger com proteção LGPD automática.
    
    Args:
        name: Nome do logger (geralmente __name__)
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: String de formatação customizada (opcional)
        
    Returns:
        Logger configurado com mascaramento LGPD
        
    Exemplo:
        >>> logger = setup_lgpd_logger(__name__)
        >>> logger.info("Cliente CPF: 123.456.789-00")
        # Output: "Cliente CPF: ***.***.***.** "
    """
    logger = logging.getLogger(name)
    
    # Remover handlers existentes para evitar duplicação
    logger.handlers.clear()
    
    # Criar handler com formatter LGPD
    handler = logging.StreamHandler()
    
    # Formato padrão se não especificado
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handler.setFormatter(LGPDFormatter(format_string))
    
    logger.addHandler(handler)
    logger.setLevel(level)
    
    # Evitar propagação para evitar logging duplicado
    logger.propagate = False
    
    return logger

def patch_all_loggers(format_string: str = None):
    """
    Adiciona formatter LGPD a todos os loggers existentes no sistema.
    
    IMPORTANTE: Chamar esta função no início da aplicação (app.py) 
    para garantir que todos os módulos usem mascaramento LGPD.
    
    Args:
        format_string: Formato customizado (opcional)
        
    Exemplo:
        # No início do app.py:
        import lgpd_logger
        lgpd_logger.patch_all_loggers()
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = LGPDFormatter(format_string)
    
    # Pegar todos os loggers registrados
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    loggers.append(logging.getLogger())  # root logger
    
    # Aplicar formatter LGPD em todos os handlers
    for logger in loggers:
        for handler in logger.handlers:
            handler.setFormatter(formatter)
    
    # Configurar root logger
    logging.basicConfig(
        level=logging.INFO,
        format=format_string,
        handlers=[logging.StreamHandler()]
    )
    
    # Aplicar formatter no root logger também
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)

def mask_sensitive_data(text: str) -> str:
    """
    Mascara dados sensíveis em uma string qualquer.
    
    Útil para mascarar dados antes de exibir em UI ou salvar em arquivo.
    
    Args:
        text: Texto a ser mascarado
        
    Returns:
        Texto com dados sensíveis mascarados
        
    Exemplo:
        >>> mask_sensitive_data("Cliente João, CPF 123.456.789-00")
        'Cliente João, CPF ***.***.***.** '
    """
    if not text:
        return text
    
    masked = text
    
    # Aplicar mesmas máscaras do formatter
    for pattern_name, regex, mask in LGPDFormatter.PATTERNS:
        masked = regex.sub(mask, masked)
    
    return masked

# ========== TESTES UNITÁRIOS EMBUTIDOS ==========

def _test_lgpd_logger():
    """
    Testes automáticos de mascaramento.
    Executar: python lgpd_logger.py
    """
    print("[TESTE] Testando LGPD Logger...")
    
    test_cases = [
        ("CPF com pontos: 123.456.789-00", "***.***.***.** "),
        ("CPF sem pontos: 12345678900", "***.***.***.** "),
        ("CNPJ: 12.345.678/0001-00", "**.***.***/****-**"),
        ("Email: joao@exemplo.com.br", "***@***.**"),
        ("Telefone: (21) 98765-4321", "(**) ****-****"),
        ("Telefone sem DDD: 98765-4321", "(**) ****-****"),
        ("Cartao: 1234 5678 9012 3456", "**** **** **** ****"),
        ("CEP: 12345-678", "*****-***"),
        ("Senha: password=minhaSenha123", "password: ****"),
        ("API Key: api_key=sk_live_abc123xyz789", "api_key: ****"),
    ]
    
    logger = setup_lgpd_logger('test_logger')
    
    print("\n[CASOS] Testando mascaramento:")
    for original, esperado_conter in test_cases:
        masked = mask_sensitive_data(original)
        passou = esperado_conter in masked
        status = "[OK]" if passou else "[FAIL]"
        print(f"{status} {original[:30]:30} -> {masked[:40]}")
    
    print("\n[LOGGER] Testando logger real:")
    logger.info("Cliente Joao Silva, CPF: 123.456.789-00, Email: joao@gmail.com")
    logger.warning("Tentativa de login com senha=abc123 falhou")
    logger.error("Erro ao processar pagamento do cartao 1234 5678 9012 3456")
    
    print("\n[SUCESSO] Testes concluidos! Verifique se os dados foram mascarados acima.")

if __name__ == '__main__':
    _test_lgpd_logger()
