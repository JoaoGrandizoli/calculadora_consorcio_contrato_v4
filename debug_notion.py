"""
Script para debugar e analisar o database Notion
"""
import os
import asyncio
from notion_client import Client as NotionClient

# Configurações
NOTION_API_KEY = "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"
NOTION_DATABASE_ID = "279482de1c1880ed8822c87a95395806"

async def analisar_notion_database():
    """Analisar completamente o database Notion"""
    try:
        # Inicializar cliente
        client = NotionClient(auth=NOTION_API_KEY)
        
        print("🔍 ANALISANDO DATABASE NOTION...")
        print(f"📋 Database ID: {NOTION_DATABASE_ID}")
        print("=" * 60)
        
        # 1. Obter estrutura do database
        print("\n📊 ESTRUTURA DO DATABASE:")
        try:
            database_info = client.databases.retrieve(database_id=NOTION_DATABASE_ID)
            
            print(f"📝 Nome: {database_info.get('title', [{}])[0].get('plain_text', 'Sem nome')}")
            print(f"🆔 ID: {database_info.get('id')}")
            print(f"📅 Criado em: {database_info.get('created_time')}")
            print(f"🔄 Editado em: {database_info.get('last_edited_time')}")
            
            # Listar propriedades (colunas)
            properties = database_info.get('properties', {})
            print(f"\n🔧 PROPRIEDADES/COLUNAS ({len(properties)} encontradas):")
            for prop_name, prop_config in properties.items():
                prop_type = prop_config.get('type', 'unknown')
                print(f"  - {prop_name}: {prop_type}")
            
        except Exception as e:
            print(f"❌ Erro ao obter estrutura: {e}")
            return
        
        # 2. Consultar registros existentes
        print("\n📄 CONTEÚDO DO DATABASE:")
        try:
            query_result = client.databases.query(
                database_id=NOTION_DATABASE_ID,
                page_size=10  # Primeiros 10 registros
            )
            
            results = query_result.get('results', [])
            print(f"📊 Total de registros encontrados: {len(results)}")
            
            if results:
                print("\n📋 REGISTROS EXISTENTES:")
                for i, page in enumerate(results, 1):
                    print(f"\n--- REGISTRO {i} ---")
                    print(f"🆔 Page ID: {page.get('id')}")
                    print(f"📅 Criado: {page.get('created_time')}")
                    
                    # Extrair dados das propriedades
                    page_properties = page.get('properties', {})
                    print("📋 Dados:")
                    for prop_name, prop_data in page_properties.items():
                        prop_type = prop_data.get('type')
                        value = extrair_valor_propriedade(prop_data)
                        print(f"  {prop_name} ({prop_type}): {value}")
                        
            else:
                print("📭 Nenhum registro encontrado no database")
                
        except Exception as e:
            print(f"❌ Erro ao consultar registros: {e}")
        
        # 3. Testar criação de um registro
        print("\n🧪 TESTANDO CRIAÇÃO DE REGISTRO:")
        try:
            test_properties = {
                "Nome Completo": {
                    "title": [{"text": {"content": "Teste Debug Notion"}}]
                }
            }
            
            # Verificar se outras propriedades existem e adicionar
            if "Email" in properties:
                if properties["Email"].get("type") == "email":
                    test_properties["Email"] = {"email": "teste@debug.com"}
                elif properties["Email"].get("type") == "rich_text":
                    test_properties["Email"] = {"rich_text": [{"text": {"content": "teste@debug.com"}}]}
            
            if "Nome" in properties:
                test_properties["Nome"] = {"rich_text": [{"text": {"content": "Teste"}}]}
                
            if "Sobrenome" in properties:
                test_properties["Sobrenome"] = {"rich_text": [{"text": {"content": "Debug"}}]}
                
            if "Telefone" in properties:
                if properties["Telefone"].get("type") == "phone_number":
                    test_properties["Telefone"] = {"phone_number": "(11) 99999-9999"}
                elif properties["Telefone"].get("type") == "rich_text":
                    test_properties["Telefone"] = {"rich_text": [{"text": {"content": "(11) 99999-9999"}}]}
                    
            if "Profissão" in properties:
                test_properties["Profissão"] = {"rich_text": [{"text": {"content": "Desenvolvedor"}}]}
            
            print(f"📝 Tentando criar com propriedades: {list(test_properties.keys())}")
            
            create_result = client.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties=test_properties
            )
            
            print(f"✅ Registro teste criado com sucesso!")
            print(f"🆔 ID: {create_result.get('id')}")
            
        except Exception as e:
            print(f"❌ Erro ao criar registro teste: {e}")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")

def extrair_valor_propriedade(prop_data):
    """Extrair valor legível de uma propriedade Notion"""
    prop_type = prop_data.get('type')
    
    if prop_type == 'title':
        titles = prop_data.get('title', [])
        return ' '.join([t.get('plain_text', '') for t in titles]) if titles else ''
        
    elif prop_type == 'rich_text':
        texts = prop_data.get('rich_text', [])
        return ' '.join([t.get('plain_text', '') for t in texts]) if texts else ''
        
    elif prop_type == 'email':
        return prop_data.get('email', '')
        
    elif prop_type == 'phone_number':
        return prop_data.get('phone_number', '')
        
    elif prop_type == 'select':
        select_data = prop_data.get('select')
        return select_data.get('name', '') if select_data else ''
        
    elif prop_type == 'date':
        date_data = prop_data.get('date')
        return date_data.get('start', '') if date_data else ''
        
    elif prop_type == 'number':
        return prop_data.get('number', '')
        
    elif prop_type == 'checkbox':
        return prop_data.get('checkbox', False)
        
    else:
        return f"[{prop_type}] {str(prop_data)[:50]}..."

if __name__ == "__main__":
    asyncio.run(analisar_notion_database())