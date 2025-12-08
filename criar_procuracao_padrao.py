import database as db
from docx import Document
import os

def importar_procuracao():
    print("Iniciando importação da Procuração Padrão...")
    
    docx_path = "teste_procuracao.docx"
    
    if not os.path.exists(docx_path):
        print(f"[ERRO] Arquivo não encontrado: {docx_path}")
        return

    try:
        # Ler o arquivo DOCX
        doc = Document(docx_path)
        texto_completo = []
        for para in doc.paragraphs:
            texto_completo.append(para.text)
            
        conteudo = "\n".join(texto_completo)
        
        # Salvar no banco
        # Primeiro, limpar se já existir um com esse nome para evitar duplicatas (opcional, mas bom pra teste)
        # Como não temos delete por nome fácil exposto, vamos apenas inserir.
        # Se quiser evitar duplicatas, poderia checar antes.
        
        db.salvar_modelo_documento(
            "Procuração Padrão",
            "Procuração",
            conteudo
        )
        
        print("[OK] Modelo 'Procuração Padrão' importado com sucesso!")
        
        # Verificar
        df = db.sql_get_query("SELECT * FROM modelos_documentos WHERE titulo = 'Procuração Padrão'")
        if not df.empty:
            print(f"[OK] Verificação: Encontrado ID {df.iloc[0]['id']}")
            print(f"--- Início do Conteúdo ---\n{df.iloc[0]['conteudo'][:200]}...\n--- Fim do Conteúdo ---")
        else:
            print("[ERRO] Verificação falhou: Modelo não encontrado no banco.")

    except Exception as e:
        print(f"[ERRO] Falha na importação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    importar_procuracao()
