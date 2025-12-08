# -*- coding: utf-8 -*-
"""
Script para criar usuario admin inicial
"""

import sys
import os
import bcrypt

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def criar_usuario_admin():
    """Cria o usuário admin inicial se não existir"""
    
    try:
        import database as db
        
        print("Verificando usuario admin...")
        
        # Verificar se já existe um admin
        admin_existente = db.get_usuario_by_username('admin')
        
        if admin_existente:
            print("[INFO] Usuario 'admin' ja existe")
            print(f"Nome: {admin_existente['nome']}")
            print(f"Role: {admin_existente['role']}")
            print(f"Ativo: {'Sim' if admin_existente['ativo'] == 1 else 'Nao'}")
            
            resposta = input("\nDeseja resetar a senha para 'admin123'? (s/n): ")
            if resposta.lower() == 's':
                # Gerar novo hash bcrypt
                senha = "admin123"
                senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                
                # Atualizar senha
                db.sql_run("UPDATE usuarios SET password_hash = ? WHERE username = 'admin'", 
                          (senha_hash,))
                
                print("\n[SUCESSO] Senha resetada para: admin123")
                print("\nCredenciais de acesso:")
                print("Usuario: admin")
                print("Senha: admin123")
            else:
                print("\nOperacao cancelada")
            return
        
        # Criar novo usuario admin
        print("\n[INFO] Criando usuario admin inicial...")
        
        senha = "admin123"
        nome = "Administrador"
        
        # Gerar hash bcrypt da senha
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        
        # Inserir no banco
        db.sql_run("""
            INSERT INTO usuarios (username, password_hash, nome, role, ativo)
            VALUES (?, ?, ?, ?, ?)
        """, ('admin', senha_hash, nome, 'admin', 1))
        
        print("\n[SUCESSO] Usuario admin criado com sucesso!")
        print("\nCredenciais de acesso:")
        print("Usuario: admin")
        print("Senha: admin123")
        print("\nIMPORTANTE: Altere esta senha apos o primeiro login!")
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CRIACAO DE USUARIO ADMIN")
    print("=" * 60)
    print()
    
    sucesso = criar_usuario_admin()
    
    if sucesso:
        print("\nVoce pode agora fazer login no sistema com:")
        print("  Usuario: admin")
        print("  Senha: admin123")
    
    sys.exit(0 if sucesso else 1)
