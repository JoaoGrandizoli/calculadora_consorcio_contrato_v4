#!/usr/bin/env python3
"""
Detailed test for the saldo devedor bug fix
Focuses specifically on the balance calculation around contemplation month 17
"""

import requests
import json

def test_saldo_devedor_detailed():
    """Detailed analysis of saldo devedor calculation around contemplation"""
    
    # Exact parameters from user report
    parametros = {
        "valor_carta": 100000,
        "prazo_meses": 120,
        "taxa_admin": 0.21,
        "fundo_reserva": 0.03,
        "mes_contemplacao": 17,
        "lance_livre_perc": 0.10,
        "taxa_reajuste_anual": 0.05
    }
    
    print("🔍 DETAILED SALDO DEVEDOR ANALYSIS")
    print("=" * 60)
    print(f"Parameters: valor_carta={parametros['valor_carta']:,}, mes_contemplacao={parametros['mes_contemplacao']}")
    print(f"lance_livre_perc={parametros['lance_livre_perc']}, prazo_meses={parametros['prazo_meses']}")
    print()
    
    try:
        response = requests.post("https://simula-credito.preview.emergentagent.com/api/simular", 
                               json=parametros, 
                               timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return False
            
        data = response.json()
        
        if data.get('erro'):
            print(f"❌ Simulation Error: {data.get('mensagem')}")
            return False
        
        detalhamento = data['detalhamento']
        resumo = data['resumo_financeiro']
        
        print("📊 FINANCIAL SUMMARY:")
        print(f"Base Contract: R${resumo['base_contrato']:,.2f}")
        print(f"Lance Livre: R${resumo['valor_lance_livre']:,.2f}")
        print(f"Carta Value at Contemplation: R${resumo['valor_carta_contemplacao']:,.2f}")
        print()
        
        print("📈 SALDO DEVEDOR PROGRESSION (Months 15-21):")
        print("Month | Date  | Parcela    | Saldo Devedor | Contemplação | Fluxo")
        print("-" * 70)
        
        for item in detalhamento:
            if 15 <= item['mes'] <= 21:
                mes = item['mes']
                data_mes = item['data']
                parcela = item['parcela_corrigida']
                saldo = item['saldo_devedor']
                contemplacao = "✅ SIM" if item['eh_contemplacao'] else "   não"
                fluxo = item['fluxo_liquido']
                
                print(f"{mes:5d} | {data_mes:5s} | R${parcela:8,.2f} | R${saldo:11,.2f} | {contemplacao:10s} | R${fluxo:8,.2f}")
        
        print()
        
        # Specific analysis of the bug fix
        print("🐛 BUG FIX ANALYSIS:")
        
        # Get specific months
        month_16 = next(item for item in detalhamento if item['mes'] == 16)
        month_17 = next(item for item in detalhamento if item['mes'] == 17)
        month_18 = next(item for item in detalhamento if item['mes'] == 18)
        
        saldo_16 = month_16['saldo_devedor']
        saldo_17 = month_17['saldo_devedor']
        saldo_18 = month_18['saldo_devedor']
        parcela_17 = month_17['parcela_corrigida']
        valor_carta_17 = month_17['valor_carta_corrigido']
        
        print(f"Month 16 balance: R${saldo_16:,.2f}")
        print(f"Month 17 installment: R${parcela_17:,.2f}")
        print(f"Month 17 carta value: R${valor_carta_17:,.2f}")
        print(f"Month 17 balance: R${saldo_17:,.2f}")
        print(f"Month 18 balance: R${saldo_18:,.2f}")
        print()
        
        # Calculate expected balance decrease
        expected_decrease = parcela_17
        actual_decrease = saldo_16 - saldo_17
        
        print(f"Expected balance decrease (only installment): R${expected_decrease:,.2f}")
        print(f"Actual balance decrease: R${actual_decrease:,.2f}")
        print(f"Difference: R${abs(expected_decrease - actual_decrease):,.2f}")
        print()
        
        # Verify the fix
        issues = []
        
        # 1. Balance should not go to zero
        if saldo_17 < 1000:
            issues.append(f"Balance too low in month 17: R${saldo_17:,.2f}")
        
        # 2. Balance decrease should be approximately the installment
        if abs(expected_decrease - actual_decrease) > 100:
            issues.append(f"Balance decrease incorrect: expected R${expected_decrease:,.2f}, got R${actual_decrease:,.2f}")
        
        # 3. Balance should continue decreasing
        if saldo_18 >= saldo_17:
            issues.append(f"Balance not decreasing after contemplation")
        
        # 4. Final balance should be close to zero
        final_balance = detalhamento[-1]['saldo_devedor']
        if final_balance > 1000:
            issues.append(f"Final balance too high: R${final_balance:,.2f}")
        
        if issues:
            print("❌ ISSUES FOUND:")
            for issue in issues:
                print(f"   • {issue}")
            return False
        else:
            print("✅ BUG FIX VERIFICATION SUCCESSFUL!")
            print("   • Balance does not go to zero after contemplation")
            print("   • Balance decreases only by installment amount")
            print("   • Balance continues decreasing in following months")
            print(f"   • Final balance reaches zero naturally: R${final_balance:,.2f}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_saldo_devedor_detailed()
    exit(0 if success else 1)