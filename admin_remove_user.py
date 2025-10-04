#!/usr/bin/env python3
"""
Script Administrativo - Remover Usuário do Sistema
=========================================

Este script permite remover um usuário específico do MongoDB
para permitir que ele se recadestre com o mesmo email.

USO:
python3 admin_remove_user.py usuario@email.com

IMPORTANTE:
- Use apenas quando o usuário solicitar reset de senha via contato@caremfo.com
- Confirme a identidade do usuário antes de executar
- Este script remove PERMANENTEMENTE o usuário do banco
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def remover_usuario(email):
    """Remove um usuário específico do banco de dados"""
    
    # Conectar ao MongoDB
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'consorcio_db')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print(f"🔍 Procurando usuário: {email}")
        
        # Verificar se usuário existe
        user = await db.leads.find_one({"email": email})
        
        if not user:
            print(f"❌ Usuário {email} não encontrado no banco de dados.")
            return False
        
        print(f"✅ Usuário encontrado:")
        print(f"   - Nome: {user.get('nome', 'N/A')} {user.get('sobrenome', 'N/A')}")
        print(f"   - Email: {user.get('email', 'N/A')}")
        print(f"   - Cadastrado em: {user.get('created_at', 'N/A')}")
        print(f"   - ID: {user.get('id', 'N/A')}")
        
        # Confirmação de segurança
        print(f"\n⚠️  ATENÇÃO: Esta operação é IRREVERSÍVEL!")
        confirmacao = input(f"Deseja realmente remover o usuário {email}? (digite 'CONFIRMAR'): ")
        
        if confirmacao != 'CONFIRMAR':
            print("❌ Operação cancelada.")
            return False
        
        # Remover usuário
        resultado = await db.leads.delete_one({"email": email})
        
        if resultado.deleted_count > 0:
            print(f"✅ Usuário {email} removido com sucesso!")
            print(f"📝 Log: {datetime.now().isoformat()} - Usuário {email} removido pelo admin")
            return True
        else:
            print(f"❌ Erro ao remover usuário {email}")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante a operação: {str(e)}")
        return False
    finally:
        client.close()

async def listar_usuarios():
    """Lista todos os usuários no banco (para referência)"""
    
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'consorcio_db')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print("📋 Listando todos os usuários:")
        print("-" * 50)
        
        async for user in db.leads.find({}):
            print(f"Email: {user.get('email', 'N/A')}")
            print(f"Nome: {user.get('nome', 'N/A')} {user.get('sobrenome', 'N/A')}")
            print(f"Cadastro: {user.get('created_at', 'N/A')}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {str(e)}")
    finally:
        client.close()

def main():
    """Função principal do script"""
    
    if len(sys.argv) < 2:
        print("❌ Uso incorreto!")
        print("   Para remover usuário: python3 admin_remove_user.py usuario@email.com")
        print("   Para listar usuários: python3 admin_remove_user.py --list")
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == "--list":
        print("🔍 Listando usuários no banco de dados...")
        asyncio.run(listar_usuarios())
    elif "@" in comando:  # Parece ser um email
        email = comando.lower().strip()
        print(f"🗑️  Iniciando remoção do usuário: {email}")
        sucesso = asyncio.run(remover_usuario(email))
        
        if sucesso:
            print(f"\n✅ CONCLUÍDO: Usuário {email} pode agora se recadastrar.")
        else:
            print(f"\n❌ FALHA: Não foi possível remover o usuário {email}.")
    else:
        print("❌ Formato inválido! Use um email válido ou --list")
        sys.exit(1)

if __name__ == "__main__":
    main()