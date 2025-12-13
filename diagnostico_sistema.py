"""
Diagnóstico do Sistema - Lopes & Ribeiro

Script consolidado para verificar a saúde do sistema.
Substitui os 16+ scripts de verificação que estavam na quarentena.

Uso:
    python diagnostico_sistema.py
    
    Ou com opções:
    python diagnostico_sistema.py --modulo database
    python diagnostico_sistema.py --completo
"""

import os
import sys
import importlib
from datetime import datetime

# Configura path do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def print_header(titulo: str):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 60)
    print(f"  {titulo}")
    print("=" * 60)


def print_result(nome: str, status: bool, detalhe: str = ""):
    """Imprime resultado de verificação."""
    icon = "[OK]" if status else "[X]"
    print(f"  {icon} {nome}: {'OK' if status else 'FALHA'} {detalhe}")


def verificar_dependencias() -> bool:
    """Verifica se todas as dependências estão instaladas."""
    print_header("1. VERIFICAÇÃO DE DEPENDÊNCIAS")
    
    dependencias = [
        'streamlit',
        'pandas',
        'bcrypt',
        'google.auth',
        'googleapiclient',
        'plotly'
    ]
    
    todas_ok = True
    for dep in dependencias:
        try:
            importlib.import_module(dep.split('.')[0])
            print_result(dep, True)
        except ImportError:
            print_result(dep, False, "(não instalado)")
            todas_ok = False
    
    return todas_ok


def verificar_arquivos_criticos() -> bool:
    """Verifica se arquivos críticos existem."""
    print_header("2. ARQUIVOS CRÍTICOS")
    
    arquivos = [
        'app.py',
        'database.py',
        'utils.py',
        'requirements.txt',
        '.env',
        'dados_escritorio.db'
    ]
    
    todos_ok = True
    for arquivo in arquivos:
        caminho = os.path.join(BASE_DIR, arquivo)
        existe = os.path.exists(caminho)
        if existe and arquivo.endswith('.db'):
            tamanho = os.path.getsize(caminho)
            print_result(arquivo, existe, f"({tamanho / 1024:.1f} KB)")
        else:
            print_result(arquivo, existe)
        if not existe:
            todos_ok = False
    
    return todos_ok


def verificar_modulos() -> bool:
    """Verifica sintaxe de todos os módulos."""
    print_header("3. SINTAXE DOS MÓDULOS")
    
    modules_dir = os.path.join(BASE_DIR, 'modules')
    todos_ok = True
    
    for arquivo in os.listdir(modules_dir):
        if arquivo.endswith('.py') and not arquivo.startswith('__'):
            caminho = os.path.join(modules_dir, arquivo)
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, caminho, 'exec')
                print_result(arquivo, True)
            except SyntaxError as e:
                print_result(arquivo, False, f"(Linha {e.lineno}: {e.msg})")
                todos_ok = False
            except Exception as e:
                print_result(arquivo, False, f"({str(e)[:50]})")
                todos_ok = False
    
    return todos_ok


def verificar_database() -> bool:
    """Verifica conexão e tabelas do banco de dados."""
    print_header("4. BANCO DE DADOS")
    
    try:
        import database as db
        
        # Inicializar
        db.init_db()
        print_result("Inicialização", True)
        
        # Verificar tabelas principais
        tabelas = [
            'usuarios', 'clientes', 'processos', 'financeiro',
            'agenda', 'parceiros', 'andamentos', 'modelos_documentos'
        ]
        
        todas_ok = True
        for tabela in tabelas:
            try:
                df = db.sql_get(tabela)
                count = len(df)
                print_result(f"Tabela {tabela}", True, f"({count} registros)")
            except Exception as e:
                print_result(f"Tabela {tabela}", False, f"({str(e)[:30]})")
                todas_ok = False
        
        return todas_ok
        
    except Exception as e:
        print_result("Conexão", False, f"({str(e)[:50]})")
        return False


def verificar_google_apis() -> bool:
    """Verifica conexão com APIs do Google."""
    print_header("5. GOOGLE APIS")
    
    apis_ok = True
    
    # Google Drive
    try:
        import google_drive as gd
        service = gd.autenticar()
        if service:
            print_result("Google Drive", True, "(Autenticado)")
        else:
            print_result("Google Drive", False, "(Falha na autenticação)")
            apis_ok = False
    except Exception as e:
        print_result("Google Drive", False, f"({str(e)[:40]})")
        apis_ok = False
    
    # Google Calendar
    try:
        import google_calendar as gc
        # Apenas verificar importação
        print_result("Google Calendar", True, "(Módulo OK)")
    except Exception as e:
        print_result("Google Calendar", False, f"({str(e)[:40]})")
        apis_ok = False
    
    return apis_ok


def verificar_logs() -> bool:
    """Verifica configuração de logs."""
    print_header("6. SISTEMA DE LOGS")
    
    logs_dir = os.path.join(BASE_DIR, 'logs')
    
    if os.path.exists(logs_dir):
        arquivos_log = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        print_result("Diretório logs/", True, f"({len(arquivos_log)} arquivo(s))")
        
        for log_file in arquivos_log:
            caminho = os.path.join(logs_dir, log_file)
            tamanho = os.path.getsize(caminho)
            print_result(f"  {log_file}", True, f"({tamanho / 1024:.1f} KB)")
        
        return True
    else:
        print_result("Diretório logs/", False, "(não existe, será criado na execução)")
        return True  # Não é erro crítico


def gerar_relatorio() -> dict:
    """Gera relatório completo de diagnóstico."""
    print("\n" + "=" * 60)
    print("  DIAGNOSTICO DO SISTEMA - LOPES & RIBEIRO")
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    
    resultados = {
        'dependencias': verificar_dependencias(),
        'arquivos': verificar_arquivos_criticos(),
        'modulos': verificar_modulos(),
        'database': verificar_database(),
        'google_apis': verificar_google_apis(),
        'logs': verificar_logs()
    }
    
    # Resumo final
    print_header("RESUMO FINAL")
    
    total = len(resultados)
    ok = sum(1 for v in resultados.values() if v)
    
    print(f"\n  Verificações: {ok}/{total}")
    
    if ok == total:
        print("\n  [OK] SISTEMA SAUDAVEL - Todas as verificacoes passaram!")
    else:
        print("\n  [!] ATENCAO - Algumas verificacoes falharam.")
        print("  Verifique os itens marcados com [X] acima.")
    
    print("\n" + "=" * 60)
    
    return resultados


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnóstico do Sistema Lopes & Ribeiro')
    parser.add_argument('--modulo', help='Verificar módulo específico')
    parser.add_argument('--completo', action='store_true', help='Verificação completa')
    
    args = parser.parse_args()
    
    if args.modulo:
        print(f"Verificando módulo: {args.modulo}")
        if args.modulo == 'database':
            verificar_database()
        elif args.modulo == 'modulos':
            verificar_modulos()
        elif args.modulo == 'apis':
            verificar_google_apis()
        else:
            print(f"Módulo '{args.modulo}' não reconhecido.")
            print("Opções: database, modulos, apis")
    else:
        gerar_relatorio()
