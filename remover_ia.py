"""
Script de Remoção Automática do Módulo IA Jurídica
Execução: python remover_ia.py
"""

import re

def remover_ia_do_sistema():
    """Remove módulo de IA do sistema de forma segura"""
    
    print("[INICIO] Iniciando remocao do modulo IA Juridica...")
    
    # 1. Atualizar app.py - Remover menu IA
    print("\n1️⃣  Atualizando app.py...")
    try:
        with open("app.py", "r", encoding="utf-8") as f:
            conteudo = f.read()
        
        # Remover "IA Jurídica" do menu
        conteudo = conteudo.replace(
            '["Clientes", "Financeiro", "Processos", "Agenda", "IA Jurídica", "Painel Geral"]',
            '["Clientes", "Financeiro", "Processos", "Agenda", "Painel Geral"]'
        )
        
        # Remover seção inteira de IA Jurídica
        pattern = r'# ==========================================\r?\n# 5\. IA JURÍDICA\r?\n# ==========================================.*?# ==========================================\r?\n# 6\. PAINEL GERAL\r?\n# =========================================='
        replacement = '# ==========================================\n# 5. PAINEL GERAL\n# =========================================='
        conteudo = re.sub(pattern, replacement, conteudo, flags=re.DOTALL)
        
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(conteudo)
        
        print("   ✅ app.py atualizado")
    except Exception as e:
        print(f"   ❌ Erro ao atualizar app.py: {e}")
        return False
    
    # 2. Atualizar utils.py - Remover funções de IA
    print("\n2️⃣  Atualizando utils.py...")
    try:
        with open("utils.py", "r", encoding="utf-8") as f:
            conteudo = f.read()
        
        # Remover imports da IA
        imports_remover = [
            "import google.generativeai as genai\n",
            "from dotenv import load_dotenv\n",
            "import concurrent.futures\n"
        ]
        
        for imp in imports_remover:
            conteudo = conteudo.replace(imp, "")
        
        # Remover carregamento do .env e API_KEY
        pattern_env = r'load_dotenv\(\).*?API_KEY_GEMINI = os\.getenv\("GOOGLE_API_KEY"\)\r?\n'
        conteudo = re.sub(pattern_env, "", conteudo, flags=re.DOTALL)
        
        # Remover funções de IA
        pattern_obter = r'def obter_modelo_ativo\(\):.*?except: return \'gemini-flash-latest\'\r?\n\r?\n'
        conteudo = re.sub(pattern_obter, "", conteudo, flags=re.DOTALL)
        
        pattern_consultar = r'def consultar_ia\(prompt, timeout=30\):.*?return f"❌ \*\*Erro inesperado\*\*: {str\(e\)\[:100\]}"\r?\n\r?\n'
        conteudo = re.sub(pattern_consultar, "", conteudo, flags=re.DOTALL)
        
        with open("utils.py", "w", encoding="utf-8") as f:
            f.write(conteudo)
        
        print("   ✅ utils.py atualizado")
    except Exception as e:
        print(f"   ❌ Erro ao atualizar utils.py: {e}")
        return False
    
    # 3. Atualizar requirements.txt - Remover dependências da IA
    print("\n3️⃣  Atualizando requirements.txt...")
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            linhas = f.readlines()
        
        # Remover dependências de IA
        dependencias_remover = ["google-generativeai", "python-dotenv"]
        linhas_filtradas = [
            linha for linha in linhas 
            if not any(dep in linha.lower() for dep in dependencias_remover)
        ]
        
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.writelines(linhas_filtradas)
        
        print("   ✅ requirements.txt atualizado")
    except Exception as e:
        print(f"   ❌ Erro ao atualizar requirements.txt: {e}")
        return False
    
    print("\n✨ Remoção concluída com sucesso!")
    print("\n📋 Resumo das alterações:")
    print("   - Removido menu 'IA Jurídica' do app.py")
    print("   - Removida seção completa de IA em app.py")
    print("   - Removidas funções consultar_ia() e obter_modelo_ativo() em utils.py")
    print("   - Removidos imports google.generativeai, dotenv e concurrent.futures")
    print("   - Removidas dependências google-generativeai e python-dotenv")
    print("\n🔄 Próximos passos:")
    print("   1. Testar o sistema: streamlit run app.py")
    print("   2. Se funcionar, fazer commit: git add . && git commit -m 'Removido módulo IA Jurídica'")
    
    return True

if __name__ == "__main__":
    sucesso = remover_ia_do_sistema()
    if not sucesso:
        print("\n⚠️  Houve erros durante a remoção. Verifique os arquivos manualmente.")
    else:
        print("\n✅ Sistema pronto para uso sem IA!")
