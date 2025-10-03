#!/usr/bin/env python3
"""
Critical Test for Consortium Simulator Issue
Tests the exact issue reported by user: Frontend shows 'N/A' for CET and Valor Total
"""

import requests
import json
import sys

def test_critical_simulator_issue():
    """
    🔥 CRITICAL TEST: Test the exact issue reported by user
    
    USER ISSUE: "O simulador de consórcio não está fazendo cálculos! O frontend mostra 'N/A' para CET e Valor Total."
    
    Test requirements from user:
    1. Test direct endpoint /api/simular with basic data
    2. Verify response contains numeric values (not null) for cet_anual and valor_total_pago
    3. Check for expected response fields: grafico_probabilidade, grafico_fluxo, grafico_saldo, tabela_dados
    4. If returning null/N/A, identify where it's failing
    
    Exact parameters from user:
    - valor_carta: 100000
    - prazo_meses: 120
    - taxa_admin: 0.21
    - fundo_reserva: 0.03
    - mes_contemplacao: 1
    - lance_livre_perc: 0.10
    - taxa_reajuste_anual: 0.05
    """
    base_url = "https://consortech.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Exact parameters from user report
    parametros = {
        "valor_carta": 100000,
        "prazo_meses": 120,
        "taxa_admin": 0.21,
        "fundo_reserva": 0.03,
        "mes_contemplacao": 1,
        "lance_livre_perc": 0.10,
        "taxa_reajuste_anual": 0.05
    }
    
    print(f"🔥 TESTING CRITICAL SIMULATOR ISSUE - User Report: Frontend shows 'N/A' for CET and Valor Total")
    print(f"   Testing endpoint: /api/simular")
    print(f"   Parameters: {json.dumps(parametros, indent=2)}")
    print(f"   Base URL: {base_url}")
    
    try:
        # Test the exact endpoint with exact parameters
        response = requests.post(f"{api_url}/simular", 
                               json=parametros, 
                               timeout=30)
        
        success = response.status_code == 200
        critical_issues = []
        
        print(f"\n📡 RESPONSE STATUS: {response.status_code}")
        
        if success:
            data = response.json()
            print(f"   ✅ HTTP 200 OK - Response received")
            print(f"   📋 Response keys: {list(data.keys())}")
            
            # Check if simulation has error
            if data.get('erro'):
                critical_issues.append(f"SIMULATION ERROR: {data.get('mensagem')}")
                success = False
                print(f"   ❌ Simulation error: {data.get('mensagem')}")
            else:
                print(f"   ✅ No simulation error")
                
                # 1. CRITICAL: Check cet_anual (user reports N/A)
                resultados = data.get('resultados', {})
                cet_anual = resultados.get('cet_anual')
                
                print(f"\n🔍 CHECKING CET_ANUAL:")
                print(f"   Raw value: {cet_anual}")
                print(f"   Type: {type(cet_anual)}")
                
                if cet_anual is None:
                    critical_issues.append("❌ CRITICAL: cet_anual is NULL - this causes frontend N/A")
                    print(f"   ❌ cet_anual is NULL")
                elif str(cet_anual) in ['nan', 'inf', '-inf']:
                    critical_issues.append(f"❌ CRITICAL: cet_anual is invalid: {cet_anual}")
                    print(f"   ❌ cet_anual is invalid: {cet_anual}")
                else:
                    print(f"   ✅ cet_anual is valid: {cet_anual} ({cet_anual*100:.2f}% a.a.)")
                
                # 2. CRITICAL: Check valor_total_pago (user reports N/A)
                resumo_financeiro = data.get('resumo_financeiro', {})
                valor_total_pago = resumo_financeiro.get('total_parcelas')
                
                print(f"\n🔍 CHECKING VALOR_TOTAL_PAGO:")
                print(f"   Raw value: {valor_total_pago}")
                print(f"   Type: {type(valor_total_pago)}")
                
                if valor_total_pago is None:
                    critical_issues.append("❌ CRITICAL: valor_total_pago (total_parcelas) is NULL")
                    print(f"   ❌ valor_total_pago is NULL")
                elif str(valor_total_pago) in ['nan', 'inf', '-inf']:
                    critical_issues.append(f"❌ CRITICAL: valor_total_pago is invalid: {valor_total_pago}")
                    print(f"   ❌ valor_total_pago is invalid: {valor_total_pago}")
                else:
                    print(f"   ✅ valor_total_pago is valid: R${valor_total_pago:,.2f}")
                
                # 3. Check required response fields
                print(f"\n🔍 CHECKING REQUIRED FIELDS:")
                required_fields = {
                    'parametros': data.get('parametros'),
                    'resultados': data.get('resultados'),
                    'fluxos': data.get('fluxos'),
                    'detalhamento': data.get('detalhamento'),
                    'resumo_financeiro': data.get('resumo_financeiro')
                }
                
                for field, value in required_fields.items():
                    if value is None:
                        print(f"   ❌ {field}: NULL")
                    else:
                        print(f"   ✅ {field}: Present ({type(value).__name__})")
                
                missing_fields = [field for field, value in required_fields.items() if value is None]
                if missing_fields:
                    critical_issues.append(f"❌ Missing response fields: {missing_fields}")
                else:
                    print(f"   ✅ All required response fields present")
                
                # 4. Check convergence status
                convergiu = resultados.get('convergiu', False)
                motivo_erro = resultados.get('motivo_erro')
                
                print(f"\n🔍 CHECKING CONVERGENCE:")
                print(f"   Convergiu: {convergiu}")
                print(f"   Motivo erro: {motivo_erro}")
                
                if not convergiu:
                    print(f"   ⚠️ CET did not converge: {motivo_erro}")
                    # Check if VPL is available as alternative
                    vpl = resultados.get('vpl')
                    if vpl is None or str(vpl) in ['nan', 'inf', '-inf']:
                        critical_issues.append("❌ CRITICAL: CET didn't converge AND VPL is invalid")
                        print(f"   ❌ VPL is also invalid: {vpl}")
                    else:
                        print(f"   ✅ VPL available as alternative: R${vpl:,.2f}")
                else:
                    print(f"   ✅ CET converged successfully")
                
                # 5. Check data completeness
                fluxos = data.get('fluxos', [])
                detalhamento = data.get('detalhamento', [])
                
                print(f"\n🔍 CHECKING DATA COMPLETENESS:")
                print(f"   Cash flows: {len(fluxos)} (expected 121)")
                print(f"   Monthly details: {len(detalhamento)} (expected 120)")
                
                if len(fluxos) != 121:  # 0 + 120 months
                    critical_issues.append(f"❌ Wrong number of cash flows: {len(fluxos)} (expected 121)")
                else:
                    print(f"   ✅ Cash flows complete: {len(fluxos)} periods")
                
                if len(detalhamento) != 120:  # 120 months
                    critical_issues.append(f"❌ Wrong number of detail months: {len(detalhamento)} (expected 120)")
                else:
                    print(f"   ✅ Monthly details complete: {len(detalhamento)} months")
                
                # 6. Show sample data
                print(f"\n📊 SAMPLE DATA:")
                if resultados:
                    print(f"   Results keys: {list(resultados.keys())}")
                if resumo_financeiro:
                    print(f"   Financial summary keys: {list(resumo_financeiro.keys())}")
                    print(f"   Base contract: R${resumo_financeiro.get('base_contrato', 'N/A'):,.2f}")
                    print(f"   Lance livre: R${resumo_financeiro.get('valor_lance_livre', 'N/A'):,.2f}")
            
            success = len(critical_issues) == 0
            
            print(f"\n🎯 FINAL RESULT:")
            if success:
                print(f"   ✅ SIMULATOR WORKING CORRECTLY")
                print(f"   CET: {cet_anual*100:.2f}% a.a.")
                print(f"   Total Pago: R${valor_total_pago:,.2f}")
                print(f"   Convergiu: {convergiu}")
            else:
                print(f"   ❌ CRITICAL ISSUES FOUND:")
                for issue in critical_issues:
                    print(f"     - {issue}")
                
        else:
            critical_issues.append(f"HTTP ERROR: {response.status_code}")
            print(f"   ❌ HTTP {response.status_code}: {response.text[:300]}")
            
        return success, critical_issues
        
    except Exception as e:
        print(f"   ❌ EXCEPTION: {str(e)}")
        return False, [f"Exception: {str(e)}"]

if __name__ == "__main__":
    print("🔥 CRITICAL SIMULATOR TEST")
    print("=" * 80)
    
    success, issues = test_critical_simulator_issue()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ CRITICAL TEST PASSED - Simulator is working correctly")
        sys.exit(0)
    else:
        print("❌ CRITICAL TEST FAILED - Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)