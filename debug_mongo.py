"""
Script para debugar e visualizar dados do MongoDB
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime
import json

# Configurações do MongoDB (mesmas do backend)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "consorcio_db"

async def analisar_mongodb():
    """Analisar completamente o banco MongoDB"""
    try:
        # Conectar ao MongoDB
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        print("🔍 ANALISANDO BANCO MONGODB...")
        print(f"📋 URL: {MONGO_URL}")
        print(f"🗄️  Database: {DB_NAME}")
        print("=" * 80)
        
        # 1. Listar todas as coleções
        print("\n📊 COLEÇÕES EXISTENTES:")
        collections = await db.list_collection_names()
        for i, collection in enumerate(collections, 1):
            count = await db[collection].count_documents({})
            print(f"  {i}. {collection} ({count} documentos)")
        
        if not collections:
            print("❌ Nenhuma coleção encontrada!")
            return
        
        # 2. Analisar coleção LEADS
        if "leads" in collections:
            print("\n👥 COLEÇÃO 'leads':")
            leads_cursor = db.leads.find({}).sort("created_at", -1)  # Mais recentes primeiro
            leads = await leads_cursor.to_list(length=10)  # Primeiros 10
            
            print(f"📊 Total de leads: {await db.leads.count_documents({})}")
            
            if leads:
                for i, lead in enumerate(leads, 1):
                    print(f"\n--- LEAD {i} ---")
                    print(f"🆔 ID: {lead.get('id', 'N/A')}")
                    print(f"👤 Nome: {lead.get('nome', '')} {lead.get('sobrenome', '')}")
                    print(f"📧 Email: {lead.get('email', 'N/A')}")
                    print(f"📱 Telefone: {lead.get('telefone', 'N/A')}")
                    print(f"💼 Profissão: {lead.get('profissao', 'N/A')}")
                    print(f"🔑 Token: {lead.get('access_token', 'N/A')[:20]}...")
                    print(f"🔐 Tem senha: {'Sim' if lead.get('senha_hash') else 'Não'}")
                    print(f"📅 Criado em: {lead.get('created_at', 'N/A')}")
                    print(f"🔗 Fonte: {lead.get('source', 'N/A')}")
                    
                    # Verificar se há simulações associadas
                    if lead.get('access_token'):
                        sim_count = await db.simulations.count_documents({"access_token_usado": lead.get('access_token')})
                        print(f"📈 Simulações: {sim_count}")
            else:
                print("📭 Nenhum lead encontrado")
        
        # 3. Analisar coleção SIMULATIONS
        if "simulations" in collections:
            print(f"\n📈 COLEÇÃO 'simulations':")
            sim_cursor = db.simulations.find({}).sort("timestamp", -1)  # Mais recentes primeiro
            simulations = await sim_cursor.to_list(length=10)  # Primeiros 10
            
            print(f"📊 Total de simulações: {await db.simulations.count_documents({})}")
            
            if simulations:
                # Estatísticas
                with_token = await db.simulations.count_documents({"access_token_usado": {"$ne": None, "$ne": ""}})
                without_token = await db.simulations.count_documents({"$or": [{"access_token_usado": None}, {"access_token_usado": ""}]})
                
                print(f"✅ Com token (associadas): {with_token}")
                print(f"❌ Sem token (órfãs): {without_token}")
                
                for i, sim in enumerate(simulations, 1):
                    print(f"\n--- SIMULAÇÃO {i} ---")
                    print(f"🆔 ID: {sim.get('simulation_id', 'N/A')}")
                    print(f"💰 Valor: R$ {sim.get('valor_carta', 0):,.2f}")
                    print(f"📅 Prazo: {sim.get('prazo_meses', 'N/A')} meses")
                    print(f"📊 Taxa Admin: {sim.get('taxa_admin', 0)*100:.1f}%")
                    print(f"🎯 CET: {sim.get('cet_anual', 0)*100:.2f}%")
                    print(f"🔑 Token: {sim.get('access_token_usado', 'SEM TOKEN')[:20] if sim.get('access_token_usado') else 'SEM TOKEN'}...")
                    print(f"🕐 Timestamp: {sim.get('timestamp', 'N/A')}")
                    
                    # Verificar se encontra o lead dono
                    if sim.get('access_token_usado'):
                        lead_owner = await db.leads.find_one({"access_token": sim.get('access_token_usado')})
                        if lead_owner:
                            print(f"👤 Lead dono: {lead_owner.get('nome', '')} ({lead_owner.get('email', '')})")
                        else:
                            print(f"⚠️  Token não encontra lead dono!")
            else:
                print("📭 Nenhuma simulação encontrada")
                
        # 4. Verificar outras coleções
        for collection in collections:
            if collection not in ['leads', 'simulations']:
                count = await db[collection].count_documents({})
                print(f"\n📋 COLEÇÃO '{collection}': {count} documentos")
                if count > 0:
                    sample = await db[collection].find_one({})
                    print(f"📄 Exemplo de documento:")
                    # Mostrar apenas as chaves para não poluir
                    if isinstance(sample, dict):
                        keys = list(sample.keys())[:10]  # Primeiras 10 chaves
                        print(f"   Campos: {keys}")
        
        print(f"\n" + "=" * 80)
        print("🎯 RESUMO:")
        print(f"📊 Total de coleções: {len(collections)}")
        if "leads" in collections:
            total_leads = await db.leads.count_documents({})
            print(f"👥 Total de leads: {total_leads}")
        if "simulations" in collections:
            total_sims = await db.simulations.count_documents({})
            print(f"📈 Total de simulações: {total_sims}")
            
    except Exception as e:
        print(f"❌ Erro ao conectar no MongoDB: {e}")
        print("💡 Certifique-se que o MongoDB está rodando em localhost:27017")

if __name__ == "__main__":
    asyncio.run(analisar_mongodb())